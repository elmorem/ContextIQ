"""Base HTTP client with retry logic and error handling."""

import asyncio
import logging
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from shared.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseHTTPClient:
    """Base HTTP client with retry logic, timeout handling, and error management."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL for the service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: Request path (will be appended to base_url)
            **kwargs: Additional arguments to pass to httpx request

        Returns:
            httpx.Response object

        Raises:
            ServiceUnavailableError: If service is unavailable after retries
            httpx.HTTPStatusError: If response has error status code
        """
        client = await self._get_client()
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                return response

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Request to {self.base_url}{path} failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(
                        f"Request to {self.base_url}{path} failed after {self.max_retries} attempts"
                    )

            except httpx.HTTPStatusError as e:
                # Don't retry on client errors (4xx), only on server errors (5xx)
                if e.response.status_code < 500:
                    raise
                last_exception = e
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Server error {e.response.status_code} for {self.base_url}{path} (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(
                        f"Server error {e.response.status_code} for {self.base_url}{path} after {self.max_retries} attempts"
                    )

        raise ServiceUnavailableError(
            f"Service at {self.base_url} is unavailable after {self.max_retries} attempts: {last_exception}"
        )

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """
        Make GET request.

        Args:
            path: Request path
            params: Query parameters
            headers: Additional headers

        Returns:
            HTTP response
        """
        return await self._request_with_retry(
            "GET",
            path,
            params=params,
            headers=headers,
        )

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """
        Make POST request.

        Args:
            path: Request path
            json: JSON body
            data: Form data
            headers: Additional headers

        Returns:
            HTTP response
        """
        return await self._request_with_retry(
            "POST",
            path,
            json=json,
            data=data,
            headers=headers,
        )

    async def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """
        Make PUT request.

        Args:
            path: Request path
            json: JSON body
            headers: Additional headers

        Returns:
            HTTP response
        """
        return await self._request_with_retry(
            "PUT",
            path,
            json=json,
            headers=headers,
        )

    async def patch(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """
        Make PATCH request.

        Args:
            path: Request path
            json: JSON body
            headers: Additional headers

        Returns:
            HTTP response
        """
        return await self._request_with_retry(
            "PATCH",
            path,
            json=json,
            headers=headers,
        )

    async def delete(
        self,
        path: str,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """
        Make DELETE request.

        Args:
            path: Request path
            headers: Additional headers

        Returns:
            HTTP response
        """
        return await self._request_with_retry(
            "DELETE",
            path,
            headers=headers,
        )
