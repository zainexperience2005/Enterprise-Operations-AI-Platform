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
from langgraph.types import interrupt

from app.actions import (
    evaluate_action_policy,
    execute_action,
)
from app.agents.actions_proposer import propose_action
from app.agents.api_agent import run_api_specialist
from app.agents.evaluator import evaluate_evidence
from app.agents.investigation_state import InvestigationState
from app.agents.planner.planner import create_investigation_plan
from app.agents.planner.schemas import InvestigationPlan, PlanStep
from app.agents.rag_agent import run_rag_specialist
from app.agents.sql_agent import run_sql_specialist
from app.memory.service import (
    load_memory_context,
    save_resolution_memory,
)
from app.reliability import evidence_fingerprint
from app.security.audit import record_audit_event

# ----------------------------------------------------------------------------
# System Configuration & Safety Guardrails
# ----------------------------------------------------------------------------

# Maximum number of specialist steps allowed before forced termination.
# Prevents unbounded loops in cyclic routing graphs.
MAX_INVESTIGATION_STEPS = 15

# Loop Engineering: Bounded correction budgets and stagnation limits
MAX_CORRECTION_LOOPS = 3
MAX_SPECIALIST_CALLS = 10
MAX_STAGNATION = 2

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
        "correction_count": state.get("correction_count", 0),
        "specialist_call_count": state.get("specialist_call_count", 0),
        "stagnation_count": state.get("stagnation_count", 0),
        "previous_evidence_fingerprints": list(state.get("previous_evidence_fingerprints", [])),
        "last_evidence_fingerprint": state.get("last_evidence_fingerprint"),
        "loop_status": state.get("loop_status", "in_progress"),
    }


def route_next_step(
    state: InvestigationState,
) -> str:
    """Graph Conditional Router: Dynamically selects the next node to execute.

    Routing Decisions:
    1. If plan is missing or empty -> route to "evidence_evaluator".
    2. If `current_step` >= number of plan steps -> route to "evidence_evaluator".
    3. If `total_iterations` >= `MAX_INVESTIGATION_STEPS` -> route to "evidence_evaluator" (safety brake).
    4. Otherwise, inspects `plan.steps[current_step].specialist`:
       - "api"  -> routes to "api" specialist node.
       - "sql"  -> routes to "sql" specialist node.
       - "rag"  -> routes to "rag" specialist node.
       - other  -> routes to "evidence_evaluator".

    Args:
        state: Current investigation state.

    Returns:
        str: Next node key ('api', 'sql', 'rag', or 'evidence_evaluator').
    """
    plan = state.get("plan")
    if not plan or not plan.steps:
        return "evidence_evaluator"

    current_step = state.get("current_step", 0)
    total_iterations = state.get("total_iterations", 0)

    # Route to evidence evaluator if all steps are completed or iteration limit reached
    if current_step >= len(plan.steps) or total_iterations >= MAX_INVESTIGATION_STEPS:
        return "evidence_evaluator"

    step = plan.steps[current_step]

    if step.specialist in ("sql", "api", "rag"):
        return step.specialist

    return "evidence_evaluator"


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
        "specialist_call_count": state.get("specialist_call_count", 0) + 1,
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
        "specialist_call_count": state.get("specialist_call_count", 0) + 1,
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
        "specialist_call_count": state.get("specialist_call_count", 0) + 1,
    }


# ============================================================================
# Graph Nodes: Loop Engineering (Evidence Evaluation & Correction)
# ============================================================================

