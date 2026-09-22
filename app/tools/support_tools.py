from langchain_core.tools import tool

from app.config import settings
from app.tools.http_client import (
    EnterpriseAPIError,
    EnterpriseAPIClient,
)
from app.tools.schemas import SupportTicketLookupInput


client = EnterpriseAPIClient(
    base_url=settings.enterprise_api_url,
)


@tool(args_schema=SupportTicketLookupInput)
def get_support_ticket(ticket_number: str) -> dict:
    """
    Retrieve a support ticket including the
    customer complaint, priority and status.
    """

    try:
        return client.get(
            f"/support/tickets/{ticket_number}"
        )

    except EnterpriseAPIError as exc:
        return {
            "success": False,
            "error": str(exc),
        }