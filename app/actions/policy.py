from app.actions.schemas import (
    PolicyDecision,
    ProposedAction,
)


REFUND_APPROVAL_THRESHOLD = 100.0


def evaluate_action_policy(
    action: ProposedAction,
) -> PolicyDecision:

    if action.action_type.value == "refund":

        if action.amount <= 0:
            return PolicyDecision(
                allowed=False,
                approval_required=False,
                reason="Refund amount must be positive.",
            )

        if action.amount > REFUND_APPROVAL_THRESHOLD:
            return PolicyDecision(
                allowed=True,
                approval_required=True,
                reason=(
                    "Refund exceeds the automatic "
                    "approval threshold."
                ),
            )

        return PolicyDecision(
            allowed=True,
            approval_required=False,
            reason=(
                "Refund is within the configured "
                "automatic-action threshold."
            ),
        )

    return PolicyDecision(
        allowed=False,
        approval_required=False,
        reason="Unsupported action type.",
    )