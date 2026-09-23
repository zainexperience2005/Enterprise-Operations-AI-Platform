from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    REFUND = "refund"


class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class ProposedAction(BaseModel):
    action_type: ActionType

    invoice_number: str

    amount: float = Field(
        gt=0,
        description="Proposed refund amount.",
    )

    reason: str = Field(
        min_length=10,
    )

    evidence_summary: str

class PolicyDecision(BaseModel):
    allowed: bool

    approval_required: bool

    reason: str