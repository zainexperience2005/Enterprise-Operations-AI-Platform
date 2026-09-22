"""Investigation State Definition.

Defines the shared state dictionary passed across nodes in the
multi-agent investigation graph (Planner -> Specialists -> Resolution).
"""

from typing import Any, TypedDict

from app.agents.planner.schemas import InvestigationPlan


class InvestigationState(TypedDict, total=False):
    """Represents the global state for an enterprise operations investigation.

    Attributes:
        request: The initial user query or problem statement describing
            the operational issue to investigate.
        plan: The structured InvestigationPlan produced by the Planner agent.
        current_step: Zero-based index of the plan step currently being executed.
        evidence: Chronological list of collected evidence records from specialist
            executions.
        errors: Log of any execution errors or failed data retrievals encountered.
        sql_result: Output from the most recently executed SQL specialist step.
        api_result: Output from the most recently executed API specialist step.
        final_resolution: The comprehensive synthesis and conclusion produced
            by the Resolution Analyst.
        total_iterations: Total number of execution cycles across all specialist
            steps to prevent infinite loops.
    """

    request: str
    plan: InvestigationPlan
    current_step: int
    evidence: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    sql_result: str | None
    api_result: str | None
    final_resolution: str | None
    total_iterations: int