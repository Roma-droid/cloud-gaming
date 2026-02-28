"""Authentication API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import (
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from backend.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.config import get_settings
from backend.database import get_db
from backend.models.user import User
from backend.utils.logging import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)) -> User:
    existing = await db.execute(
        select(User).where((User.username == data.username) | (User.email == data.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info("user_registered", user_id=str(user.id), username=user.username)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    settings = get_settings()
    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id)

    logger.info("user_logged_in", user_id=str(user.id))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: TokenRefresh, db: AsyncSession = Depends(get_db)) -> dict:
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    settings = get_settings()
    access_token = create_access_token(user.id, user.username)
    new_refresh_token = create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user
