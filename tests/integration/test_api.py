"""Integration tests for API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestAuthAPI:
    async def test_register(self, client: AsyncClient):
        response = await client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "id" in data

    async def test_register_duplicate(self, client: AsyncClient, test_user):
        response = await client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
        })
        assert response.status_code == 409

    async def test_register_invalid_username(self, client: AsyncClient):
        response = await client.post("/api/auth/register", json={
            "username": "ab",  # Too short
            "email": "test2@example.com",
            "password": "password123",
        })
        assert response.status_code == 422

    async def test_login(self, client: AsyncClient, test_user):
        response = await client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        response = await client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    async def test_get_me(self, client: AsyncClient, test_user, auth_headers):
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    async def test_get_me_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/auth/me")
        assert response.status_code == 403  # No auth header

    async def test_refresh_token(self, client: AsyncClient, test_user):
        # Login first
        login_response = await client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        tokens = login_response.json()

        # Refresh
        response = await client.post("/api/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestGamesAPI:
    async def test_list_games_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/games/")
        assert response.status_code == 403

    async def test_list_games(self, client: AsyncClient, auth_headers, test_game):
        response = await client.get("/api/games/", headers=auth_headers)
        assert response.status_code == 200
        games = response.json()
        assert len(games) >= 1
        assert games[0]["title"] == "Test Game"

    async def test_get_game(self, client: AsyncClient, auth_headers, test_game):
        response = await client.get(f"/api/games/{test_game.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["slug"] == "test-game"


class TestInstancesAPI:
    async def test_list_instances(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/instances/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestHealthEndpoints:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_liveness(self, client: AsyncClient):
        response = await client.get("/health/live")
        assert response.status_code == 200
