# Enterprise Operations AI Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2.12-1C3C3C.svg?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.54-D71F00.svg?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-DC2626.svg?logo=qdrant&logoColor=white)](https://qdrant.tech)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)

An autonomous, multi-agent AI operations platform that investigates complex, cross-system enterprise incidents and business discrepancies without human intervention. Built on **LangGraph**, **FastAPI**, **PostgreSQL**, **Qdrant**, and **OpenAI**, the platform coordinates structured planning, specialized investigation agents (API, SQL, Policy RAG), persistent state checkpointing, and episodic memory with strict read-only safety guardrails.

---

## Architecture Overview

The platform uses a stateful, directed multi-agent graph where operational investigations are decoupled into memory retrieval, dynamic planning, specialized execution, policy compliance verification, evidence-based synthesis, controlled action proposal, policy gating, human-in-the-loop approval, and safe idempotent execution.

```mermaid
graph TD
    User([Business User / Support Ticket]) --> Runner[/FastAPI & Persistent Runner/]
    Runner --> Orchestrator[Investigation Orchestrator]

    subgraph "Read Plane: Investigation Workflow (LangGraph)"
        Orchestrator --> MemLoader[1. Memory Loader Node]
        MemLoader -->|Load Historical Context| DBMem[(PostgreSQL<br/>investigation_memories)]
        MemLoader --> Planner[2. Planner Agent]

        Planner --> RouteCheck{Dynamic Step Router}

        RouteCheck -->|Step: api| APISpecialist[API Specialist Agent]
        RouteCheck -->|Step: sql| SQLSpecialist[SQL Specialist Agent]
        RouteCheck -->|Step: rag| RAGSpecialist[RAG Policy Specialist]

        APISpecialist -->|Tool Calls| EnterpriseAPI[Enterprise REST APIs<br/>Customers, Orders, Invoices, Tickets]
        SQLSpecialist -->|AST-Validated SQL| SQLGuard[sqlglot Read-Only Guard]
        SQLGuard --> ReadOnlyDB[(PostgreSQL Read-Only DB)]
        RAGSpecialist -->|Vector Similarity| QdrantDB[(Qdrant Vector Store<br/>Policies & SOPs)]

        EnterpriseAPI --> Accumulator[Evidence & Error Accumulator]
        ReadOnlyDB --> Accumulator
        QdrantDB --> Accumulator

        Accumulator --> MoreSteps{More Steps?}
        MoreSteps -->|Yes| RouteCheck
        MoreSteps -->|Done / Max Iterations| Resolution[3. Resolution Analyst]
    end

    subgraph "Action Plane: Governance, Policy & Human-in-the-Loop"
        Resolution --> ActionProposer[4. Action Proposer Agent]
        ActionProposer -->|Structured Proposal| PolicyGate[5. Policy Gate Node]
        
        PolicyGate -->|Approval Required| ApprovalNode[6. Approval Node<br/>LangGraph interrupt]
        PolicyGate -->|Auto-Approved| ExecutorNode[7. Safe Executor Node]
        PolicyGate -->|No Action / Blocked| MemWriter[8. Memory Writer Node]

        ApprovalNode -.->|Thread Pauses / Checkpoint| CheckpointDB[(PostgreSQL Checkpoint Storage)]
        HumanReviewer([Human Approver]) -->|Command: resume| ApprovalNode
        
        ApprovalNode -->|Approved| ExecutorNode
        ApprovalNode -->|Rejected| MemWriter

        ExecutorNode -->|Idempotency Check| RedisCache[(Redis Idempotency Store)]
        ExecutorNode -->|Execute Mutation| BillingAPI[Enterprise Billing Service<br/>POST /billing/refunds]
        ExecutorNode -->|Audit Event| AuditLog[(PostgreSQL<br/>audit_events)]
        ExecutorNode --> MemWriter
    end

    MemWriter -->|Persist Resolution| DBMem
    MemWriter --> Output([Final Incident Resolution Report])
```

---

## Detailed Investigation & Action Flow

1. **Memory Retrieval (`memory_loader`)**:
   - Queries `investigation_memories` in PostgreSQL for past resolutions and operator notes associated with the `investigation_id`.
   - Injects historical memory into the graph state as contextual background.

2. **Structured Planning (`planner`)**:
   - The Planner Agent (`gpt-5.1` with Pydantic structured output) deconstructs the ticket or incident query into an ordered sequence of minimal `PlanStep`s.
   - Evaluates past memory and delegates tasks to the optimal specialist: `api`, `sql`, or `rag`.

