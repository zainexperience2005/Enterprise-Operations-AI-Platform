import uuid
from app.actions.service import execute_refund, build_idempotency_key, get_redis_client


def test_refund_idempotency_prevents_duplicate_execution():
    """Ensure duplicate refund executions return cached receipt without duplicate side-effects."""
    unique_id = f"TEST-{uuid.uuid4().hex[:8]}"
    invoice_number = "INV-2001"
    amount = 50.0

    # 1. First execution
    first_res = execute_refund(
        investigation_id=unique_id,
        invoice_number=invoice_number,
        amount=amount,
    )

    assert first_res["status"] == "completed"
    assert first_res.get("idempotent_replay") is not True

    # 2. Second execution with identical parameters
    second_res = execute_refund(
        investigation_id=unique_id,
        invoice_number=invoice_number,
        amount=amount,
    )

    assert second_res["status"] == "completed"
    assert second_res["refund_id"] == first_res["refund_id"]
    assert second_res.get("idempotent_replay") is True
