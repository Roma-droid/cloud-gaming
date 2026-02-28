"""Prometheus metrics middleware for FastAPI."""

from __future__ import annotations

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from backend.monitoring.metrics import http_request_duration_seconds, http_requests_total


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        path = request.url.path
        method = request.method

        # Normalize path to avoid high cardinality
        if "/instances/" in path:
            path = "/api/instances/{id}"
        elif "/streaming/" in path:
            path = "/api/streaming/{action}"

        http_requests_total.labels(method=method, path=path, status=response.status_code).inc()
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)

        return response
