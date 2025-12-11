"""
Main FastAPI application for sessions service.

Provides REST API for session management, event tracking, and state persistence.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from services.sessions.app.api.health import router as health_router
from services.sessions.app.api.v1.sessions import router as sessions_router
from services.sessions.app.core.config import get_settings
from services.sessions.app.core.dependencies import close_connections
from shared.observability.metrics import get_metrics
from shared.observability.middleware import MetricsMiddleware
from shared.observability.tracing import instrument_fastapi, setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan.

    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    app.state.settings = settings

    # Setup distributed tracing
    setup_tracing(
        service_name=settings.service_name,
        service_version=settings.service_version,
        console_export=settings.debug,
    )

    yield

    # Shutdown
    await close_connections()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="Sessions Service",
        description="Conversation session management with state persistence and event tracking",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
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

    # Metrics middleware
    app.add_middleware(MetricsMiddleware, service_name=settings.service_name)

    # Instrument with OpenTelemetry
    instrument_fastapi(app)

    # Register routers
    app.include_router(health_router, tags=["health"])
    app.include_router(sessions_router, tags=["sessions"])

    # Metrics endpoint
    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint."""
        return Response(content=get_metrics(), media_type="text/plain")

    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "services.sessions.app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
