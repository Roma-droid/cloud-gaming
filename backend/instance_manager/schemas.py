"""Instance manager schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InstanceCreate(BaseModel):
    game_id: uuid.UUID
    resolution: str = Field(default="1080p", pattern=r"^(720p|1080p|1440p)$")
    fps: int = Field(default=60, ge=30, le=144)
    bitrate_kbps: int = Field(default=6000, ge=1000, le=50000)


class InstanceResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    game_id: uuid.UUID
    status: str
    server_node: str | None
    display_number: int | None
    stream_port: int | None
    resolution: str
    fps: int
    bitrate_kbps: int
    created_at: datetime
    last_activity_at: datetime

    model_config = {"from_attributes": True}


class InstanceStats(BaseModel):
    cpu_percent: float
    memory_mb: float
    memory_limit_mb: float
    gpu_utilization: float | None = None
    uptime_seconds: float
