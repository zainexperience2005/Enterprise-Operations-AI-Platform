from app.actions import ProposedAction
from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    request: str
    plan: Any

    current_step: int

    evidence: list[dict[str, Any]]
    errors: list[dict[str, Any]]

    sql_result: str | None
    api_result: str | None
    rag_result: str | None

    final_resolution: str | None

    total_iterations: int

    # Memory
    memory_context: list[dict[str, Any]]
    investigation_id: str

    proposed_action: ProposedAction | None

    approval_required: bool

    approval_status: str | None

    action_result: dict[str, Any] | None