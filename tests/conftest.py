"""Test fixtures and configuration."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.auth.security import create_access_token, hash_password
from backend.config import Settings, get_settings
from backend.database import Base, get_db
from backend.main import create_app


def get_test_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///./test.db",
        redis_url="redis://localhost:6379/1",
        jwt_secret_key="test-secret-key",
        app_debug=True,
        app_env="test",
    )


# Test database engine
test_engine = create_async_engine("sqlite+aiosqlite:///./test.db", echo=False)
test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def app():
    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_settings] = get_test_settings
    return application


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession):
    from backend.models.user import User

    user = User(
        id=uuid.uuid4(),
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(test_user.id, test_user.username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_game(db_session: AsyncSession):
    from backend.models.game import Game

    game = Game(
        id=uuid.uuid4(),
        title="Test Game",
        slug="test-game",
        description="A test game",
        docker_image="cloud-gaming/test-game:latest",
        required_gpu=False,
        min_cpu_cores=2,
        min_memory_mb=2048,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)
    return game
