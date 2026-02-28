"""Game instance (running session) database model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class InstanceStatus(StrEnum):
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class GameInstance(Base):
    __tablename__ = "game_instances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id"), nullable=False
    )
    container_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=InstanceStatus.PENDING, index=True
    )
    server_node: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stream_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution: Mapped[str] = mapped_column(String(10), default="1080p")
    fps: Mapped[int] = mapped_column(Integer, default=60)
    bitrate_kbps: Mapped[int] = mapped_column(Integer, default=6000)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="instances")  # noqa: F821