def evidence_evaluator_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Evaluates accumulated evidence against the original goal.

    Calculates evidence fingerprint to detect stagnation across loop iterations.
    Applies structured evaluation and bounds checks (budgets, stagnation limits).
    """
    evidence_list = state.get("evidence", [])
    current_fp = evidence_fingerprint(evidence_list)
    last_fp = state.get("last_evidence_fingerprint")
    stagnation_count = state.get("stagnation_count", 0)
    prev_fingerprints = list(state.get("previous_evidence_fingerprints", []))

    if last_fp is not None and current_fp == last_fp:
        stagnation_count += 1
    else:
        stagnation_count = 0

    prev_fingerprints.append(current_fp)

    formatted_evidence = _format_evidence_for_prompt(evidence_list)
    formatted_errors = _format_errors_for_prompt(state.get("errors", []))

    evaluation = evaluate_evidence(
        request=state.get("request", ""),
        evidence=formatted_evidence,
        errors=formatted_errors,
    )
    eval_dict = evaluation.model_dump()

    # Determine loop status based on deterministic policies & budgets
    if eval_dict.get("verdict") == "sufficient":
        loop_status = "success"
    elif stagnation_count >= MAX_STAGNATION:
        loop_status = "stagnated"
    elif state.get("correction_count", 0) >= MAX_CORRECTION_LOOPS:
        loop_status = "budget_exhausted"
    elif state.get("specialist_call_count", 0) >= MAX_SPECIALIST_CALLS:
        loop_status = "budget_exhausted"
    elif eval_dict.get("recommended_specialist") in (None, "none"):
        loop_status = "insufficient"
    else:
        loop_status = "correcting"

    return {
        "evaluation": eval_dict,
        "stagnation_count": stagnation_count,
        "last_evidence_fingerprint": current_fp,
        "previous_evidence_fingerprints": prev_fingerprints,
        "loop_status": loop_status,
    }


def route_after_evaluation(
    state: InvestigationState,
) -> str:
    """Graph Conditional Router: Routes after evidence evaluation.

    Routes to 'correction' if gaps exist and budget remains.
    Otherwise routes to 'resolution'.
    """
    loop_status = state.get("loop_status")
    if loop_status == "correcting":
        return "correction"

    return "resolution"


def correction_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Creates a targeted, single-step plan to close the identified evidence gap."""
    evaluation = state.get("evaluation") or {}
    specialist = evaluation.get("recommended_specialist", "api")
    instruction = evaluation.get("recommended_instruction") or "Investigate missing evidence."
    correction_count = state.get("correction_count", 0) + 1

    step_id = len(state.get("evidence", [])) + 1
    correction_plan = InvestigationPlan(
        goal=state.get("request", ""),
        steps=[
            PlanStep(
                step_id=step_id,
                specialist=specialist if specialist in ("api", "sql", "rag") else "api",
                instruction=instruction,
                reason="Corrective step requested by evidence evaluator.",
            )
        ],
    )

    return {
        "correction_count": correction_count,
        "loop_status": "correcting",
        "plan": correction_plan,
        "current_step": 0,
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


def route_after_resolution(
    state: InvestigationState,
) -> str:
    """Graph Conditional Router: Routes after resolution synthesis.

    If loop stopped due to budget exhaustion, stagnation, dependency failure,
    or insufficient evidence, prevent financial action proposal and route
    directly to memory_writer.
    """
    if state.get("loop_status") in {
        "budget_exhausted",
        "stagnated",
        "dependency_failure",
        "insufficient",
    }:
        return "memory_writer"

    return "action_proposal"


def action_proposal_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Evaluates evidence & resolution to propose a structured business action."""
    evidence = _format_evidence_for_prompt(
        state.get("evidence", [])
    )
    investigation_id = state.get("investigation_id", "unknown-investigation")

    proposal = propose_action(
        request=state.get("request", ""),
        evidence=evidence,
        resolution=state.get(
            "final_resolution",
            "",
        ),
    )

    if proposal.should_act and proposal.action:
        record_audit_event(
            investigation_id=investigation_id,
            event_type="ACTION_PROPOSED",
            actor="action_proposer",
            details={
                "action": proposal.action.model_dump(),
                "explanation": proposal.explanation,
            },
        )
        return {"proposed_action": proposal.action}

    return {"proposed_action": None}


def policy_gate_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Applies deterministic Python policy rules to evaluate the proposed action."""
    action = state.get("proposed_action")
    investigation_id = state.get("investigation_id", "unknown-investigation")

    if action is None:
        return {
            "approval_required": False,
            "approval_status": "not_required",
        }

    decision = evaluate_action_policy(action)

    record_audit_event(
        investigation_id=investigation_id,
        event_type="POLICY_CHECKED",
        actor="policy_engine",
        details=decision.model_dump(),
    )

    if not decision.allowed:
        return {
            "approval_required": False,
            "approval_status": "blocked",
        }

    if decision.approval_required:
        record_audit_event(
            investigation_id=investigation_id,
            event_type="APPROVAL_REQUESTED",
            actor="policy_engine",
            details={
                "reason": decision.reason,
                "action": action.model_dump(),
            },
        )
        return {
            "approval_required": True,
            "approval_status": "pending",
        }

    return {
        "approval_required": False,
        "approval_status": "not_required",
    }


def approval_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Interrupts execution to request human approval via LangGraph interrupt."""
    action = state.get("proposed_action")
    investigation_id = state.get("investigation_id", "unknown-investigation")

    if action is None:
        return {
            "approval_status": "not_required"
        }

    decision = interrupt(
        {
            "type": "human_approval_required",
            "action": action.model_dump(),
            "message": "This action requires human approval.",
        }
    )

    approved = bool(decision.get("approved", False))
    approver = decision.get("approved_by", "human_reviewer")

    event_type = "ACTION_APPROVED" if approved else "ACTION_REJECTED"
    record_audit_event(
        investigation_id=investigation_id,
        event_type=event_type,
        actor=approver,
        details={
            "approved": approved,
            "action": action.model_dump(),
            "feedback": decision.get("feedback", ""),
        },
    )

    return {
        "approval_status": (
            "approved"
            if approved
            else "rejected"
        )
    }


def executor_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph Node: Executes authorized business actions with defense-in-depth validation."""
    action = state.get("proposed_action")
    investigation_id = state.get("investigation_id", "unknown-investigation")

    if action is None:
        return {
            "action_result": {
                "success": False,
                "error": "No action supplied.",
            }
        }

    # Defense in depth: Verify authorization before executing financial mutations
    if state.get("approval_required"):
        if state.get("approval_status") != "approved":
            record_audit_event(
                investigation_id=investigation_id,
                event_type="ACTION_FAILED",
                actor="executor",
                details="Attempted execution without required human approval.",
            )
            return {
                "action_result": {
                    "success": False,
                    "error": "Required human approval missing or rejected.",
                }
            }

    try:
        result = execute_action(
            action=action,
            investigation_id=investigation_id,
        )
        return {"action_result": result}
    except Exception as exc:
        record_audit_event(
            investigation_id=investigation_id,
            event_type="ACTION_FAILED",
            actor="executor",
            details={"error": str(exc)},
        )
        return {
            "action_result": {
                "success": False,
                "error": str(exc),
            }
        }


def route_after_policy(
    state: InvestigationState,
) -> str:
    """Route after policy gate: approval, executor, or terminal memory writer."""
    if state.get("proposed_action") is None:
        return "memory_writer"

    status = state.get("approval_status")
    if status == "blocked":
        return "memory_writer"

    if state.get("approval_required", False):
        return "approval"

    return "executor"


def route_after_approval(
    state: InvestigationState,
) -> str:
    """Route after approval: executor if approved, otherwise memory writer."""
    if state.get("approval_status") == "approved":
        return "executor"

    return "memory_writer"


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
builder.add_node("evidence_evaluator", evidence_evaluator_node)
builder.add_node("correction", correction_node)
builder.add_node("resolution", resolution_node)
builder.add_node("action_proposal", action_proposal_node)
builder.add_node("policy_gate", policy_gate_node)
builder.add_node("approval", approval_node)
builder.add_node("executor", executor_node)
builder.add_node("memory_writer", memory_writer_node)

# Entry Point: Initialize pipeline through memory loader then planner
builder.add_edge(START, "memory_loader")
builder.add_edge("memory_loader", "planner")

# Conditional routing table mapping specialist/step router output to target node
STEP_ROUTING = {
    "api": "api",
    "sql": "sql",
    "rag": "rag",
    "evidence_evaluator": "evidence_evaluator",
}

# Dynamic conditional edges between specialists and correction:
builder.add_conditional_edges("planner", route_next_step, STEP_ROUTING)
builder.add_conditional_edges("api", route_next_step, STEP_ROUTING)
builder.add_conditional_edges("sql", route_next_step, STEP_ROUTING)
builder.add_conditional_edges("rag", route_next_step, STEP_ROUTING)
builder.add_conditional_edges("correction", route_next_step, STEP_ROUTING)

# Dynamic conditional edges from Evidence Evaluator (resolution vs correction loop):
EVALUATION_ROUTING = {
    "resolution": "resolution",
    "correction": "correction",
}
builder.add_conditional_edges("evidence_evaluator", route_after_evaluation, EVALUATION_ROUTING)

# Resolution conditional branch (Action Proposer vs terminal Memory Writer if halted):
RESOLUTION_ROUTING = {
    "action_proposal": "action_proposal",
    "memory_writer": "memory_writer",
}
builder.add_conditional_edges("resolution", route_after_resolution, RESOLUTION_ROUTING)
builder.add_edge("action_proposal", "policy_gate")

# Policy Gate dynamic branch:
POLICY_ROUTING = {
    "approval": "approval",
    "executor": "executor",
    "memory_writer": "memory_writer",
}
builder.add_conditional_edges("policy_gate", route_after_policy, POLICY_ROUTING)

# Approval dynamic branch:
APPROVAL_ROUTING = {
    "executor": "executor",
    "memory_writer": "memory_writer",
}
builder.add_conditional_edges("approval", route_after_approval, APPROVAL_ROUTING)

# Executor -> Memory Writer -> END
builder.add_edge("executor", "memory_writer")
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
    recursion_limit: int = 50,
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