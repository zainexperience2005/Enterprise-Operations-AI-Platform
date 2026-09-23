"""Investigation Planner Implementation.

Instantiates the ChatOpenAI model bound with structured output
to parse high-level operational requests into an actionable InvestigationPlan.
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.planner.prompt import PLANNER_SYSTEM_PROMPT
from app.agents.planner.schemas import InvestigationPlan

# Deterministic model instance dedicated to structured planning
planner_model = ChatOpenAI(
    model="gpt-5.1",
    temperature=0,
)

# Bind InvestigationPlan schema for guaranteed Pydantic output validation
structured_planner = planner_model.with_structured_output(
    InvestigationPlan
)


def create_investigation_plan(
    user_request: str,
    memory_context: list[dict[str, Any]] | None = None,
) -> InvestigationPlan:
    """Create a structured, multi-step investigation plan from a user query.

    Deconstructs an operational issue or ticket into an ordered sequence of
    targeted investigation steps assigned to specialized agents (API, SQL, RAG).

    Args:
        user_request: High-level business inquiry or incident description
            (e.g., ticket ID or complaint description).
        memory_context: Historical memories from prior investigations for the same
            ticket/incident, giving the planner awareness of past resolutions or notes.

    Returns:
        InvestigationPlan: An ordered sequence of PlanSteps assigned to
            specialized agents (API, SQL, or RAG).
    """
    human_content = user_request

    # If historical memory exists, provide it as background context to the planner
    if memory_context:
        formatted_memories = "\n".join(
            f"- [{m.get('memory_type', 'note')}]: {m.get('content', '')}"
            for m in memory_context
        )
        human_content = (
            f"User Request:\n{user_request}\n\n"
            f"Historical Investigation Memory (Context Only):\n{formatted_memories}"
        )

    return structured_planner.invoke(
        [
            SystemMessage(
                content=PLANNER_SYSTEM_PROMPT
            ),
            HumanMessage(
                content=human_content
            ),
        ]
    )