"""Game database model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    docker_image: Mapped[str] = mapped_column(String(500), nullable=False)
    required_gpu: Mapped[bool] = mapped_column(default=False)
    min_cpu_cores: Mapped[int] = mapped_column(Integer, default=2)
    min_memory_mb: Mapped[int] = mapped_column(Integer, default=2048)
    launch_command: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
