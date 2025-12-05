"""
Health check endpoints for sessions service.

Provides service health status and dependency checks.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.sessions.app.core.config import SessionsServiceSettings, get_settings
from services.sessions.app.core.dependencies import get_db_session

router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model."""

    status: str = Field(..., description="Service status (healthy/unhealthy)")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Check timestamp")


class DetailedHealthStatus(HealthStatus):
    """Detailed health status with dependency checks."""

    database: str = Field(..., description="Database status (healthy/unhealthy)")
    redis: str = Field(..., description="Redis status (healthy/unhealthy)")


@router.get(
    "/health",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Returns basic service health status",
)
async def health_check(
    settings: Annotated[SessionsServiceSettings, Depends(get_settings)],
) -> HealthStatus:
    """
    Basic health check endpoint.

    Returns:
        Service health status
    """
    return HealthStatus(
        status="healthy",
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Returns detailed health status with dependency checks",
)
async def detailed_health_check(
    settings: Annotated[SessionsServiceSettings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> DetailedHealthStatus:
    """
    Detailed health check endpoint with dependency validation.

    Checks:
    - Database connectivity
    - Redis connectivity (if enabled)

    Args:
        settings: Service settings
        db: Database session

    Returns:
        Detailed health status
    """
    # Check database
    db_status = "unhealthy"
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # Check Redis (if enabled)
    redis_status = "disabled"
    if settings.enable_cache:
        # Redis check would go here if we had the client
        redis_status = "not_implemented"

    # Overall status
    overall_status = "healthy" if db_status == "healthy" else "unhealthy"

    return DetailedHealthStatus(
        status=overall_status,
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.now(UTC),
        database=db_status,
        redis=redis_status,
    )


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Returns 200 if service is ready to accept requests",
)
async def readiness_check(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """
    Readiness check for Kubernetes/container orchestration.

    Validates that all dependencies are available.

    Args:
        db: Database session

    Returns:
        Ready status

    Raises:
        HTTPException: If service is not ready
    """
    # Check database connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() != 1:
            raise Exception("Database check failed")
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}",
        ) from e

    return {"status": "ready"}


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Returns 200 if service is alive",
)
async def liveness_check() -> dict[str, str]:
    """
    Liveness check for Kubernetes/container orchestration.

    Simple check that service is running.

    Returns:
        Alive status
    """
    return {"status": "alive"}
