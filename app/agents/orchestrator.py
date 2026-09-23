"""Investigation Orchestrator.

==============================================================================
ENTERPRISE OPERATIONS AI PLATFORM - MULTI-AGENT INVESTIGATION PIPELINE
==============================================================================

This module implements the central orchestration engine for autonomous enterprise
investigations using LangGraph. It coordinates specialized AI agents to investigate
complex, cross-system operational incidents (e.g., billing discrepancies, unauthorized
charges, order status mismatches) with read-only safety guardrails.

------------------------------------------------------------------------------
HIGH-LEVEL ARCHITECTURE & LIFECYCLE FLOW
------------------------------------------------------------------------------

                 +-----------------------------+
                 |            START            |
                 +-----------------------------+
                                |
                                v
                 +-----------------------------+
                 |     1. memory_loader        |  <-- Loads past episode memories
                 +-----------------------------+      for this investigation_id
                                |
                                v
                 +-----------------------------+
                 |     2. planner_node         |  <-- Decomposes incident into
                 +-----------------------------+      ordered PlanSteps (API/SQL/RAG)
                                |
            +-------------------+-------------------+
            |                                       |
            v                                       v
    +---------------+                       +---------------+
    | route_next_step| <--------------------+ Specialist    |
    +---------------+                       | Execution     |
            |                               +---------------+
            |-- (step == "api")  --> [ api_specialist_node ] ------+
            |-- (step == "sql")  --> [ sql_specialist_node ] ------+  Accumulates
            |-- (step == "rag")  --> [ rag_specialist_node ] ------+  evidence/errors
            |                                                      |  in State
            +-- (all steps completed OR max iterations)            |
            |                                                      |
            v                                                      |
    +-------------------------------+                              |
    |      3. resolution_node       | <----------------------------+
    +-------------------------------+
            |  Synthesizes evidence & errors into factual report
            v
    +-------------------------------+
    |      4. memory_writer         |  <-- Persists final resolution into
    +-------------------------------+      PostgreSQL investigation_memories
            |
            v
    +-------------------------------+
    |             END               |
    +-------------------------------+

------------------------------------------------------------------------------
CORE AGENT ROLES & RESPONSIBILITIES
------------------------------------------------------------------------------
1. Memory Loader (app/memory/service.py):
   Retrieves historical memories (prior resolutions, customer notes) tied to the
   incident ID from PostgreSQL to provide context before planning.

2. Planner Agent (app/agents/planner/):
   An LLM with structured output (InvestigationPlan schema) that analyzes the
   inquiry and formulates a concise, ordered list of steps targeted to:
   - "api": Point lookups (customer details, order items, invoices, tickets).
   - "sql": Relational analysis (joins, aggregates, numeric discrepancy checks).
   - "rag": Enterprise policy, SOP, and threshold retrieval (e.g., refund policies).

3. Specialist Execution Nodes:
   Each specialist executes its assigned step instruction in isolation, receiving
   current investigation evidence and historical memory, and appends structured
   findings to `state["evidence"]` (or exceptions to `state["errors"]`).

4. Resolution Analyst:
   A dedicated synthesis agent that consumes all accumulated evidence and errors,
   enforcing strict policy adherence:
   - Must distinguish proven facts from operational conclusions.
   - Must highlight numeric and policy discrepancies.
   - Must NEVER hallucinate data or claim business actions were executed.

5. Memory Writer:
   Commits the final resolution into long-term storage (`investigation_memories`)
   for auditability and future multi-turn context.

------------------------------------------------------------------------------
STATE MANAGEMENT & PERSISTENCE
------------------------------------------------------------------------------
- State Schema: Defined in `InvestigationState` (TypedDict).
- Checkpointing: Supports `PostgresSaver` checkpointer for thread resumption,
  audit tracking, and human-in-the-loop inspection.
==============================================================================
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.agents.api_agent import run_api_specialist
from app.agents.investigation_state import InvestigationState
from app.agents.planner.planner import create_investigation_plan
from app.agents.rag_agent import run_rag_specialist
from app.agents.sql_agent import run_sql_specialist
from app.memory.service import (
    load_memory_context,
    save_resolution_memory,
)

# ----------------------------------------------------------------------------
# System Configuration & Safety Guardrails
# ----------------------------------------------------------------------------

# Maximum number of specialist steps allowed before forced termination.
# Prevents unbounded loops in cyclic routing graphs.
MAX_INVESTIGATION_STEPS = 15

# Deterministic model instance for synthesizing conclusive incident resolutions
resolution_model = ChatOpenAI(
    model="gpt-5.1",
    temperature=0,
)

RESOLUTION_PROMPT = """
You are the Resolution Analyst for an enterprise
operations investigation system.

