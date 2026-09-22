# Enterprise Operations AI Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2.12-1C3C3C.svg?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.54-D71F00.svg?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)

An autonomous, multi-agent AI operations engineer that investigates complex, cross-system enterprise incidents and business discrepancies without human intervention. Built on **LangGraph**, **FastAPI**, **PostgreSQL**, and **OpenAI**, the platform coordinates structured planning, specialized agents, and a resolution analyst with strict read-only safety guardrails.

---

## Architecture Overview

The platform uses a directed, stateful multi-agent architecture where investigations are decoupled into planning, specialized execution, and evidence-based synthesis.

```mermaid
graph TD
    User([Business User / Incident Ticket]) --> Router[/API & Scripts/]
    Router --> Orchestrator[Investigation Orchestrator]

    subgraph "Investigation Workflow (LangGraph)"
        Orchestrator --> Planner[Planner Agent]
        Planner --> PlanCheck{Evaluate Steps}

        PlanCheck -->|Step: api| APISpecialist[API Specialist Agent]
        PlanCheck -->|Step: sql| SQLSpecialist[SQL Specialist Agent]

        APISpecialist -->|Tool Calls| EnterpriseAPI[Enterprise REST APIs<br/>Customers, Orders, Invoices, Tickets]
        SQLSpecialist -->|Safe Read-Only SQL| SQLGuard[AST Validator sqlglot]
        SQLGuard --> ReadOnlyDB[(PostgreSQL Read-Only DB)]

        EnterpriseAPI --> Accumulator[Evidence & Error Accumulator]
        ReadOnlyDB --> Accumulator

        Accumulator --> MoreSteps{More Steps?}
        MoreSteps -->|Yes| PlanCheck
        MoreSteps -->|Done / Max Iterations| ResolutionAnalyst[Resolution Analyst]
    end

    ResolutionAnalyst --> Output([Final Incident Resolution Report])
```

---

## Key Features

- **Multi-Agent Orchestration**: Stateful coordination powered by LangGraph, managing state transitions between planners, domain specialists, and synthesizers.
- **Dynamic Structured Planning**: High-level problem statements are automatically deconstructed into typed, ordered `PlanStep` sequences assigned to optimal specialists.
- **Safe, Read-Only SQL Execution**:
  - AST-level validation using `sqlglot` strictly prohibits `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, and administrative statements.
  - Explicit schema exposure to prevent hallucinated columns or table joins.
- **Enterprise REST API Integrations**: ReAct-driven tools for fast point retrieval of Customers, Orders, Invoices, and Support Tickets.
- **Error-Resilient Workflow**: Gracefully handles specialist timeouts or query failures by recording diagnostics without terminating the overall investigation.
- **Non-Mutation Guarantee**: Strictly designed for incident investigation, root-cause diagnosis, and discrepancy reporting; never performs destructive business actions (e.g. refunds, cancellations).
- **Full Observability**: Integrated with LangSmith for distributed tracing and LLM call inspection.

---

## Agent System Design

| Agent | Responsibility | Core Tools / Capabilities |
|---|---|---|
| **Planner Agent** | Deconstructs unstructured problem inquiries into an ordered, minimal `InvestigationPlan`. | `with_structured_output(InvestigationPlan)` |
| **API Specialist** | Direct resource lookups via enterprise REST APIs. | Customer, Order, Billing, and Ticket API endpoints. |
| **SQL Specialist** | Cross-table joins, numerical comparisons, discrepancy detection, and relational analysis. | AST-validated `execute_safe_query`, `inspect_database_schema`. |
| **Resolution Analyst** | Synthesizes accumulated evidence and diagnostic errors into a final, fact-grounded resolution. | Controlled synthesis prompt enforcing fact-versus-inference separation. |

---

## Repository Structure

```text
Enterprise-Operations-AI-Platform/
├── app/
│   ├── agents/                     # Multi-agent graph definitions
│   │   ├── planner/                # Structured planning agent & schemas
│   │   │   ├── planner.py          # Plan generation logic
│   │   │   ├── prompt.py           # Planner system prompts
│   │   │   └── schemas.py          # Pydantic schemas (InvestigationPlan, PlanStep)
│   │   ├── api_agent.py            # ReAct REST API investigation specialist
│   │   ├── sql_agent.py            # AST-safe SQL investigation specialist
│   │   ├── orchestrator.py         # Main multi-agent coordinator & router
│   │   └── investigation_state.py  # TypedDict graph state definition
│   ├── api/                        # FastAPI REST API endpoints
│   │   └── routes/                 # Customer, billing, orders, and support routes
│   ├── config.py                   # Pydantic environment configuration
│   ├── db/                         # SQLAlchemy models, sessions, and safe SQL executor
│   │   └── sql/                    # SQL AST validator & executor
│   ├── main.py                     # FastAPI application entry point
│   └── tools/                      # LangChain tool registries & HTTP clients
├── migrations/                     # Alembic database migration scripts
├── scripts/                        # Demonstration & execution scripts
│   ├── run_specialist.py           # Runs full end-to-end multi-agent investigation
│   ├── run_sql_agent.py            # Directly runs SQL specialist
│   ├── seed_database.py            # Seeds demo enterprise operational data
│   └── test_planner.py             # Tests structured plan generation
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

