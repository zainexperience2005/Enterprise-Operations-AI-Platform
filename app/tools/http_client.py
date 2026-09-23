import random
import time
from typing import Any

import httpx

from app.config import settings

# Explicit transient status codes eligible for retry
RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


class EnterpriseAPIError(Exception):
    """Base exception for enterprise API failures."""


class EnterpriseNotFoundError(EnterpriseAPIError):
    """Requested enterprise resource does not exist (HTTP 404 - permanent)."""


# Backward-compatible alias for existing tool imports
ResourceNotFoundError = EnterpriseNotFoundError


class EnterpriseTemporaryError(EnterpriseAPIError):
    """Temporary API failure eligible for retry with backoff."""


class EnterpriseAPIUnavailableError(EnterpriseAPIError):
    """Enterprise API is unavailable after exhausting retry attempts."""


class EnterpriseAPIClient:
    """HTTP client for enterprise REST APIs with exponential backoff and jitter."""

    def __init__(
        self,
        base_url: str,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = (
            timeout if timeout is not None else settings.http_timeout_seconds
        )
        self.max_retries = (
            max_retries if max_retries is not None else settings.http_max_retries
        )
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def get(self, path: str) -> dict[str, Any]:
        """Perform a GET request with exponential backoff and jitter on transient errors.

        Args:
            path: Relative API endpoint path (e.g. '/customers/CUST-1001').

        Returns:
            dict[str, Any]: Parsed JSON response payload.

        Raises:
            EnterpriseNotFoundError: When endpoint returns 404 (non-retryable).
            EnterpriseAPIUnavailableError: When max retries are exceeded on transient failures.
            EnterpriseAPIError: On unexpected HTTP client/server errors.
        """
        path = "/" + path.lstrip("/")

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.get(path)

                # 404 Not Found is a permanent domain error - DO NOT retry
                if response.status_code == 404:
                    raise EnterpriseNotFoundError(
                        f"Resource not found: {path}"
                    )

                # Transient errors eligible for retry
                if response.status_code in RETRYABLE_STATUS_CODES:
                    raise EnterpriseTemporaryError(
                        f"Temporary API failure: {response.status_code}"
                    )

                response.raise_for_status()
                return response.json()

            except EnterpriseNotFoundError:
                raise

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                EnterpriseTemporaryError,
            ) as exc:
                if attempt >= self.max_retries:
                    raise EnterpriseAPIUnavailableError(
                        f"Enterprise API unavailable after {self.max_retries} retries: {path}"
                    ) from exc

                # Exponential backoff with jitter to prevent thundering herd
                delay = (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(delay)

            except httpx.HTTPStatusError as exc:
                raise EnterpriseAPIError(
                    f"Enterprise API returned HTTP {exc.response.status_code}"
                ) from exc

        raise EnterpriseAPIUnavailableError(
            f"Enterprise API unavailable: {path}"
        )