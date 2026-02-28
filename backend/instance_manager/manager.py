"""Game instance lifecycle manager using Docker."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import docker
import docker.errors
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.instance_manager.schemas import InstanceStats
from backend.models.game import Game
from backend.models.game_instance import GameInstance, InstanceStatus

logger = structlog.get_logger(__name__)

# Track allocated display numbers and ports
_allocated_displays: set[int] = set()
_allocated_ports: set[int] = set()
_next_display = 99
_next_port = 10000
_lock = asyncio.Lock()


async def _allocate_display() -> int:
    global _next_display
    async with _lock:
        while _next_display in _allocated_displays:
            _next_display += 1
        display = _next_display
        _allocated_displays.add(display)
        _next_display += 1
        return display


async def _allocate_ports() -> tuple[int, int]:
    global _next_port
    async with _lock:
        while _next_port in _allocated_ports or (_next_port + 1) in _allocated_ports:
            _next_port += 1
        stream_port = _next_port
        input_port = _next_port + 1
        _allocated_ports.update({stream_port, input_port})
        _next_port += 2
        return stream_port, input_port


def _release_resources(display: int | None, stream_port: int | None, input_port: int | None) -> None:
    if display is not None:
        _allocated_displays.discard(display)
    if stream_port is not None:
        _allocated_ports.discard(stream_port)
    if input_port is not None:
        _allocated_ports.discard(input_port)


def _get_docker_client() -> docker.DockerClient:
    return docker.from_env()


async def create_instance(
    db: AsyncSession,
    user_id: uuid.UUID,
    game_id: uuid.UUID,
    resolution: str = "1080p",
    fps: int = 60,
    bitrate_kbps: int = 6000,
) -> GameInstance:
    """Create and start a new game instance in a Docker container."""
    settings = get_settings()

    # Check active session limit
    result = await db.execute(
        select(GameInstance).where(
            GameInstance.user_id == user_id,
            GameInstance.status.in_([InstanceStatus.PENDING, InstanceStatus.STARTING, InstanceStatus.RUNNING]),
        )
    )
    active = result.scalars().all()
    if len(active) >= settings.max_sessions_per_user:
        raise ValueError(f"Maximum {settings.max_sessions_per_user} active session(s) allowed")

    # Load game config
    game_result = await db.execute(select(Game).where(Game.id == game_id))
    game = game_result.scalar_one_or_none()
    if game is None:
        raise ValueError("Game not found")

    display = await _allocate_display()
    stream_port, input_port = await _allocate_ports()

    instance = GameInstance(
        user_id=user_id,
        game_id=game_id,
        status=InstanceStatus.PENDING,
        display_number=display,
        stream_port=stream_port,
        input_port=input_port,
        resolution=resolution,
        fps=fps,
        bitrate_kbps=bitrate_kbps,
    )
    db.add(instance)
    await db.flush()
    await db.refresh(instance)

    # Start container in background
    asyncio.create_task(_start_container(instance.id, game, display, stream_port, settings))

    logger.info(
        "instance_created",
        instance_id=str(instance.id),
        user_id=str(user_id),
        game=game.title,
        display=display,
    )
    return instance


async def _start_container(
    instance_id: uuid.UUID,
    game: Game,
    display: int,
    stream_port: int,
    settings: Any,
) -> None:
    """Start the Docker container for a game instance."""
    from backend.database import async_session_factory

    try:
        client = _get_docker_client()

        resolution_map = {"720p": "1280x720", "1080p": "1920x1080", "1440p": "2560x1440"}

        environment = {
            "DISPLAY": f":{display}",
            "RESOLUTION": resolution_map.get("1080p", "1920x1080"),
            "GAME_LAUNCH_CMD": game.launch_command or "",
        }

        # Container resource limits
        host_config: dict[str, Any] = {
            "nano_cpus": int(settings.game_container_cpu_limit * 1e9),
            "mem_limit": settings.game_container_memory_limit,
            "network_mode": settings.docker_network,
            "ports": {
                f"{stream_port}/udp": stream_port,
            },
        }

        # GPU passthrough if available
        if settings.gpu_enabled:
            host_config["device_requests"] = [
                docker.types.DeviceRequest(count=1, capabilities=[["gpu"]])
            ]

        container = await asyncio.to_thread(
            client.containers.run,
            game.docker_image,
            detach=True,
            name=f"game-{instance_id}",
            environment=environment,
            **host_config,
        )

        async with async_session_factory() as db:
            await db.execute(
                update(GameInstance)
                .where(GameInstance.id == instance_id)
                .values(
                    container_id=container.id,
                    status=InstanceStatus.RUNNING,
                )
            )
            await db.commit()

        logger.info("container_started", instance_id=str(instance_id), container=container.short_id)

    except Exception as e:
        logger.error("container_start_failed", instance_id=str(instance_id), error=str(e))
        async with async_session_factory() as db:
            await db.execute(
                update(GameInstance)
                .where(GameInstance.id == instance_id)
                .values(status=InstanceStatus.ERROR)
            )
            await db.commit()


async def destroy_instance(db: AsyncSession, instance_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Stop and remove a game instance."""
    result = await db.execute(
        select(GameInstance).where(
            GameInstance.id == instance_id,
            GameInstance.user_id == user_id,
        )
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise ValueError("Instance not found")

    if instance.status == InstanceStatus.STOPPED:
        raise ValueError("Instance already stopped")

    instance.status = InstanceStatus.STOPPING
    await db.flush()

    # Stop container
    if instance.container_id:
        try:
            client = _get_docker_client()
            container = await asyncio.to_thread(client.containers.get, instance.container_id)
            await asyncio.to_thread(container.stop, timeout=10)
            await asyncio.to_thread(container.remove, force=True)
        except docker.errors.NotFound:
            logger.warning("container_not_found", container_id=instance.container_id)
        except Exception as e:
            logger.error("container_stop_failed", error=str(e))

    _release_resources(instance.display_number, instance.stream_port, instance.input_port)

    instance.status = InstanceStatus.STOPPED
    instance.ended_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info("instance_destroyed", instance_id=str(instance_id))


async def monitor_resources(instance_id: uuid.UUID) -> InstanceStats | None:
    """Get resource usage stats for a running instance."""
    from backend.database import async_session_factory

    async with async_session_factory() as db:
        result = await db.execute(select(GameInstance).where(GameInstance.id == instance_id))
        instance = result.scalar_one_or_none()

    if instance is None or not instance.container_id:
        return None

    try:
        client = _get_docker_client()
        container = await asyncio.to_thread(client.containers.get, instance.container_id)
        stats = await asyncio.to_thread(container.stats, stream=False)

        # Calculate CPU %
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = (
            stats["cpu_stats"]["system_cpu_usage"]
            - stats["precpu_stats"]["system_cpu_usage"]
        )
        cpu_count = stats["cpu_stats"]["online_cpus"]
        cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0 if system_delta > 0 else 0.0

        memory_usage = stats["memory_stats"]["usage"] / (1024 * 1024)
        memory_limit = stats["memory_stats"]["limit"] / (1024 * 1024)

        started_at = container.attrs["State"]["StartedAt"]

        return InstanceStats(
            cpu_percent=round(cpu_percent, 2),
            memory_mb=round(memory_usage, 2),
            memory_limit_mb=round(memory_limit, 2),
            uptime_seconds=0,  # Simplified
        )
    except Exception as e:
        logger.error("monitor_failed", instance_id=str(instance_id), error=str(e))
        return None


async def cleanup_idle_instances() -> int:
    """Stop instances that have been idle beyond the timeout."""
    settings = get_settings()
    from backend.database import async_session_factory

    cleaned = 0
    async with async_session_factory() as db:
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(
            minutes=settings.idle_timeout_minutes
        )
        result = await db.execute(
            select(GameInstance).where(
                GameInstance.status == InstanceStatus.RUNNING,
                GameInstance.last_activity_at < cutoff,
            )
        )
        idle_instances = result.scalars().all()

        for instance in idle_instances:
            try:
                await destroy_instance(db, instance.id, instance.user_id)
                cleaned += 1
            except Exception as e:
                logger.error("cleanup_failed", instance_id=str(instance.id), error=str(e))

        await db.commit()

    if cleaned:
        logger.info("idle_cleanup_completed", cleaned_count=cleaned)
    return cleaned
