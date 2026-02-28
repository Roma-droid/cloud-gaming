"""Game catalog schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class GameCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    docker_image: str = Field(..., max_length=500)
    required_gpu: bool = False
    min_cpu_cores: int = Field(default=2, ge=1, le=16)
    min_memory_mb: int = Field(default=2048, ge=512, le=32768)
    launch_command: str | None = None
    cover_image_url: str | None = None


class GameResponse(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    description: str | None
    docker_image: str
    required_gpu: bool
    min_cpu_cores: int
    min_memory_mb: int
    launch_command: str | None
    cover_image_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
