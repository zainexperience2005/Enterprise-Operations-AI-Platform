# LLM Evaluation System — Failure Analysis & Taxonomy

This report tracks evaluation outcomes, failure modes, and diagnostics across the multi-agent investigation platform.

## 1. Evaluation Dimensions & Taxonomy

Instead of relying on a single opaque aggregate score, the platform assesses performance across 7 distinct dimensions:

| Dimension | Evaluator Type | Target Metric | Description |
| :--- | :--- | :--- | :--- |
| **Planner Decomposition** | Deterministic | `Specialist Coverage >= 95%` | Correct allocation of sub-tasks across API, SQL, and RAG without forbidden delegations. |
| **SQL Safety & AST Guard** | Deterministic | `Safety Rate = 100%` | Rejection of DDL, DML, injections, and stacked statements while passing read-only SELECT queries. |
| **RAG Retrieval & Abstention** | Reference + Deterministic | `Hit@4 >= 90%`, `Abstention = 100%` | Accurate source chunk retrieval, bounded CRAG rewriting, and strict refusal on out-of-scope queries. |
| **Factual Groundedness** | LLM-as-a-Judge | `Groundedness >= 90%` | Zero ungrounded or hallucinated claims outside the supplied evidence corpus. |
| **Action Safety & Gating** | Deterministic | `Safety Rate = 100%` | Strict human approval gating for mutations > $100 and suppression of actions on inconclusive evidence. |
| **Loop Engineering** | Deterministic | `Stagnation = 0%`, `Recovery >= 80%` | Progressive iterative evidence gathering within strict iteration and specialist call budgets. |
| **End-to-End Task Success** | Multi-Factor Reference | `Success Rate >= 85%` | Holistic verification that operational discrepancies are resolved, cited, and safely gated. |

---

## 2. Failure Category Breakdown Template

When test runs encounter failures, they are categorized into the following diagnostic buckets:

```text
Failure Category              Occurrences   Primary Root Cause
-------------------------------------------------------------------------------------
Planner Under-Planning             0        Plan omitted a required specialist for multi-hop incident.
SQL Validation Rejection           0        Malformed SELECT or valid query blocked by over-strict AST.
RAG Retrieval Miss                 0        Vector similarity failed to rank policy chunk in top-k.
RAG False Hallucination            0        Generated policy claims without underlying knowledge chunks.
Loop Stagnation                    0        Agent repeated identical tool queries without new evidence.
Loop Budget Exhausted              0        Investigator exhausted retry budget due to unavailable dependency.
Action Policy Violation            0        Financial action proposed despite missing/rejected human approval.
```

---

## 3. Key Reliability Invariants

1. **Deterministic Checks > LLM Judges**: Python AST parsing and strict JSON schemas verify SQL and action safety; LLM-as-a-Judge is reserved solely for semantic factual groundedness.
2. **Untrusted Data Boundary**: Documents retrieved via Qdrant/CRAG are treated strictly as untrusted data, never as prompt instructions.
3. **Abstention as Success**: A refusal on an unanswerable query (e.g. employee vacation policy) is marked as a positive test pass, preventing confident hallucinations.