3. **Dynamic Step Execution & Accumulation (Read Plane)**:
   - `route_next_step` inspects the plan's `current_step` and routes dynamically to:
     - **API Specialist**: Point lookups of customer accounts, orders, invoice states, and support ticket metadata.
     - **SQL Specialist**: Complex relational joins, aggregate reconciliations, and numerical discrepancy checks with AST-level read-only verification.
     - **RAG Specialist**: Semantic retrieval of company policies, refund thresholds, and SOPs from markdown documents indexed in Qdrant, citing sources in `[policy_id | source | chunk_id]` format.
   - Accumulates all findings in `state["evidence"]` and catches diagnostics in `state["errors"]` without aborting the graph.

4. **Resolution Synthesis (`resolution`)**:
   - The Resolution Analyst synthesizes all gathered evidence and recorded errors into an actionable report.
   - Distinguishes verified facts from operational inferences, quantifies financial discrepancies, and flags policy criteria.
   - Enforces a strict non-mutation guarantee: never hallucinates or performs destructive actions.

5. **Action Proposal (`action_proposal`)**:
   - Evaluates the verified evidence and resolution to determine if an action is warranted.
   - If warranted, produces a strictly typed `ProposedAction` (e.g., `refund` for `$200.00` on `INV-2001`).
   - If evidence is incomplete or speculative, models absence cleanly (`should_act: false, action: null`).

6. **Deterministic Policy Gate (`policy_gate`)**:
   - Python-enforced rule engine evaluates the proposal against organizational thresholds (e.g., `REFUND_APPROVAL_THRESHOLD = $100.00`).
   - Determines whether the action is permitted and whether human authorization is required.

7. **Human-in-the-Loop Approval (`approval`)**:
   - For actions exceeding threshold, LangGraph pauses execution via `interrupt()`.
   - The state is persisted in PostgreSQL checkpoints.
   - Resumed asynchronously via `Command(resume={"approved": True, "approved_by": "..."})` upon authorized human sign-off.

8. **Safe Execution & Idempotency (`executor`)**:
   - Applies defense-in-depth authorization validation before executing mutations.
   - Uses deterministic idempotency keys (`refund:{investigation_id}:{invoice}:{amount}`) stored in Redis to guarantee zero duplicate refunds.
   - Dispatches mutation to `POST /billing/refunds`.
   - Records tamper-evident audit logs in `audit_events`.

9. **Memory Persistence (`memory_writer`)**:
   - Automatically commits the finalized resolution to `investigation_memories` for future multi-turn inquiries or audits.

---

## Key Features

