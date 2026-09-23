import httpx
import pytest
import respx

from app.tools.http_client import (
    EnterpriseAPIClient,
    EnterpriseAPIUnavailableError,
    EnterpriseNotFoundError,
)


@respx.mock
def test_retries_transient_503_and_succeeds():
    """Test that transient HTTP 503 triggers exponential backoff and succeeds on retry."""
    client = EnterpriseAPIClient(
        base_url="http://testserver",
        timeout=2.0,
        max_retries=2,
    )

    route = respx.get("http://testserver/customers/CUST-1001")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json={"customer_number": "CUST-1001", "name": "Acme Corp"}),
    ]

    data = client.get("/customers/CUST-1001")

    assert data["customer_number"] == "CUST-1001"
    assert route.call_count == 2


@respx.mock
def test_does_not_retry_permanent_404():
    """Test that permanent HTTP 404 does NOT retry and fails immediately."""
    client = EnterpriseAPIClient(
        base_url="http://testserver",
        timeout=2.0,
        max_retries=2,
    )

    route = respx.get("http://testserver/customers/NON-EXISTENT")
    route.return_value = httpx.Response(404)

    with pytest.raises(EnterpriseNotFoundError):
        client.get("/customers/NON-EXISTENT")

    # Assert exactly 1 call was made (no futile retries on 404)
    assert route.call_count == 1


@respx.mock
def test_raises_unavailable_after_exhausting_retries():
    """Test that persistent 500/503 raises EnterpriseAPIUnavailableError after max retries."""
    client = EnterpriseAPIClient(
        base_url="http://testserver",
        timeout=2.0,
        max_retries=2,
    )

    route = respx.get("http://testserver/invoices/INV-9999")
    route.return_value = httpx.Response(503)

    with pytest.raises(EnterpriseAPIUnavailableError):
        client.get("/invoices/INV-9999")

    # Initial attempt + 2 retries = 3 calls
    assert route.call_count == 3


@respx.mock
def test_retries_rate_limit_429():
    """Test that rate limit HTTP 429 is treated as transient and retried."""
    client = EnterpriseAPIClient(
        base_url="http://testserver",
        timeout=2.0,
        max_retries=2,
    )

    route = respx.get("http://testserver/orders/ORD-1001")
    route.side_effect = [
        httpx.Response(429),
        httpx.Response(200, json={"order_number": "ORD-1001", "total_amount": 1400.0}),
    ]

    data = client.get("/orders/ORD-1001")
    assert data["order_number"] == "ORD-1001"
    assert route.call_count == 2
