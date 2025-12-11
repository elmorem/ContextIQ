"""
API Gateway for ContextIQ.

Provides unified entry point for all services with:
- Request routing to Sessions and Memory services
- Health check aggregation
- Correlation ID tracking
- Request/response logging
"""

import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.config.logging import get_logger

logger = get_logger(__name__)


# Service URLs from environment
SESSIONS_SERVICE_URL = "http://sessions-service:8001"
MEMORY_SERVICE_URL = "http://memory-service:8002"


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Lifespan context manager for startup and shutdown."""
    logger.info("api_gateway_starting")

    # Create HTTP client for proxying requests
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=5.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )

    yield

    # Cleanup
    await app.state.http_client.aclose()
    logger.info("api_gateway_stopped")


app = FastAPI(
    title="ContextIQ API Gateway",
    description="Unified API gateway for ContextIQ services",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next: Any) -> Any:
    """Add correlation ID to requests for tracking across services."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

    # Add to request state for logging
    request.state.correlation_id = correlation_id

    # Process request
    response = await call_next(request)

    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id

    return response


@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Any:
    """Log all requests and responses."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
        correlation_id=correlation_id,
    )

    response = await call_next(request)

    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        correlation_id=correlation_id,
    )

    return response


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Gateway health check.

    Returns:
        Health status of gateway and downstream services
    """
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0",
    }


@app.get("/health/services")
async def services_health_check(request: Request) -> dict[str, Any]:
    """
    Aggregate health check for all services.

    Returns:
        Health status of all downstream services
    """
    client: httpx.AsyncClient = request.app.state.http_client
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    services_status = {}

    # Check Sessions Service
    try:
        response = await client.get(
            f"{SESSIONS_SERVICE_URL}/health",
            timeout=5.0,
            headers={"X-Correlation-ID": correlation_id},
        )
        services_status["sessions"] = {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "response_time_ms": int(response.elapsed.total_seconds() * 1000),
        }
    except Exception as e:
        services_status["sessions"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Check Memory Service
    try:
        response = await client.get(
            f"{MEMORY_SERVICE_URL}/health",
            timeout=5.0,
            headers={"X-Correlation-ID": correlation_id},
        )
        services_status["memory"] = {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "response_time_ms": int(response.elapsed.total_seconds() * 1000),
        }
    except Exception as e:
        services_status["memory"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Determine overall health
    all_healthy = all(service.get("status") == "healthy" for service in services_status.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services_status,
    }


async def proxy_request(
    request: Request,
    target_url: str,
    path: str,
) -> Response:
    """
    Proxy request to target service.

    Args:
        request: Incoming FastAPI request
        target_url: Base URL of target service
        path: Path to append to target URL

    Returns:
        Response from target service
    """
    client: httpx.AsyncClient = request.app.state.http_client
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    # Build full URL
    url = f"{target_url}{path}"

    # Forward query parameters
    if request.url.query:
        url = f"{url}?{request.url.query}"

    # Prepare headers
    headers = dict(request.headers)
    headers["X-Correlation-ID"] = correlation_id
    headers.pop("host", None)  # Remove host header

    try:
        # Read request body
        body = await request.body()

        # Proxy request
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body if body else None,
        )

        # Return proxied response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    except httpx.TimeoutException:
        logger.error(
            "proxy_timeout",
            target_url=target_url,
            path=path,
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"detail": "Service request timed out"},
        )

    except httpx.ConnectError:
        logger.error(
            "proxy_connect_error",
            target_url=target_url,
            path=path,
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Service unavailable"},
        )

    except Exception as e:
        logger.error(
            "proxy_error",
            target_url=target_url,
            path=path,
            error=str(e),
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "Gateway error"},
        )


# Sessions Service routes
@app.api_route(
    "/api/v1/sessions/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_sessions(request: Request, path: str) -> Response:
    """Proxy requests to Sessions Service."""
    return await proxy_request(request, SESSIONS_SERVICE_URL, f"/api/v1/sessions/{path}")


# Memory Service routes
@app.api_route(
    "/api/v1/memories/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_memories(request: Request, path: str) -> Response:
    """Proxy requests to Memory Service."""
    return await proxy_request(request, MEMORY_SERVICE_URL, f"/api/v1/memories/{path}")


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with service information."""
    return {
        "service": "ContextIQ API Gateway",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "services_health": "/health/services",
            "sessions": "/api/v1/sessions",
            "memories": "/api/v1/memories",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
