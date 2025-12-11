"""
FastAPI middleware for observability.

Provides automatic metrics collection and tracing for HTTP requests.
"""

import time
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from shared.observability.metrics import (
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""

    def __init__(self, app: Any, service_name: str):
        """
        Initialize metrics middleware.

        Args:
            app: FastAPI application
            service_name: Name of the service
        """
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect metrics.

        Args:
            request: HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response
        """
        method = request.method
        endpoint = request.url.path

        # Track in-progress requests
        http_requests_in_progress.labels(
            service=self.service_name,
            method=method,
            endpoint=endpoint,
        ).inc()

        # Measure request duration
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Track failed requests
            status_code = 500
            raise e
        finally:
            # Record metrics
            duration = time.time() - start_time

            http_requests_in_progress.labels(
                service=self.service_name,
                method=method,
                endpoint=endpoint,
            ).dec()

            http_requests_total.labels(
                service=self.service_name,
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).inc()

            http_request_duration_seconds.labels(
                service=self.service_name,
                method=method,
                endpoint=endpoint,
            ).observe(duration)

        return response
