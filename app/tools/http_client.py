import time
from typing import Any

import httpx


class EnterpriseAPIError(Exception):
    """Base exception for enterprise API failures."""


class ResourceNotFoundError(EnterpriseAPIError):
    """Requested enterprise resource does not exist."""


class EnterpriseAPIUnavailableError(EnterpriseAPIError):
    """Enterprise API is temporarily unavailable."""


class EnterpriseAPIClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        max_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def get(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"

        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.get(
                    url,
                    timeout=self.timeout,
                )

                if response.status_code == 404:
                    raise ResourceNotFoundError(
                        f"Resource not found: {path}"
                    )

                response.raise_for_status()

                return response.json()

            except ResourceNotFoundError:
                raise

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
            ) as exc:
                if attempt == self.max_retries:
                    raise EnterpriseAPIUnavailableError(
                        f"Enterprise API unavailable: {path}"
                    ) from exc

                time.sleep(2**attempt)

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code

                if status >= 500 and attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue

                raise EnterpriseAPIError(
                    f"Enterprise API returned HTTP {status}"
                ) from exc

        raise EnterpriseAPIUnavailableError(
            f"Enterprise API unavailable: {path}"
        )