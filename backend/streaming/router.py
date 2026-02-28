"""Streaming API routes for WebRTC signaling."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database import get_db
from backend.models.game_instance import GameInstance, InstanceStatus
from backend.models.user import User
from backend.streaming import webrtc

router = APIRouter(prefix="/streaming", tags=["streaming"])


class WebRTCOffer(BaseModel):
    instance_id: uuid.UUID
    sdp: str
    type: str = "offer"


class WebRTCAnswer(BaseModel):
    sdp: str
    type: str


class ICECandidate(BaseModel):
    instance_id: uuid.UUID
    candidate: dict


class BitrateUpdate(BaseModel):
    instance_id: uuid.UUID
    bitrate_kbps: int


@router.post("/webrtc/offer", response_model=WebRTCAnswer)
async def webrtc_offer(
    data: WebRTCOffer,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle WebRTC SDP offer and return an answer."""
    result = await db.execute(
        select(GameInstance).where(
            GameInstance.id == data.instance_id,
            GameInstance.user_id == user.id,
            GameInstance.status == InstanceStatus.RUNNING,
        )
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Running instance not found",
        )

    answer = await webrtc.create_stream(
        instance_id=instance.id,
        user_id=user.id,
        display=instance.display_number or 99,
        resolution=instance.resolution,
        fps=instance.fps,
        bitrate_kbps=instance.bitrate_kbps,
        offer_sdp=data.sdp,
        offer_type=data.type,
    )
    return answer


@router.post("/webrtc/ice-candidate", status_code=status.HTTP_204_NO_CONTENT)
async def add_ice_candidate(
    data: ICECandidate,
    user: User = Depends(get_current_user),
) -> None:
    """Add an ICE candidate for WebRTC connection."""
    await webrtc.add_ice_candidate(data.instance_id, data.candidate)


@router.post("/bitrate", status_code=status.HTTP_204_NO_CONTENT)
async def update_bitrate(
    data: BitrateUpdate,
    user: User = Depends(get_current_user),
) -> None:
    """Update stream bitrate for adaptive quality."""
    await webrtc.update_stream_bitrate(data.instance_id, data.bitrate_kbps)


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_stream(
    instance_id: uuid.UUID,
    user: User = Depends(get_current_user),
) -> None:
    """Stop a streaming session."""
    await webrtc.close_stream(instance_id)
