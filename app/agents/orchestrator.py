"""Investigation Orchestrator.

Orchestrates multi-agent incident investigations by coordinating:
1. Planner Agent: Deconstructs the business incident into discrete tasks.
2. Specialist Agents (API, SQL): Executes steps sequentially while accumulating factual evidence.
3. Resolution Analyst: Synthesizes gathered evidence and errors into a definitive operational conclusion.
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.agents.api_agent import run_api_specialist
from app.agents.investigation_state import InvestigationState
from app.agents.planner.planner import create_investigation_plan
from app.agents.sql_agent import run_sql_specialist
from app.agents.rag_agent import run_rag_specialist

# Safety ceiling to prevent unbounded execution loops
MAX_INVESTIGATION_STEPS = 15

# Resolution model synthesizing evidence into a conclusive report
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


def _format_evidence_for_prompt(evidence: list[dict[str, Any]]) -> str:
    """Format structured evidence records into clean, readable text for prompts.

    Args:
        evidence: List of dictionaries with step_id, specialist, instruction, and result.

    Returns:
        str: Formatted markdown string representing the evidence log.
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

    Args:
        errors: List of dictionaries detailing failed steps and exception messages.

    Returns:
        str: Bulleted markdown string of errors.
    """
    if not errors:
        return "None"

    return "\n".join(
        f"- Step {err.get('step_id', '?')} [{err.get('specialist', 'unknown')}]: {err.get('error', '')}"
        for err in errors
    )


def build_specialist_context(
    state: InvestigationState,
    instruction: str,
) -> str:
    """Construct contextual prompt containing past evidence for the next specialist step.

    Args:
        state: Current investigation state containing prior evidence and request.
        instruction: Specific instruction assigned to the specialist.

    Returns:
        str: Fully formatted prompt string with background and clear boundary rules.
    """
    formatted_evidence = _format_evidence_for_prompt(
        state.get("evidence", [])
    )

    return f"""Original investigation request:

{state.get("request", "")}

Current instruction:

{instruction}

Evidence collected by previous specialists:

{formatted_evidence}

Perform only your assigned investigation task.
Return factual evidence, not unsupported assumptions.
"""


def planner_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph node: Generates or adopts an investigation plan for the request.

    If a pre-constructed plan is already present in state, it is reused.
    Otherwise, invokes the planner LLM to decompose the inquiry into structured steps.
    """
    plan = state.get("plan")
    errors: list[dict[str, Any]] = list(state.get("errors", []))

    if not plan:
        try:
            plan = create_investigation_plan(state["request"])
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
    """Graph router: Selects the next node ('api', 'sql', or 'resolution').

    Transitions to 'resolution' when all steps are completed, the iteration
    limit is reached, or the plan is invalid.
    """
    plan = state.get("plan")
    if not plan or not plan.steps:
        return "resolution"

    current_step = state.get("current_step", 0)
    total_iterations = state.get("total_iterations", 0)

    # Terminate to resolution if all steps are done or iteration limit is reached
    if current_step >= len(plan.steps) or total_iterations >= MAX_INVESTIGATION_STEPS:
        return "resolution"

    step = plan.steps[current_step]

    if step.specialist in ("sql", "api", "rag"):
        return step.specialist

    return "resolution"


def api_specialist_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph node: Executes an API specialist step and logs evidence or errors."""
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

    # Execute specialist with error trapping to prevent graph collapse
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
    """Graph node: Executes an SQL specialist step and logs evidence or errors."""
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

    # Execute specialist with error trapping to prevent graph collapse
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

    plan = state.get("plan")
    current_step = state.get(
        "current_step",
        0,
    )

    evidence = list(
        state.get("evidence", [])
    )

    errors = list(
        state.get("errors", [])
    )

    if not plan or current_step >= len(plan.steps):
        return {
            "current_step": current_step,
            "total_iterations": state.get(
                "total_iterations",
                0,
            ),
        }

    step = plan.steps[current_step]

    try:
        context = build_specialist_context(
            state,
            step.instruction,
        )

        result = run_rag_specialist(
            context
        )

    except Exception as exc:
        result = (
            "Error during RAG specialist "
            f"execution: {str(exc)}"
        )

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
        "evidence": evidence,
        "errors": errors,
        "current_step": current_step + 1,
        "total_iterations": (
            state.get(
                "total_iterations",
                0,
            )
            + 1
        ),
    }

def resolution_node(
    state: InvestigationState,
) -> dict[str, Any]:
    """Graph node: Resolution Analyst synthesizes evidence and errors into a conclusion."""
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
# StateGraph Assembly
# ============================================================================
builder = StateGraph(InvestigationState)

# Register investigation nodes
builder.add_node("planner", planner_node)
builder.add_node("api", api_specialist_node)
builder.add_node("sql", sql_specialist_node)
builder.add_node("resolution", resolution_node)
builder.add_node(
    "rag",
    rag_specialist_node,
)
# Entry point
builder.add_edge(START, "planner")

# Conditional routing table
STEP_ROUTING = {
    "api": "api",
    "sql": "sql",
    "rag": "rag",
    "resolution": "resolution",
}

# Dynamic step execution edges
builder.add_conditional_edges("planner", route_next_step, STEP_ROUTING)
builder.add_conditional_edges("api", route_next_step, STEP_ROUTING)
builder.add_conditional_edges("sql", route_next_step, STEP_ROUTING)
builder.add_conditional_edges(
    "rag",
    route_next_step,
    STEP_ROUTING,
)
# Terminal edge
builder.add_edge("resolution", END)

# Compiled graph ready for execution
investigation_graph = builder.compile()


def run_investigation(
    request: str,
    recursion_limit: int = 25,
) -> dict[str, Any]:
    """Execute end-to-end investigation workflow for a business query.

    Args:
        request: The operational question or incident ticket prompt.
        recursion_limit: Maximum graph recursion depth before termination.

    Returns:
        dict[str, Any]: Final InvestigationState containing plan, evidence,
            and final resolution.
    """
    return investigation_graph.invoke(
        {"request": request},
        config={"recursion_limit": recursion_limit},
    )