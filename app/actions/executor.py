from app.actions.schemas import ProposedAction
from app.actions.service import execute_refund


class ActionExecutionError(Exception):
    pass


def execute_action(
    action: ProposedAction,
    investigation_id: str,
) -> dict:
    """Execute an approved business action via the domain service."""
    if action.action_type.value == "refund":
        return execute_refund(
            investigation_id=investigation_id,
            invoice_number=action.invoice_number,
            amount=action.amount,
        )

    raise ActionExecutionError(
        f"Unsupported action type: {action.action_type.value}"
    )