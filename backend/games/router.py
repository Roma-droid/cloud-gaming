"""Games catalog API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_admin_user, get_current_user
from backend.database import get_db
from backend.games.schemas import GameCreate, GameResponse
from backend.models.game import Game
from backend.models.user import User

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/", response_model=list[GameResponse])
async def list_games(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Game]:
    result = await db.execute(select(Game).order_by(Game.title))
    return list(result.scalars().all())


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Game:
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return game


@router.post("/", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(
    data: GameCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> Game:
    existing = await db.execute(select(Game).where(Game.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Game slug already exists")

    game = Game(**data.model_dump())
    db.add(game)
    await db.flush()
    await db.refresh(game)
    return game


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> None:
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    await db.delete(game)
