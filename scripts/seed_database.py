import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
from decimal import Decimal

from app.db import (
    Customer,
    Invoice,
    Order,
    OrderItem,
    Payment,
    SupportTicket,
    SessionLocal
)


def seed():
    db = SessionLocal()

    try:
        existing = db.query(Customer).first()

        if existing:
            print("Database already contains data.")
            return

        customer = Customer(
            customer_number="CUST-001",
            name="Ahmad Khan",
            email="ahmad@example.com",
            status="active",
        )

        db.add(customer)
        db.flush()

        order = Order(
            order_number="ORD-1001",
            customer_id=customer.id,
            status="completed",
            total_amount=Decimal("1400.00"),
        )

        db.add(order)
        db.flush()

        db.add_all(
            [
                OrderItem(
                    order_id=order.id,
                    product_name="Business Laptop",
                    quantity=1,
                    unit_price=Decimal("1200.00"),
                ),
                OrderItem(
                    order_id=order.id,
                    product_name="USB-C Dock",
                    quantity=1,
                    unit_price=Decimal("200.00"),
                ),
            ]
        )

        invoice = Invoice(
            invoice_number="INV-2001",
            customer_id=customer.id,
            order_id=order.id,

            # Deliberate problem:
            amount=Decimal("1600.00"),

            status="paid",
        )

        db.add(invoice)
        db.flush()

        payment = Payment(
            payment_reference="PAY-3001",
            invoice_id=invoice.id,
            amount=Decimal("1600.00"),
            status="completed",
            paid_at=datetime.utcnow(),
        )

        ticket = SupportTicket(
            ticket_number="TICK-4001",
            customer_id=customer.id,
            subject="Incorrect invoice amount",
            description=(
                "Customer reports being charged more "
                "than the original order total."
            ),
            status="open",
            priority="high",
        )

        db.add_all([payment, ticket])

        db.commit()

        print("Database seeded successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()