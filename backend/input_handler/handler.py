"""Input handler: processes keyboard, mouse, and gamepad events from the client
and injects them into the game container's virtual display."""

from __future__ import annotations

import asyncio
import uuid
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class InputType(StrEnum):
    KEYBOARD = "keyboard"
    MOUSE_MOVE = "mouse_move"
    MOUSE_BUTTON = "mouse_button"
    MOUSE_SCROLL = "mouse_scroll"
    GAMEPAD = "gamepad"


class InputAction(StrEnum):
    DOWN = "down"
    UP = "up"
    MOVE = "move"


class InputEvent(BaseModel):
    """Client input event."""

    type: InputType
    # Keyboard
    key: str | None = None
    key_code: int | None = None
    action: InputAction = InputAction.DOWN
    # Mouse
    x: float | None = None
    y: float | None = None
    dx: float | None = None
    dy: float | None = None
    button: int | None = None  # 0=left, 1=middle, 2=right
    scroll_x: float | None = None
    scroll_y: float | None = None
    # Gamepad
    gamepad_index: int | None = None
    axis: int | None = None
    axis_value: float | None = None
    gamepad_button: int | None = None
    # Timestamp from client for latency measurement
    timestamp: float | None = None


# Web key names -> X11 keysym mapping (subset)
KEY_MAP: dict[str, str] = {
    "Escape": "Escape",
    "Enter": "Return",
    "Backspace": "BackSpace",
    "Tab": "Tab",
    "Space": "space",
    "ArrowUp": "Up",
    "ArrowDown": "Down",
    "ArrowLeft": "Left",
    "ArrowRight": "Right",
    "ShiftLeft": "Shift_L",
    "ShiftRight": "Shift_R",
    "ControlLeft": "Control_L",
    "ControlRight": "Control_R",
    "AltLeft": "Alt_L",
    "AltRight": "Alt_R",
    "CapsLock": "Caps_Lock",
    "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4",
    "F5": "F5", "F6": "F6", "F7": "F7", "F8": "F8",
    "F9": "F9", "F10": "F10", "F11": "F11", "F12": "F12",
    "Delete": "Delete",
    "Insert": "Insert",
    "Home": "Home",
    "End": "End",
    "PageUp": "Page_Up",
    "PageDown": "Page_Down",
}


class InputInjector:
    """Injects input events into a Docker container's virtual display using xdotool."""

    def __init__(self, container_id: str, display: int = 99) -> None:
        self.container_id = container_id
        self.display = display
        self._queue: asyncio.Queue[InputEvent] = asyncio.Queue(maxsize=1000)
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("input_injector_started", container=self.container_id[:12])

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("input_injector_stopped", container=self.container_id[:12])

    async def inject(self, event: InputEvent) -> None:
        """Queue an input event for injection."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop oldest events under pressure
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._queue.put_nowait(event)

    async def _process_loop(self) -> None:
        """Process queued input events."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                await self._handle_event(event)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("input_injection_error", error=str(e))

    async def _handle_event(self, event: InputEvent) -> None:
        match event.type:
            case InputType.KEYBOARD:
                await self._inject_keyboard(event)
            case InputType.MOUSE_MOVE:
                await self._inject_mouse_move(event)
            case InputType.MOUSE_BUTTON:
                await self._inject_mouse_button(event)
            case InputType.MOUSE_SCROLL:
                await self._inject_mouse_scroll(event)
            case InputType.GAMEPAD:
                await self._inject_gamepad(event)

    async def _exec_in_container(self, cmd: list[str]) -> None:
        """Execute a command inside the Docker container."""
        full_cmd = [
            "docker", "exec",
            "-e", f"DISPLAY=:{self.display}",
            self.container_id,
            *cmd,
        ]
        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=1.0)

    async def _inject_keyboard(self, event: InputEvent) -> None:
        if not event.key:
            return

        key_name = event.key
        # Map single characters directly
        if len(key_name) == 1:
            x11_key = key_name.lower()
        else:
            x11_key = KEY_MAP.get(key_name, key_name)

        if event.action == InputAction.DOWN:
            await self._exec_in_container(["xdotool", "keydown", x11_key])
        else:
            await self._exec_in_container(["xdotool", "keyup", x11_key])

    async def _inject_mouse_move(self, event: InputEvent) -> None:
        if event.dx is not None and event.dy is not None:
            await self._exec_in_container([
                "xdotool", "mousemove_relative", "--",
                str(int(event.dx)), str(int(event.dy)),
            ])
        elif event.x is not None and event.y is not None:
            await self._exec_in_container([
                "xdotool", "mousemove",
                str(int(event.x)), str(int(event.y)),
            ])

    async def _inject_mouse_button(self, event: InputEvent) -> None:
        button = (event.button or 0) + 1  # xdotool uses 1-indexed buttons
        if event.action == InputAction.DOWN:
            await self._exec_in_container(["xdotool", "mousedown", str(button)])
        else:
            await self._exec_in_container(["xdotool", "mouseup", str(button)])

    async def _inject_mouse_scroll(self, event: InputEvent) -> None:
        scroll_y = event.scroll_y or 0
        if scroll_y > 0:
            await self._exec_in_container(["xdotool", "click", "4"])  # Scroll up
        elif scroll_y < 0:
            await self._exec_in_container(["xdotool", "click", "5"])  # Scroll down

    async def _inject_gamepad(self, event: InputEvent) -> None:
        # Gamepad events mapped to keyboard via xdotool
        # In production, use uinput or evdev for proper gamepad emulation
        logger.debug("gamepad_event", event=event.model_dump())


# Active injector registry
_injectors: dict[uuid.UUID, InputInjector] = {}


async def get_or_create_injector(
    instance_id: uuid.UUID,
    container_id: str,
    display: int,
) -> InputInjector:
    if instance_id not in _injectors:
        injector = InputInjector(container_id=container_id, display=display)
        await injector.start()
        _injectors[instance_id] = injector
    return _injectors[instance_id]


async def remove_injector(instance_id: uuid.UUID) -> None:
    injector = _injectors.pop(instance_id, None)
    if injector:
        await injector.stop()


async def close_all_injectors() -> None:
    for instance_id in list(_injectors.keys()):
        await remove_injector(instance_id)
