"""
Main FastAPI application for memory service.

Provides REST API for episodic memory storage with embeddings and revision tracking.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from services.memory.app.api.health import router as health_router
from services.memory.app.api.v1.memories import router as memories_router
from services.memory.app.api.v1.revisions import router as revisions_router
from services.memory.app.core.config import get_settings
from shared.auth.api_key import APIKeyHandler
from shared.auth.config import AuthSettings
from shared.auth.jwt import JWTHandler
from shared.auth.middleware import AuthenticationMiddleware
from shared.config.logging import get_logger
from shared.observability.metrics import get_metrics
from shared.observability.middleware import MetricsMiddleware
from shared.observability.tracing import instrument_fastapi, setup_tracing

logger = get_logger(__name__)


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

    # Load authentication settings
    auth_settings = AuthSettings()
    app.state.auth_settings = auth_settings

    if auth_settings.require_auth:
        logger.info("authentication_enabled", service="memory", require_auth=True)
    else:
        logger.warning("authentication_disabled", service="memory", require_auth=False)

    yield

    # Shutdown - connections will be closed by FastAPI


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="Memory Service",
        description="Episodic memory storage with vector embeddings and revision tracking",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Authentication middleware (if enabled)
    auth_settings = AuthSettings()
    if auth_settings.require_auth:
        jwt_handler = JWTHandler(secret_key=auth_settings.jwt_secret_key)
        api_key_handler = APIKeyHandler()

        app.add_middleware(
            AuthenticationMiddleware,
            jwt_handler=jwt_handler,
            api_key_handler=api_key_handler,
            exempt_paths=auth_settings.require_auth_exceptions,
        )
        logger.info("authentication_middleware_added", service="memory")

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
    app.include_router(memories_router, tags=["memories"])
    app.include_router(revisions_router, tags=["revisions"])

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
        "services.memory.app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
