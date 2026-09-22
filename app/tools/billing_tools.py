from langchain_core.tools import tool

from app.config import settings
from app.tools.http_client import (
    EnterpriseAPIError,
    EnterpriseAPIClient,
)
from app.tools.schemas import InvoiceLookupInput


client = EnterpriseAPIClient(
    base_url=settings.enterprise_api_url,
)


@tool(args_schema=InvoiceLookupInput)
def get_invoice(invoice_number: str) -> dict:
    """
    Retrieve invoice information and associated
    payment records from the billing system.
    """

    try:
        return client.get(
            f"/billing/invoices/{invoice_number}"
        )

    except EnterpriseAPIError as exc:
        return {
            "success": False,
            "error": str(exc),
        }