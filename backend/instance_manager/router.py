"""Game instance API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database import get_db
from backend.instance_manager import manager
from backend.instance_manager.schemas import InstanceCreate, InstanceResponse, InstanceStats
from backend.models.game_instance import GameInstance, InstanceStatus
from backend.models.user import User

router = APIRouter(prefix="/instances", tags=["instances"])


@router.post("/", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    data: InstanceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GameInstance:
    try:
        instance = await manager.create_instance(
            db=db,
            user_id=user.id,
            game_id=data.game_id,
            resolution=data.resolution,
            fps=data.fps,
            bitrate_kbps=data.bitrate_kbps,
        )
        return instance
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await manager.destroy_instance(db, instance_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GameInstance:
    result = await db.execute(
        select(GameInstance).where(
            GameInstance.id == instance_id,
            GameInstance.user_id == user.id,
        )
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    return instance


@router.get("/", response_model=list[InstanceResponse])
async def list_instances(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GameInstance]:
    result = await db.execute(
        select(GameInstance)
        .where(GameInstance.user_id == user.id)
        .order_by(GameInstance.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{instance_id}/stats", response_model=InstanceStats)
async def get_instance_stats(
    instance_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InstanceStats:
    result = await db.execute(
        select(GameInstance).where(
            GameInstance.id == instance_id,
            GameInstance.user_id == user.id,
            GameInstance.status == InstanceStatus.RUNNING,
        )
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Running instance not found")

    stats = await manager.monitor_resources(instance_id)
    if stats is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stats unavailable")
    return stats
