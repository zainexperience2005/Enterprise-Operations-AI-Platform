from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.db.models import Customer


router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)


@router.get("/{customer_number}")
def get_customer(
    customer_number: str,
    db: Session = Depends(get_db),
):
    statement = select(Customer).where(
        Customer.customer_number == customer_number
    )

    customer = db.scalar(statement)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return {
        "customer_number": customer.customer_number,
        "name": customer.name,
        "email": customer.email,
        "status": customer.status,
    }