from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.db.models import SupportTicket


router = APIRouter(
    prefix="/support",
    tags=["support"],
)


@router.get("/tickets/{ticket_number}")
def get_ticket(
    ticket_number: str,
    db: Session = Depends(get_db),
):
    statement = select(SupportTicket).where(
        SupportTicket.ticket_number == ticket_number
    )

    ticket = db.scalar(statement)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Support ticket not found",
        )

    return {
        "ticket_number": ticket.ticket_number,
        "customer_id": ticket.customer_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "status": ticket.status,
        "priority": ticket.priority,
    }