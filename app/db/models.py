from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id")
    )

    status: Mapped[str] = mapped_column(String(50))

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="orders"
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order"
    )

    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="order"
    )

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)

    customer_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True)

    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer"
    )

    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="customer"
    )

    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="customer"
    )

class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id")
    )

    product_name: Mapped[str] = mapped_column(String(200))

    quantity: Mapped[int]

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    order: Mapped["Order"] = relationship(
        back_populates="items"
    )

class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)

    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id")
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id")
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    status: Mapped[str] = mapped_column(String(50))

    issued_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="invoices"
    )

    order: Mapped["Order"] = relationship(
        back_populates="invoices"
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="invoice"
    )

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    payment_reference: Mapped[str] = mapped_column(
        String(100),
        unique=True,
    )

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id")
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    status: Mapped[str] = mapped_column(String(50))

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    invoice: Mapped["Invoice"] = relationship(
        back_populates="payments"
    )

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)

    ticket_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id")
    )

    subject: Mapped[str] = mapped_column(String(250))

    description: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(50),
        default="open",
    )

    priority: Mapped[str] = mapped_column(
        String(50),
        default="normal",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="support_tickets"
    )

class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(primary_key=True)

    investigation_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
    )

    query: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(50),
        default="created",
    )

    final_resolution: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    thread_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)

    investigation_id: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )

    event_type: Mapped[str] = mapped_column(String(100))

    actor: Mapped[str] = mapped_column(String(100))

    details: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )