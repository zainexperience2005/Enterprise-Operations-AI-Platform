# Enterprise Reliability & Failure Recovery Guide

==============================================================================
ENTERPRISE OPERATIONS AI PLATFORM - RELIABILITY ENGINEERING MANUAL
==============================================================================

## 1. Reliability Philosophy

In real-world enterprise environments, external services, networks, and language models inevitably fail:
- REST APIs return `503 Service Unavailable` or `429 Too Many Requests`.
- Network connections drop or time out mid-stream.
- Databases experience lock contention or query timeouts.
- Vector stores become temporarily unreachable.
- LLMs output malformed structures or hit token budgets.

**Reliability does NOT mean the system never fails.**  
Reliability means:
> **When failure happens, the platform detects it, classifies it, retries safely if transient, degrades gracefully if permanent, records detailed audit diagnostics, and NEVER hallucinates success or executes unauthorized mutations.**

---

## 2. Failure Classification: Transient vs Permanent

| Error Category | Characteristics | HTTP / System Examples | Retry Policy |
|---|---|---|---|
| **Transient (Retryable)** | Temporary issue likely to resolve quickly under backoff. | `429` (Rate Limit), `500`, `502`, `503`, `504`, Socket Timeout, Network Reset. | **Retry** with exponential backoff & randomized jitter. |
| **Permanent (Non-Retryable)** | Deterministic error; repeated requests with identical input will always fail. | `400` (Bad Request), `401` (Unauthorized), `403` (Forbidden), `404` (Not Found), AST SQL rejection. | **Fail immediately**; do not waste latency or quotas. |

---

## 3. Reliability Matrix

| Dependency | Failure Mode | Classification | Retry Policy | Safe Fallback / Degradation |
|---|---|---|---|---|
| **Customer / Order / Billing APIs** | `503` / Network Timeout | Transient | Exponential backoff (`2^attempt + jitter`), max 2 retries. | Partial investigation report; state explicit missing sources. |
| **Customer / Order / Billing APIs** | `404 Not Found` | Permanent | **No retry** (immediate raise). | Log record absence; continue investigation with remaining records. |
| **PostgreSQL (Read-Only DB)** | Statement Timeout (`5000ms`) | Permanent | **No retry** (expensive query). | Mark database evidence unavailable; prevent resource starvation. |
| **Qdrant Vector Store** | Connection Refused / Outage | Transient / Permanent | Max 1 retry. | State that policy could not be verified; **do NOT assume policy absence**. |
| **OpenAI LLM API** | `429 Rate Limit` / `500` | Transient | Max 2 retries with backoff. | Fall back to graceful investigation pause or checkpoint save. |
| **Planner Structured Output** | Schema Validation Failure | Permanent | Log diagnostics to `state["errors"]`. | Fall back to human escalation or default investigation outline. |
| **Approval Subsystem** | Unreachable / Timed Out | Permanent | **Fail Closed** (no auto-approval). | Action remains in `pending` state; zero mutation executed. |
| **Refund / Mutation API** | Timeout / Lost Response | Transient | **Retry ONLY with identical Idempotency Key**. | Redis returns cached receipt; prevents duplicate charging. |

---

## 4. Read Plane vs Action Plane Retries

### Read Operations (Idempotent by nature)
- Operations: `GET /customers`, `GET /invoices`, `SELECT ...`
- Nature: Read-only; queries do not change enterprise state.
- Policy: Safe to retry multiple times with exponential backoff.

### Action Operations (High-Impact State Mutations)
- Operations: `POST /billing/refunds`, account updates, cancellations.
- Nature: Mutates business financial or operational state.
- **Golden Rule**: **NEVER apply blind retries to write endpoints.**
- Protection: Require a deterministic **Idempotency Key** (`refund:{investigation_id}:{invoice}:{amount}`) stored in Redis before dispatching. If a network timeout occurs and a retry is executed, the server or client cache returns the original receipt rather than executing a duplicate refund.

---

## 5. Backoff, Jitter & Circuit Breaker

### Exponential Backoff with Jitter Formula
To prevent the **thundering herd** problem where multiple parallel workers retry at the exact same millisecond:
$$\text{delay} = 2^{\text{attempt}} + \text{random}(0, 0.5)$$
- Attempt 0: ~1.0s to 1.5s
- Attempt 1: ~2.0s to 2.5s
- Attempt 2: ~4.0s to 4.5s

### Circuit Breaker Pattern
Guards downstream dependencies during catastrophic outages:
- **CLOSED**: Normal operation; all requests pass through.
- **OPEN**: Trips when consecutive failures reach `failure_threshold` (e.g. 5). Rejects calls immediately without network overhead for `recovery_seconds` (e.g. 30s).
- **HALF_OPEN**: After recovery period elapses, permits a single trial request. If successful, resets to `CLOSED`; if failed, trips back to `OPEN`.

---

## 6. Core Engineering Principles

1. **Absence of Evidence $\neq$ Evidence of Absence**:
   If RAG policy retrieval fails, report: *"Policy evidence could not be retrieved."* Never report: *"There is no policy."*
2. **Fail Closed**:
   When any security check, policy gate, or approval status is uncertain or unavailable, **BLOCK** the sensitive action.
3. **Defense in Depth**:
   Authorization and eligibility are checked at the Policy Gate AND re-verified inside the `executor_node` prior to dispatch.
4. **Separation of Concerns**:
   Internal diagnostic logs contain raw stack traces and exception types; user-facing responses communicate actionable, plain-language business status without leaking internal infrastructure details.
