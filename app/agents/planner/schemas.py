"""Investigation Planner Pydantic Schemas.

Defines the structured output contracts for the investigation planner,
ensuring strict type validation for plan steps and specialist delegation.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Supported investigation specialists in the multi-agent graph
SpecialistType = Literal[
    "sql",
    "api",
    "rag"
]


class PlanStep(BaseModel):
    """Represents a single atomic step in an investigation plan.

    Attributes:
        step_id: Sequential 1-based index of the step.
        specialist: The dedicated domain specialist responsible for this step
            ("api" for entity fetching, "sql" for relational joins & calculations).
        instruction: Clear, actionable prompt directed to the assigned specialist.
        reason: Justification explaining how this step helps resolve the investigation.
    """

    step_id: int = Field(
        description="Sequential identifier for the plan step."
    )

    specialist: SpecialistType = Field(
        description="Specialist responsible for executing this step."
    )

    instruction: str = Field(
        description="Specific investigation instruction."
    )

    reason: str = Field(
        description="Why this step is necessary."
    )


class InvestigationPlan(BaseModel):
    """Structured container for the entire generated investigation roadmap.

    Attributes:
        goal: Summary of the primary operational question to be investigated.
        steps: Ordered list of discrete PlanStep items to execute sequentially.
    """

    goal: str = Field(
        description="Primary investigation goal."
    )

    steps: list[PlanStep] = Field(
        description="Ordered investigation steps."
    )