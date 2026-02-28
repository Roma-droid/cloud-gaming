"""Cloud Gaming Platform — main FastAPI application."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database import close_db, init_db
from backend.monitoring.metrics import app_info
from backend.utils.logging import setup_logging, get_logger
from backend.utils.redis import close_redis

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    setup_logging()
    logger.info("starting", app=settings.app_name, env=settings.app_env)

    # Initialize database
    await init_db()
    logger.info("database_initialized")

    # Set app info metric
    app_info.info({"version": "0.1.0", "environment": settings.app_env})

    # Start background tasks
    cleanup_task = asyncio.create_task(_idle_cleanup_loop())

    yield

    # Shutdown
    logger.info("shutting_down")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Close all streams and injectors
    from backend.streaming.webrtc import close_all_streams
    from backend.input_handler.handler import close_all_injectors

    await close_all_streams()
    await close_all_injectors()
    await close_redis()
    await close_db()
    logger.info("shutdown_complete")


async def _idle_cleanup_loop() -> None:
    """Periodically clean up idle game instances."""
    from backend.instance_manager.manager import cleanup_idle_instances

    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            await cleanup_idle_instances()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("cleanup_loop_error", error=str(e))


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Cloud Gaming Platform",
        description="Production-ready cloud gaming streaming service",
        version="0.1.0",
        docs_url="/api/docs" if settings.app_debug else None,
        redoc_url="/api/redoc" if settings.app_debug else None,
        openapi_url="/api/openapi.json" if settings.app_debug else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus metrics middleware
    from backend.monitoring.middleware import PrometheusMiddleware
    app.add_middleware(PrometheusMiddleware)

    # Rate limiting
    from backend.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

    # API routes
    from backend.auth.router import router as auth_router
    from backend.games.router import router as games_router
    from backend.instance_manager.router import router as instances_router
    from backend.streaming.router import router as streaming_router
    from backend.input_handler.websocket import router as input_router
    from backend.monitoring.router import router as monitoring_router

    app.include_router(auth_router, prefix="/api")
    app.include_router(games_router, prefix="/api")
    app.include_router(instances_router, prefix="/api")
    app.include_router(streaming_router, prefix="/api")
    app.include_router(input_router)
    app.include_router(monitoring_router)

    return app


app = create_app()