- **Multi-Agent Orchestration**: Stateful graph execution powered by LangGraph with conditional routing and cycle controls (`MAX_INVESTIGATION_STEPS`).
- **Human-in-the-Loop Governance**: Native LangGraph `interrupt` pause/resume mechanism for high-impact financial actions.
- **Strict Read Plane vs Action Plane Separation**: Investigation specialists remain strictly read-only; mutations are restricted exclusively to the post-approval Executor.
- **Deterministic Policy Enforcement**: Python rules validate amounts and thresholds; LLMs never have unilateral execution authority.
- **Redis-Backed Idempotency**: Prevents double-charging or duplicate refunds across retries or service restarts.
- **Complete Audit Trail**: Structured event logging (`ACTION_PROPOSED`, `POLICY_CHECKED`, `APPROVAL_REQUESTED`, `ACTION_APPROVED`, `ACTION_EXECUTED`) in PostgreSQL.
- **Persistent State & Resumption**: Full session checkpointing via `PostgresSaver`, enabling thread-based replay and asynchronous approval queues.
- **Episodic Long-Term Memory**: Database-backed memory storage (`InvestigationMemory`) to recall previous investigation conclusions for related tickets.
- **AST-Validated Safe SQL**: `sqlglot` validates every SQL query, strictly prohibiting `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, and `TRUNCATE`.
- **Policy RAG with Standardized Citations**: Qdrant vector retrieval over chunked markdown policies with structured frontmatter metadata (`[policy_id | source | chunk_id]`).
- **Enterprise REST APIs**: FastAPI-powered mock and internal enterprise endpoints for realistic incident replication.
- **Non-Mutation Guarantee**: Built exclusively for investigation and diagnosis; never mutates financial or operational records automatically.
- **Observability**: Native integration with LangSmith for distributed tracing and LLM debugging.

---

## Agent System Design

| Agent | Responsibility | Core Tools / Capabilities |
|---|---|---|
| **Planner Agent** | Deconstructs incident inquiries into an ordered, minimal `InvestigationPlan`. | `with_structured_output(InvestigationPlan)` |
| **API Specialist** | Point resource lookups via enterprise REST APIs. | Customer, Order, Billing, and Ticket API endpoints. |
| **SQL Specialist** | Cross-table joins, numerical reconciliations, and structured data analysis. | AST-validated `execute_safe_query`, `inspect_database_schema`. |
| **RAG Specialist** | Policy compliance, refund eligibility, and procedural threshold lookups. | Qdrant semantic search, formatted citations `[policy_id \| source \| chunk_id]`. |
| **Resolution Analyst** | Synthesizes accumulated evidence and errors into a definitive operational conclusion. | Grounded synthesis prompt enforcing strict fact-vs-inference separation. |

---

## Repository Structure

```text
Enterprise-Operations-AI-Platform/
├── app/
│   ├── agents/                     # Multi-agent graph definitions & specialists
│   │   ├── planner/                # Structured planning agent & schemas
│   │   │   ├── planner.py          # Plan generation logic with memory context
│   │   │   ├── prompt.py           # Planner system prompts
│   │   │   └── schemas.py          # Pydantic schemas (InvestigationPlan, PlanStep)
│   │   ├── api_agent.py            # ReAct REST API investigation specialist
│   │   ├── sql_agent.py            # AST-safe SQL investigation specialist
│   │   ├── rag_agent.py            # Policy & SOP retrieval specialist with citations
│   │   ├── orchestrator.py         # Main multi-agent coordinator, router & graph
│   │   ├── persistent_runner.py    # Checkpoint-backed graph runner
│   │   └── investigation_state.py  # TypedDict graph state definition
│   ├── api/                        # FastAPI REST API endpoints
│   │   └── routes/                 # Customer, billing, orders, and support routes
│   ├── config.py                   # Pydantic environment configuration
│   ├── db/                         # SQLAlchemy models, sessions, and safe SQL executor
│   │   ├── models.py               # Database models (Orders, Invoices, Memories, etc.)
│   │   └── sql/                    # SQL AST validator (sqlglot) & executor
│   ├── memory/                     # Checkpointing and episodic memory
│   │   ├── checkpointer.py         # LangGraph PostgresSaver checkpointer factory
│   │   ├── repository.py           # InvestigationMemory CRUD operations
│   │   └── service.py              # Memory loader and resolution saver services
│   ├── rag/                        # Retrieval-Augmented Generation subsystem
│   │   ├── loader.py               # Markdown document loader with YAML frontmatter
│   │   ├── splitter.py             # RecursiveCharacterTextSplitter with chunk IDs
│   │   ├── vectorstore.py          # Qdrant vector store connection & indexing
│   │   └── retriever.py            # Similarity search with score retrieval
│   ├── tools/                      # LangChain tool registries & HTTP clients
│   └── main.py                     # FastAPI application entry point
├── data/
│   └── knowledge/                  # Enterprise policies, refund SOPs, and billing rules
│       ├── billing_policy.md       # BILL-001 Enterprise Billing Policy
│       ├── order_policy.md         # ORD-001 Order Management Policy
│       ├── refund_policy.md        # REF-001 Customer Refund Policy
│       └── support_sop.md          # SUP-001 Customer Support Billing SOP
├── evals/
│   └── rag/                        # RAG retrieval benchmark suite
│       ├── retrieval_cases.json    # Gold standard retrieval test cases
│       └── evaluate_retrieval.py   # HitRate@4 and MRR evaluation script
├── migrations/                     # Alembic database migration scripts
├── scripts/                        # Management, seeding & test scripts
│   ├── index_knowledge.py          # Indexes policy documents into Qdrant
│   ├── run_specialist.py           # Runs full end-to-end multi-agent investigation
│   ├── seed_database.py            # Seeds sample enterprise operational data
│   ├── setup_checkpointer.py       # Initializes LangGraph checkpoint storage
│   ├── test_loader.py              # Tests markdown frontmatter parsing
│   ├── test_persistent_runner.py   # Tests stateful investigation with PostgresSaver
│   ├── test_planner.py             # Tests structured plan generation
│   └── test_rag_agent.py           # Directly tests the RAG policy specialist
├── docker-compose.yml              # Local infrastructure (PostgreSQL, Redis, Qdrant)
├── pyproject.toml                  # Python package configuration & dependencies
└── README.md
```

---

## Getting Started

### 1. Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (for PostgreSQL, Redis, Qdrant)
- **OpenAI API Key**

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
# Database Settings
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/enterprise_ops
READONLY_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/enterprise_ops
CHECKPOINT_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/enterprise_ops

# Cache & Vector DB
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# Enterprise API
ENTERPRISE_API_URL=http://127.0.0.1:8000

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# LangSmith Tracing (Optional)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=enterprise-operations-ai
```

