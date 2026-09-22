"""Investigation Planner Implementation.

Instantiates the ChatOpenAI model bound with structured output
to parse high-level operational requests into an actionable InvestigationPlan.
"""

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
) -> InvestigationPlan:
    """Create a structured, multi-step investigation plan from a user query.

    Args:
        user_request: High-level business inquiry or incident description
            (e.g., ticket ID or complaint description).

    Returns:
        InvestigationPlan: An ordered sequence of PlanSteps assigned to
            specialized agents (API or SQL).
    """
    return structured_planner.invoke(
        [
            SystemMessage(
                content=PLANNER_SYSTEM_PROMPT
            ),
            HumanMessage(
                content=user_request
            ),
        ]
    )