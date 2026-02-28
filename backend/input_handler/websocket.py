"""WebSocket endpoint for real-time input handling."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import orjson
import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import decode_token
from backend.database import async_session_factory
from backend.input_handler.handler import InputEvent, get_or_create_injector, remove_injector
from backend.models.game_instance import GameInstance, InstanceStatus

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["input"])


@router.websocket("/ws/input/{instance_id}")
async def input_websocket(
    websocket: WebSocket,
    instance_id: uuid.UUID,
    token: str = Query(...),
) -> None:
    """WebSocket endpoint for receiving user input events.

    Client connects with: ws://host/ws/input/{instance_id}?token=JWT_TOKEN

    Message format:
    {
        "type": "keyboard" | "mouse_move" | "mouse_button" | "mouse_scroll" | "gamepad",
        "key": "W",
        "action": "down" | "up",
        ...
    }
    """
    # Authenticate
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = uuid.UUID(payload["sub"])

    # Verify instance ownership and status
    async with async_session_factory() as db:
        result = await db.execute(
            select(GameInstance).where(
                GameInstance.id == instance_id,
                GameInstance.user_id == user_id,
                GameInstance.status == InstanceStatus.RUNNING,
            )
        )
        instance = result.scalar_one_or_none()

    if instance is None or not instance.container_id:
        await websocket.close(code=4004, reason="Instance not found or not running")
        return

    await websocket.accept()
    logger.info("input_ws_connected", instance_id=str(instance_id), user_id=str(user_id))

    injector = await get_or_create_injector(
        instance_id=instance_id,
        container_id=instance.container_id,
        display=instance.display_number or 99,
    )

    try:
        while True:
            raw = await websocket.receive_bytes()
            try:
                data = orjson.loads(raw)
                event = InputEvent(**data)
                await injector.inject(event)

                # Update last activity timestamp periodically (not every event)
                # This is debounced by the client
            except Exception as e:
                logger.warning("invalid_input_event", error=str(e))
                await websocket.send_json({"error": "Invalid input event"})

    except WebSocketDisconnect:
        logger.info("input_ws_disconnected", instance_id=str(instance_id))
    finally:
        # Update last activity
        async with async_session_factory() as db:
            await db.execute(
                update(GameInstance)
                .where(GameInstance.id == instance_id)
                .values(last_activity_at=datetime.now(timezone.utc))
            )
            await db.commit()
