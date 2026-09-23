from typing import Any, TypedDict

from app.actions import ProposedAction


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

    # Loop Engineering
    evaluation: dict[str, Any] | None
    correction_count: int
    specialist_call_count: int
    previous_evidence_fingerprints: list[str]
    stagnation_count: int
    last_evidence_fingerprint: str | None
    loop_status: str | None