Your job is to synthesize evidence collected by specialist
agents.

Rules:

1. Use only the supplied evidence.
2. Never invent enterprise facts.
3. Clearly identify discrepancies.
4. Distinguish facts from conclusions.
5. If evidence is insufficient, say so.
6. Do not claim that any business action was executed.
7. Do not authorize refunds, cancellations or mutations.
8. Produce a concise investigation conclusion.
"""


# ============================================================================
# Helper Formatting Functions
# ============================================================================

def _format_evidence_for_prompt(evidence: list[dict[str, Any]]) -> str:
    """Format structured evidence records into clean, readable text for prompts.

    Transforms the chronological list of specialist step outputs into a
    structured markdown block suitable for LLM injection.

    Args:
        evidence: Chronological list of findings dictionaries containing
            `step_id`, `specialist`, `instruction`, and `result`.

    Returns:
        str: Cleanly formatted markdown string of all accumulated evidence.
    """
    if not evidence:
        return "None"

    formatted_entries: list[str] = []
    for item in evidence:
        step_id = item.get("step_id", "?")
        specialist = item.get("specialist", "unknown").upper()
        instruction = item.get("instruction", "")
        result = item.get("result", "")
        formatted_entries.append(
            f"Step {step_id} [{specialist}]: {instruction}\nFindings:\n{result}"
        )

    return "\n\n---\n\n".join(formatted_entries)


def _format_errors_for_prompt(errors: list[dict[str, Any]]) -> str:
    """Format captured errors into bullet points for the resolution prompt.

    Ensures the Resolution Analyst is transparently aware of any failed
    queries, API timeouts, or unreachable sources during the investigation.

    Args:
        errors: List of dictionaries detailing failed steps and exception messages.

    Returns:
        str: Bulleted markdown string of diagnostic errors.
    """
    if not errors:
        return "None"

    return "\n".join(
        f"- Step {err.get('step_id', '?')} [{err.get('specialist', 'unknown')}]: {err.get('error', '')}"
        for err in errors
    )


def format_memory_context(
    memories: list[dict[str, Any]],
) -> str:
    """Format historical memory records into a clear context block.

    Args:
        memories: List of previous investigation memory dictionaries
            containing `memory_type` and `content`.

    Returns:
        str: Formatted context string or fallback message if no memories exist.
    """
    if not memories:
        return "No relevant previous memory."

    entries = []
    for memory in memories:
        entries.append(
            f"Type: {memory['memory_type']}\n"
            f"Content: {memory['content']}"
        )

    return "\n\n---\n\n".join(entries)


def build_specialist_context(
    state: InvestigationState,
    instruction: str,
) -> str:
    """Construct contextual prompt containing past evidence for the next specialist step.

    Supplies the specialist agent with:
    1. The overarching user/ticket inquiry.
    2. Historical investigation memories (contextual only).
    3. The exact step instruction to execute now.
    4. Findings already gathered by previous steps in THIS investigation.

    Args:
        state: Current investigation state containing prior evidence and request.
        instruction: Specific operational instruction assigned to the specialist.

    Returns:
        str: Fully formatted prompt string with background and clear boundary rules.
    """
    formatted_evidence = _format_evidence_for_prompt(
        state.get("evidence", [])
    )

    formatted_memory = format_memory_context(
        state.get("memory_context", [])
    )

    return f"""
Original investigation request:

{state.get("request", "")}


Relevant previous investigation memory:

{formatted_memory}


Current instruction:

{instruction}


Evidence collected during the CURRENT investigation:

{formatted_evidence}


Important:

Previous memory is historical context, not automatically
current truth.

Use current enterprise evidence when available.

Perform only your assigned investigation task.

Return factual evidence, not unsupported assumptions.
"""


# ============================================================================
# Graph Nodes: Memory Management
# ============================================================================

def memory_loader_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Loads prior investigation memories from persistent storage.

    Execution Flow:
    1. Reads `state["investigation_id"]` (if provided).
    2. Queries PostgreSQL `investigation_memories` table via memory service.
    3. Populates `state["memory_context"]` for downstream nodes.

    Args:
        state: Current investigation state.

    Returns:
        dict[str, Any]: State delta containing `memory_context`.
    """
    investigation_id = state.get("investigation_id")

    if not investigation_id:
        return {"memory_context": []}

    memories = load_memory_context(investigation_id)

    return {"memory_context": memories}