# Install package in editable mode
pip install -e .
```

### 4. Start Infrastructure & Seed Data

```powershell
# Start PostgreSQL, Redis, and Qdrant
docker compose up -d

# Run database migrations
alembic upgrade head

# Seed sample enterprise operational data
python .\scripts\seed_database.py
```

---

## Running the Platform

### Start the Enterprise API Server

Run the FastAPI application (provides internal REST endpoints for customer, order, billing, and support lookups):

```powershell
uvicorn app.main:app --reload
```
Interactive documentation is available at `http://127.0.0.1:8000/docs`.

### Run an End-to-End Investigation

Run the orchestrator script on a real dispute scenario (e.g. Ticket `TICK-4001` with an invoice/order discrepancy):

```powershell
python .\scripts\run_specialist.py
```

### Programmatic Usage

You can invoke the investigation pipeline directly in your services:

```python
from app.agents import run_investigation

result = run_investigation(
    "Customer reported an incorrect charge in support ticket TICK-4001. Investigate what happened."
)

print("Plan:", result["plan"])
print("Evidence:", result["evidence"])
print("Final Resolution:\n", result["final_resolution"])
```

---

## Example Investigation Output

```text
============================================================
INVESTIGATION PLAN
============================================================
{
  'goal': 'Investigate incorrect charge reported in TICK-4001',
  'steps': [
    {'step_id': 1, 'specialist': 'api', 'instruction': 'Retrieve ticket TICK-4001 details'},
    {'step_id': 2, 'specialist': 'api', 'instruction': 'Fetch invoice and order records for customer'},
    {'step_id': 3, 'specialist': 'sql', 'instruction': 'Compare order line item totals against invoice amount'}
  ]
}

============================================================
FINAL RESOLUTION
============================================================
1. Established Facts:
   - Order ORD-1001 was completed with a recorded total of 1,400.00 (Business Laptop: 1,200.00, USB-C Dock: 200.00).
   - Invoice INV-2001 was issued and paid for 1,600.00 via Payment PAY-3001.
   - A 200.00 uplift exists between the order total and the billed invoice.

2. Discrepancy Analysis:
   - No duplicate invoices or duplicate payments were identified.
   - The extra 200.00 is not reflected in any order line item.
   - The discrepancy originates at the invoice-generation stage.

3. Investigation Status:
   - Confirmed discrepancy of 200.00.
   - No business mutations executed. Recommendation forwarded to billing operations for review.
```

---

## License

This project is licensed under the Apache-2.0 License. See the [LICENSE](LICENSE) file for details.
