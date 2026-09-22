from pydantic import BaseModel, Field


class CustomerLookupInput(BaseModel):
    customer_number: str = Field(
        description="Unique customer number, for example CUST-001"
    )


class OrderLookupInput(BaseModel):
    order_number: str = Field(
        description="Unique order number, for example ORD-1001"
    )


class InvoiceLookupInput(BaseModel):
    invoice_number: str = Field(
        description="Unique invoice number, for example INV-2001"
    )


class SupportTicketLookupInput(BaseModel):
    ticket_number: str = Field(
        description="Unique support ticket number, for example TICK-4001"
    )