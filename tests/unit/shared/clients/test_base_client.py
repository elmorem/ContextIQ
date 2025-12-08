"""Tests for base HTTP client."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from shared.clients.base import BaseHTTPClient
from shared.exceptions import ServiceUnavailableError


class TestBaseHTTPClient:
    """Test BaseHTTPClient functionality."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test client initialization."""
        client = BaseHTTPClient(
            base_url="http://localhost:8000",
            timeout=30,
            max_retries=3,
            retry_delay=1.0,
        )

        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.retry_delay == 1.0

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with BaseHTTPClient("http://localhost:8000") as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_get_request_success(self):
        """Test successful GET request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}

        with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=mock_response)):
            async with BaseHTTPClient("http://localhost:8000") as client:
                response = await client.get("/test")
                assert response.status_code == 200
                assert response.json() == {"result": "success"}

    @pytest.mark.asyncio
    async def test_post_request_success(self):
        """Test successful POST request."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "123"}

        with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=mock_response)):
            async with BaseHTTPClient("http://localhost:8000") as client:
                response = await client.post("/test", json={"data": "value"})
                assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """Test retry logic on timeout."""
        # First two calls timeout, third succeeds
        mock_response = Mock()
        mock_response.status_code = 200

        with patch(
            "httpx.AsyncClient.request",
            new=AsyncMock(
                side_effect=[
                    httpx.TimeoutException("Timeout"),
                    httpx.TimeoutException("Timeout"),
                    mock_response,
                ]
            ),
        ):
            async with BaseHTTPClient(
                "http://localhost:8000", max_retries=3, retry_delay=0.01
            ) as client:
                response = await client.get("/test")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_service_unavailable_after_retries(self):
        """Test ServiceUnavailableError after max retries."""
        with patch(
            "httpx.AsyncClient.request",
            new=AsyncMock(side_effect=httpx.TimeoutException("Timeout")),
        ):
            async with BaseHTTPClient(
                "http://localhost:8000", max_retries=2, retry_delay=0.01
            ) as client:
                with pytest.raises(ServiceUnavailableError):
                    await client.get("/test")

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self):
        """Test that 4xx errors are not retried."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=mock_response)):
            async with BaseHTTPClient("http://localhost:8000") as client:
                with pytest.raises(httpx.HTTPStatusError):
                    await client.get("/test")

    @pytest.mark.asyncio
    async def test_patch_request(self):
        """Test PATCH request."""
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=mock_response)):
            async with BaseHTTPClient("http://localhost:8000") as client:
                response = await client.patch("/test", json={"field": "value"})
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_request(self):
        """Test DELETE request."""
        mock_response = Mock()
        mock_response.status_code = 204

        with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=mock_response)):
            async with BaseHTTPClient("http://localhost:8000") as client:
                response = await client.delete("/test/123")
                assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_put_request(self):
        """Test PUT request."""
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=mock_response)):
            async with BaseHTTPClient("http://localhost:8000") as client:
                response = await client.put("/test/123", json={"data": "updated"})
                assert response.status_code == 200