def memory_writer_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Persists the synthesized resolution into long-term memory.

    Execution Flow:
    1. Extracts `investigation_id` and `final_resolution` from state.
    2. Persists the resolution as an episodic memory record in PostgreSQL.
    3. Enables future investigations on the same incident to retrieve past resolutions.

    Args:
        state: Current investigation state after resolution synthesis.

    Returns:
        dict[str, Any]: Empty state delta (terminal side-effect).
    """
    investigation_id = state.get("investigation_id")
    resolution = state.get("final_resolution")

    if not investigation_id or not resolution:
        return {}

    save_resolution_memory(
        investigation_id=investigation_id,
        resolution=resolution,
    )

    return {}


# ============================================================================
# Graph Nodes: Planning & Dynamic Routing
# ============================================================================

def planner_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Generates or adopts a structured investigation plan.

    Execution Flow:
    1. Checks if a pre-constructed `plan` was already provided in state.
    2. If not, invokes `create_investigation_plan()` using the LLM with structured output.
    3. Passes both the user inquiry and any historical `memory_context` to the planner.
    4. Initializes `current_step = 0`, `evidence = []`, and `errors = []`.

    Args:
        state: Current investigation state.

    Returns:
        dict[str, Any]: State delta containing initialized plan and tracking fields.
    """
    plan = state.get("plan")
    errors: list[dict[str, Any]] = list(state.get("errors", []))

    if not plan:
        try:
            plan = create_investigation_plan(
                user_request=state["request"],
                memory_context=state.get("memory_context", []),
            )
        except Exception as exc:
            errors.append(
                {
                    "step_id": 0,
                    "specialist": "planner",
                    "error": f"Failed to generate plan: {str(exc)}",
                }
            )

    return {
        "plan": plan,
        "current_step": 0,
        "evidence": list(state.get("evidence", [])),
        "errors": errors,
        "total_iterations": 0,
    }


def route_next_step(
    state: InvestigationState,
) -> str:
    """Graph Conditional Router: Dynamically selects the next node to execute.

    Routing Decisions:
    1. If plan is missing or empty -> route to "resolution".
    2. If `current_step` >= number of plan steps -> route to "resolution".
    3. If `total_iterations` >= `MAX_INVESTIGATION_STEPS` -> route to "resolution" (safety brake).
    4. Otherwise, inspects `plan.steps[current_step].specialist`:
       - "api"  -> routes to "api" specialist node.
       - "sql"  -> routes to "sql" specialist node.
       - "rag"  -> routes to "rag" specialist node.
       - other  -> routes to "resolution".

    Args:
        state: Current investigation state.

    Returns:
        str: Next node key ('api', 'sql', 'rag', or 'resolution').
    """
    plan = state.get("plan")
    if not plan or not plan.steps:
        return "resolution"

    current_step = state.get("current_step", 0)
    total_iterations = state.get("total_iterations", 0)

    # Terminate to resolution if all steps are completed or iteration limit reached
    if current_step >= len(plan.steps) or total_iterations >= MAX_INVESTIGATION_STEPS:
        return "resolution"

    step = plan.steps[current_step]

    if step.specialist in ("sql", "api", "rag"):
        return step.specialist

    return "resolution"


# ============================================================================
# Graph Nodes: Specialist Executors
# ============================================================================

