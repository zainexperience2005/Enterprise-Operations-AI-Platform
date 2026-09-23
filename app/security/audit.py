import json
from typing import Any

from app.db.models import AuditEvent
from app.db.session import SessionLocal


def record_audit_event(
    investigation_id: str,
    event_type: str,
    actor: str,
    details: dict[str, Any] | str,
) -> AuditEvent:
    """Record an audit event to the persistent audit_events table.

    Tracks actions, policy evaluations, human approvals, and execution results
    for complete operational traceability and compliance.

    Args:
        investigation_id: Identifier of the associated investigation (e.g. 'TICK-4001').
        event_type: Action or lifecycle event name (e.g. 'ACTION_PROPOSED', 'POLICY_CHECKED').
        actor: System component or user identity responsible for the event.
        details: Payload describing event metadata, proposal, or execution response.

    Returns:
        AuditEvent: Persisted database record.
    """
    if isinstance(details, dict):
        details_text = json.dumps(details, default=str)
    else:
        details_text = str(details)

    with SessionLocal() as session:
        event = AuditEvent(
            investigation_id=investigation_id,
            event_type=event_type,
            actor=actor,
            details=details_text,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event
