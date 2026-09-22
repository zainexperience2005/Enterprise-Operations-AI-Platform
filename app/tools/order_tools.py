from langchain_core.tools import tool

from app.config import settings
from app.tools.http_client import (
    EnterpriseAPIError,
    EnterpriseAPIClient,
)
from app.tools.schemas import OrderLookupInput


client = EnterpriseAPIClient(
    base_url=settings.enterprise_api_url,
)


@tool(args_schema=OrderLookupInput)
def get_order(order_number: str) -> dict:
    """
    Retrieve order details including status,
    total amount and line items.
    """

    try:
        return client.get(
            f"/orders/{order_number}"
        )

    except EnterpriseAPIError as exc:
        return {
            "success": False,
            "error": str(exc),
        }