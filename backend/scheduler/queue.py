"""Game launch queue for managing instance startup ordering."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

import structlog

from backend.utils.redis import get_redis

logger = structlog.get_logger(__name__)


class QueueStatus(StrEnum):
    WAITING = "waiting"
    LAUNCHING = "launching"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueEntry:
    user_id: uuid.UUID
    game_id: uuid.UUID
    resolution: str = "1080p"
    fps: int = 60
    position: int = 0
    status: QueueStatus = QueueStatus.WAITING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


QUEUE_KEY = "game:launch_queue"
QUEUE_DETAILS_PREFIX = "game:queue_entry:"


class LaunchQueue:
    """Redis-backed queue for game launch requests."""

    async def enqueue(self, entry: QueueEntry) -> int:
        """Add a launch request to the queue. Returns position."""
        redis = await get_redis()
        entry_id = f"{entry.user_id}:{entry.game_id}"

        # Store entry details
        await redis.hset(f"{QUEUE_DETAILS_PREFIX}{entry_id}", mapping={
            "user_id": str(entry.user_id),
            "game_id": str(entry.game_id),
            "resolution": entry.resolution,
            "fps": str(entry.fps),
            "status": entry.status,
            "created_at": entry.created_at.isoformat(),
        })
        await redis.expire(f"{QUEUE_DETAILS_PREFIX}{entry_id}", 3600)

        # Add to sorted set with timestamp as score
        await redis.zadd(QUEUE_KEY, {entry_id: entry.created_at.timestamp()})

        position = await redis.zrank(QUEUE_KEY, entry_id)
        logger.info("queue_enqueued", user_id=str(entry.user_id), position=position)
        return position or 0

    async def dequeue(self) -> QueueEntry | None:
        """Pop the next entry from the queue."""
        redis = await get_redis()

        # Get first item
        items = await redis.zrange(QUEUE_KEY, 0, 0)
        if not items:
            return None

        entry_id = items[0]
        data = await redis.hgetall(f"{QUEUE_DETAILS_PREFIX}{entry_id}")
        if not data:
            await redis.zrem(QUEUE_KEY, entry_id)
            return None

        # Remove from queue
        await redis.zrem(QUEUE_KEY, entry_id)

        # Update status
        await redis.hset(f"{QUEUE_DETAILS_PREFIX}{entry_id}", "status", QueueStatus.LAUNCHING)

        return QueueEntry(
            user_id=uuid.UUID(data["user_id"]),
            game_id=uuid.UUID(data["game_id"]),
            resolution=data.get("resolution", "1080p"),
            fps=int(data.get("fps", 60)),
            status=QueueStatus.LAUNCHING,
        )

    async def get_position(self, user_id: uuid.UUID, game_id: uuid.UUID) -> int | None:
        """Get user's position in the queue."""
        redis = await get_redis()
        entry_id = f"{user_id}:{game_id}"
        rank = await redis.zrank(QUEUE_KEY, entry_id)
        return rank

    async def cancel(self, user_id: uuid.UUID, game_id: uuid.UUID) -> bool:
        """Cancel a queued launch request."""
        redis = await get_redis()
        entry_id = f"{user_id}:{game_id}"
        removed = await redis.zrem(QUEUE_KEY, entry_id)
        if removed:
            await redis.hset(f"{QUEUE_DETAILS_PREFIX}{entry_id}", "status", QueueStatus.CANCELLED)
            logger.info("queue_cancelled", user_id=str(user_id))
        return bool(removed)

    async def get_queue_length(self) -> int:
        redis = await get_redis()
        return await redis.zcard(QUEUE_KEY)


launch_queue = LaunchQueue()
