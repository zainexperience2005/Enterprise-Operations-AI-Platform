from langchain_core.tools import tool

from app.config import settings
from app.tools.http_client import (
    EnterpriseAPIError,
    EnterpriseAPIClient,
)
from app.tools.schemas import CustomerLookupInput


client = EnterpriseAPIClient(
    base_url=settings.enterprise_api_url,
)


@tool(args_schema=CustomerLookupInput)
def get_customer(customer_number: str) -> dict:
    """
    Retrieve customer information from the enterprise CRM.

    Use this tool when customer identity, status,
    name, or account information is required.
    """

    try:
        return client.get(
            f"/customers/{customer_number}"
        )

    except EnterpriseAPIError as exc:
        return {
            "success": False,
            "error": str(exc),
        }