def api_specialist_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Executes an API specialist step.

    Execution Flow:
    1. Retrieves the current step instruction from `state["plan"]`.
    2. Builds formatted context including previous evidence and historical memory.
    3. Invokes `run_api_specialist()`, which uses ReAct tool-calling to fetch
       customer, order, invoice, or ticket resources from enterprise REST APIs.
    4. Records findings in `state["evidence"]` (or errors in `state["errors"]`).
    5. Advances `current_step` by 1 and increments `total_iterations`.

    Args:
        state: Current investigation state.

    Returns:
        dict[str, Any]: State delta with updated evidence, errors, and step pointer.
    """
    plan = state.get("plan")
    current_step = state.get("current_step", 0)
    evidence = list(state.get("evidence", []))
    errors = list(state.get("errors", []))

    if not plan or current_step >= len(plan.steps):
        return {
            "current_step": current_step,
            "total_iterations": state.get("total_iterations", 0),
        }

    step = plan.steps[current_step]

    # Execute specialist with error trapping to prevent graph crashes
    try:
        context = build_specialist_context(state, step.instruction)
        result = run_api_specialist(context)
    except Exception as exc:
        result = f"Error during API specialist execution: {str(exc)}"
        errors.append(
            {
                "step_id": step.step_id,
                "specialist": "api",
                "error": str(exc),
            }
        )

    evidence.append(
        {
            "step_id": step.step_id,
            "specialist": "api",
            "instruction": step.instruction,
            "result": result,
        }
    )

    return {
        "api_result": result,
        "evidence": evidence,
        "errors": errors,
        "current_step": current_step + 1,
        "total_iterations": state.get("total_iterations", 0) + 1,
    }


def sql_specialist_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Executes an SQL specialist step.

    Execution Flow:
    1. Retrieves the current step instruction from `state["plan"]`.
    2. Builds formatted context including previous evidence and historical memory.
    3. Invokes `run_sql_specialist()`, which executes AST-validated, read-only
       PostgreSQL queries (joins, aggregations, cross-table comparisons).
    4. Records findings in `state["evidence"]` (or errors in `state["errors"]`).
    5. Advances `current_step` by 1 and increments `total_iterations`.

    Args:
        state: Current investigation state.

    Returns:
        dict[str, Any]: State delta with updated evidence, errors, and step pointer.
    """
    plan = state.get("plan")
    current_step = state.get("current_step", 0)
    evidence = list(state.get("evidence", []))
    errors = list(state.get("errors", []))

    if not plan or current_step >= len(plan.steps):
        return {
            "current_step": current_step,
            "total_iterations": state.get("total_iterations", 0),
        }

    step = plan.steps[current_step]

    # Execute specialist with error trapping to prevent graph crashes
    try:
        context = build_specialist_context(state, step.instruction)
        result = run_sql_specialist(context)
    except Exception as exc:
        result = f"Error during SQL specialist execution: {str(exc)}"
        errors.append(
            {
                "step_id": step.step_id,
                "specialist": "sql",
                "error": str(exc),
            }
        )

    evidence.append(
        {
            "step_id": step.step_id,
            "specialist": "sql",
            "instruction": step.instruction,
            "result": result,
        }
    )

    return {
        "sql_result": result,
        "evidence": evidence,
        "errors": errors,
        "current_step": current_step + 1,
        "total_iterations": state.get("total_iterations", 0) + 1,
    }


def rag_specialist_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Executes a RAG (Retrieval-Augmented Generation) specialist step.

    Execution Flow:
    1. Retrieves the current step instruction from `state["plan"]`.
    2. Builds formatted context including previous evidence and historical memory.
    3. Invokes `run_rag_specialist()`, which performs semantic search against Qdrant
       vector store to retrieve relevant enterprise policy, SOP, and threshold documents.
    4. Enforces citation format `[policy_id | source | chunk_id]`.
    5. Records findings in `state["evidence"]` (or errors in `state["errors"]`).
    6. Advances `current_step` by 1 and increments `total_iterations`.

    Args:
        state: Current investigation state.

    Returns:
        dict[str, Any]: State delta with updated evidence, errors, and step pointer.
    """
    plan = state.get("plan")
    current_step = state.get("current_step", 0)
    evidence = list(state.get("evidence", []))
    errors = list(state.get("errors", []))

    if not plan or current_step >= len(plan.steps):
        return {
            "current_step": current_step,
            "total_iterations": state.get("total_iterations", 0),
        }

    step = plan.steps[current_step]

    try:
        context = build_specialist_context(state, step.instruction)
        result = run_rag_specialist(context)
    except Exception as exc:
        result = f"Error during RAG specialist execution: {str(exc)}"
        errors.append(
            {
                "step_id": step.step_id,
                "specialist": "rag",
                "error": str(exc),
            }
        )

    evidence.append(
        {
            "step_id": step.step_id,
            "specialist": "rag",
            "instruction": step.instruction,
            "result": result,
        }
    )

    return {
        "rag_result": result,
        "evidence": evidence,
        "errors": errors,
        "current_step": current_step + 1,
        "total_iterations": state.get("total_iterations", 0) + 1,
    }


# ============================================================================
# Graph Nodes: Resolution Synthesis
# ============================================================================

def resolution_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Synthesizes gathered evidence and errors into a definitive report.

    Execution Flow:
    1. Formats all accumulated evidence from API, SQL, and RAG specialists.
    2. Formats all diagnostic errors / inaccessible systems encountered.
    3. Calls `resolution_model` (`gpt-5.1`) with `RESOLUTION_PROMPT`.
    4. The model enforces:
       - Factual grounding strictly on evidence (no hallucinations).
       - Explicit identification of financial/policy discrepancies.
       - Disclaimers that no mutations or actions have been executed.
    5. Stores the output string in `state["final_resolution"]`.

    Args:
        state: Final investigation state with completed evidence.

    Returns:
        dict[str, Any]: State delta containing `final_resolution`.
    """
    evidence = state.get("evidence", [])
    errors = state.get("errors", [])

    formatted_evidence = _format_evidence_for_prompt(evidence)
    formatted_errors = _format_errors_for_prompt(errors)

    prompt_content = f"""Original request:

{state.get("request", "")}

Investigation evidence:

{formatted_evidence}
"""

    if errors:
        prompt_content += f"""

Errors / inaccessible sources during investigation:

{formatted_errors}
"""

    prompt_content += "\nProduce the final investigation resolution."

    response = resolution_model.invoke(
        [
            SystemMessage(content=RESOLUTION_PROMPT),
            HumanMessage(content=prompt_content),
        ]
    )

    return {
        "final_resolution": response.content,
    }


