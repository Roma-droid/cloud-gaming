"""Unit tests for authentication."""

from __future__ import annotations

import uuid

import pytest

from backend.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "securepassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


class TestJWT:
    def test_create_and_decode_access_token(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id, "testuser")
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["username"] == "testuser"
        assert payload["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        user_id = uuid.uuid4()
        token = create_refresh_token(user_id)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_invalid_token_returns_none(self):
        assert decode_token("invalid.token.here") is None
        assert decode_token("") is None

    def test_access_and_refresh_differ(self):
        user_id = uuid.uuid4()
        access = create_access_token(user_id, "user")
        refresh = create_refresh_token(user_id)
        assert access != refresh
        assert decode_token(access)["type"] == "access"
        assert decode_token(refresh)["type"] == "refresh"
