"""Monitoring and health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from backend.monitoring.metrics import app_info
from backend.streaming.webrtc import get_active_sessions

router = APIRouter(tags=["monitoring"])


@router.get("/health")
async def health_check() -> dict:
    return {"status": "healthy"}


@router.get("/health/ready")
async def readiness_check() -> dict:
    # Check dependencies
    checks: dict[str, str] = {}

    try:
        from backend.utils.redis import get_redis
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    try:
        from backend.database import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if all_ok else "degraded", "checks": checks}


@router.get("/health/live")
async def liveness_check() -> dict:
    return {"status": "alive"}


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> PlainTextResponse:
    """Expose Prometheus metrics."""
    # Update dynamic metrics
    sessions = get_active_sessions()
    from backend.monitoring.metrics import active_streams
    active_streams.set(len(sessions))

    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
