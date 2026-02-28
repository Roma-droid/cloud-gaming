"""Unit tests for input handler."""

from __future__ import annotations

import pytest

from backend.input_handler.handler import InputAction, InputEvent, InputType, KEY_MAP


class TestInputEvent:
    def test_keyboard_event(self):
        event = InputEvent(type=InputType.KEYBOARD, key="W", action=InputAction.DOWN)
        assert event.type == "keyboard"
        assert event.key == "W"
        assert event.action == "down"

    def test_mouse_move_event(self):
        event = InputEvent(type=InputType.MOUSE_MOVE, dx=10.5, dy=-3.2, action=InputAction.MOVE)
        assert event.dx == 10.5
        assert event.dy == -3.2

    def test_mouse_button_event(self):
        event = InputEvent(type=InputType.MOUSE_BUTTON, button=0, action=InputAction.DOWN)
        assert event.button == 0

    def test_gamepad_event(self):
        event = InputEvent(
            type=InputType.GAMEPAD,
            gamepad_index=0,
            axis=1,
            axis_value=0.75,
            action=InputAction.MOVE,
        )
        assert event.gamepad_index == 0
        assert event.axis_value == 0.75

    def test_from_json(self):
        data = {"type": "keyboard", "key": "Space", "action": "down", "timestamp": 123.45}
        event = InputEvent(**data)
        assert event.key == "Space"
        assert event.timestamp == 123.45


class TestKeyMap:
    def test_common_keys_mapped(self):
        assert "Escape" in KEY_MAP
        assert "Enter" in KEY_MAP
        assert "ArrowUp" in KEY_MAP
        assert "ShiftLeft" in KEY_MAP

    def test_function_keys_mapped(self):
        for i in range(1, 13):
            assert f"F{i}" in KEY_MAP
