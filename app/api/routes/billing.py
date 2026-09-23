from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_db
from app.db.models import Invoice


router = APIRouter(
    prefix="/billing",
    tags=["billing"],
)


@router.get("/invoices/{invoice_number}")
def get_invoice(
    invoice_number: str,
    db: Session = Depends(get_db),
):
    statement = (
        select(Invoice)
        .options(selectinload(Invoice.payments))
        .where(Invoice.invoice_number == invoice_number)
    )

    invoice = db.scalar(statement)

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    return {
        "invoice_number": invoice.invoice_number,
        "customer_id": invoice.customer_id,
        "order_id": invoice.order_id,
        "amount": float(invoice.amount),
        "status": invoice.status,
        "payments": [
            {
                "payment_reference": payment.payment_reference,
                "amount": float(payment.amount),
                "status": payment.status,
            }
            for payment in invoice.payments
        ],
    }


class RefundRequest(BaseModel):
    invoice_number: str
    amount: float
    idempotency_key: str


@router.post("/refunds")
def create_refund(
    request: RefundRequest,
    db: Session = Depends(get_db),
):
    statement = select(Invoice).where(
        Invoice.invoice_number == request.invoice_number
    )
    invoice = db.scalar(statement)

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    # In our mock enterprise billing system, we generate a confirmation ID
    refund_id = f"REFUND-{invoice.id}-{int(request.amount)}"

    return {
        "refund_id": refund_id,
        "invoice_number": invoice.invoice_number,
        "amount": request.amount,
        "status": "completed",
        "idempotency_key": request.idempotency_key,
    }