# ============================================================================
# StateGraph Assembly & Compilation
# ============================================================================

# Instantiate StateGraph with TypedDict schema
builder = StateGraph(InvestigationState)

# Register investigation nodes
builder.add_node("memory_loader", memory_loader_node)
builder.add_node("planner", planner_node)
builder.add_node("api", api_specialist_node)
builder.add_node("sql", sql_specialist_node)
builder.add_node("rag", rag_specialist_node)
builder.add_node("resolution", resolution_node)
builder.add_node("memory_writer", memory_writer_node)

# Entry Point: Initialize pipeline through memory loader then planner
builder.add_edge(START, "memory_loader")
builder.add_edge("memory_loader", "planner")

# Conditional routing table mapping router output to target node
STEP_ROUTING = {
    "api": "api",
    "sql": "sql",
    "rag": "rag",
    "resolution": "resolution",
}

# Dynamic conditional edges:
# After planner or any specialist finishes, route_next_step evaluates if more steps
# remain or if we should proceed to resolution synthesis.
builder.add_conditional_edges("planner", route_next_step, STEP_ROUTING)
builder.add_conditional_edges("api", route_next_step, STEP_ROUTING)
builder.add_conditional_edges("sql", route_next_step, STEP_ROUTING)
builder.add_conditional_edges("rag", route_next_step, STEP_ROUTING)

# Terminal flow:
# resolution -> memory_writer (saves final resolution into DB) -> END
builder.add_edge("resolution", "memory_writer")
builder.add_edge("memory_writer", END)


def create_investigation_graph(
    checkpointer=None,
):
    """Compile the LangGraph investigation workflow with an optional checkpointer.

    Args:
        checkpointer: Optional LangGraph checkpointer (e.g. PostgresSaver) to
            enable state persistence, session resumption, and human-in-the-loop.

    Returns:
        CompiledStateGraph: Executable LangGraph instance ready for invocation.
    """
    return builder.compile(checkpointer=checkpointer)


# Default compiled graph instance (in-memory execution without persistence)
investigation_graph = create_investigation_graph()


# ============================================================================
# Public Execution APIs
# ============================================================================

def run_investigation(
    request: str,
    investigation_id: str | None = None,
    recursion_limit: int = 25,
) -> dict[str, Any]:
    """Execute an end-to-end investigation workflow for an operational incident.

    Args:
        request: The operational question or incident ticket prompt.
        investigation_id: Optional incident tracking ID (e.g., 'TICK-4001') to
            enable historical memory loading and resolution writing.
        recursion_limit: Maximum graph recursion depth before termination.

    Returns:
        dict[str, Any]: Final InvestigationState containing plan, evidence,
            and final resolution.
    """
    initial_state: dict[str, Any] = {"request": request}
    if investigation_id:
        initial_state["investigation_id"] = investigation_id

    return investigation_graph.invoke(
        initial_state,
        config={"recursion_limit": recursion_limit},
    )