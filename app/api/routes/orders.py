from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_db
from app.db.models import Order


router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)


@router.get("/{order_number}")
def get_order(
    order_number: str,
    db: Session = Depends(get_db),
):
    statement = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number)
    )

    order = db.scalar(statement)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return {
        "order_number": order.order_number,
        "customer_id": order.customer_id,
        "status": order.status,
        "total_amount": float(order.total_amount),
        "items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
            }
            for item in order.items
        ],
    }