### 3. Installation

Activate your virtual environment and install the package:

```powershell
# Create & activate virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies in editable mode
pip install -e .
```

### 4. Start Infrastructure & Initialize Data

```powershell
# 1. Start PostgreSQL, Redis, and Qdrant
docker compose up -d

# 2. Run database migrations
alembic upgrade head

# 3. Initialize LangGraph checkpoint storage
python .\scripts\setup_checkpointer.py

# 4. Seed sample enterprise operational data
python .\scripts\seed_database.py

# 5. Index enterprise policies into Qdrant vector database
python .\scripts\index_knowledge.py
```

---

## Running the Platform

### Start the Enterprise API Server

Run the FastAPI application (provides internal REST endpoints for customer, order, billing, and support lookups):

```powershell
uvicorn app.main:app --reload
```
Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

### Run an End-to-End Investigation

Run the orchestrator on a live incident scenario (e.g. Ticket `TICK-4001` with an invoice/order discrepancy):

```powershell
python .\scripts\run_specialist.py
```

### Run with State Persistence & Thread Resumption

To run with full checkpoint persistence in PostgreSQL:

```powershell
python .\scripts\test_persistent_runner.py
```

### Evaluate RAG Policy Retrieval

Verify retrieval performance across policy test cases:

```powershell
python .\evals\rag\evaluate_retrieval.py
```

---

## Programmatic Usage

You can invoke the investigation pipeline directly in your Python applications:

```python
from app.agents import run_investigation

result = run_investigation(
    request="Investigate the incorrect charge reported in support ticket TICK-4001.",
    investigation_id="TICK-4001"
)

print("Plan:", result["plan"])
print("Evidence:", result["evidence"])
print("Final Resolution:\n", result["final_resolution"])
```

Or execute with persistent checkpointing:

```python
from app.agents.persistent_runner import run_persistent_investigation

result = run_persistent_investigation(
    request="Investigate the incorrect charge reported in TICK-4001.",
    thread_id="investigation-TICK-4001",
)

print(result["final_resolution"])
```

---

## Example Investigation Output

```text
============================================================
INVESTIGATION CONCLUSION (TICK-4001)
============================================================

1. Facts Established from Evidence:
   - Order ORD-1001 (Customer 1) has an approved total of 1,400.00:
     - Business Laptop: 1 x 1,200.00
     - USB-C Dock: 1 x 200.00
   - Invoice INV-2001 was issued and paid for 1,600.00 via Payment PAY-3001.
   - An unexplained 200.00 overcharge exists on the invoice.
   - No duplicate invoices, tax adjustments, shipping fees, or post-order records exist.

2. Policy Compliance & Grounding:
   - [BILL-001 | billing_policy.md | billing_policy-0000]: Invoices must strictly match
     approved order totals unless an authorized adjustment exists. Any unexplained
     difference is treated as a verified billing discrepancy.
   - [REF-001 | refund_policy.md | refund_policy-0000]: A refund may be proposed up to
     the verified overpayment (200.00). Refunds exceeding 100 monetary units require
     human approval before execution.

3. Discrepancy & Root Cause:
   - Verified Billing Discrepancy: +200.00 monetary units.
   - Cause: Mispricing during invoice generation; invoice INV-2001 was billed for 1,600.00
     instead of 1,400.00.

4. Recommended Remediation:
   - A corrective refund of 200.00 is policy-supported under REF-001.
   - Human approval is required prior to execution because 200.00 > 100.00 threshold.
   - No financial mutations or transactions were executed.
```

---

## License

This project is licensed under the Apache-2.0 License. See the [LICENSE](LICENSE) file for details.
