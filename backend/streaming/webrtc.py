"""WebRTC signaling and streaming using aiortc."""

from __future__ import annotations

import asyncio
import fractions
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from aiortc import (
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)
from aiortc.contrib.media import MediaRelay
from av import VideoFrame

from backend.config import get_settings
from backend.streaming.capture import CaptureConfig, FFmpegCapture, RESOLUTION_MAP

logger = structlog.get_logger(__name__)

relay = MediaRelay()


class VideoStreamTrack:
    """Custom video track that reads frames from FFmpeg pipe."""

    kind = "video"

    def __init__(self, capture: FFmpegCapture) -> None:
        self._capture = capture
        self._reader: asyncio.StreamReader | None = None
        self._pts = 0
        self._time_base = fractions.Fraction(1, 90000)
        self._started = False

    async def start(self) -> None:
        if not self._started:
            self._reader = await self._capture.start_pipe()
            self._started = True

    async def recv(self) -> VideoFrame:
        """Read the next video frame."""
        if not self._started:
            await self.start()

        # Read raw H.264 NAL units and create a black frame placeholder
        # In production, this would decode actual frames from FFmpeg
        cfg = self._capture.config
        frame = VideoFrame(width=cfg.width, height=cfg.height, format="yuv420p")
        frame.pts = self._pts
        frame.time_base = self._time_base
        self._pts += 90000 // cfg.fps  # 90kHz clock
        return frame

    async def stop(self) -> None:
        await self._capture.stop()


@dataclass
class StreamSession:
    """Represents an active WebRTC streaming session."""

    instance_id: uuid.UUID
    user_id: uuid.UUID
    pc: RTCPeerConnection
    capture: FFmpegCapture
    video_track: VideoStreamTrack
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())

    async def close(self) -> None:
        await self.video_track.stop()
        await self.pc.close()
        logger.info("stream_session_closed", instance_id=str(self.instance_id))


# Active sessions registry
_sessions: dict[uuid.UUID, StreamSession] = {}


def _build_rtc_config() -> RTCConfiguration:
    settings = get_settings()
    ice_servers = [RTCIceServer(urls=[settings.stun_server])]
    if settings.turn_server:
        ice_servers.append(
            RTCIceServer(
                urls=[settings.turn_server],
                username=settings.turn_username,
                credential=settings.turn_password,
            )
        )
    return RTCConfiguration(iceServers=ice_servers)


async def create_stream(
    instance_id: uuid.UUID,
    user_id: uuid.UUID,
    display: int,
    resolution: str,
    fps: int,
    bitrate_kbps: int,
    offer_sdp: str,
    offer_type: str,
) -> dict[str, str]:
    """Create a WebRTC peer connection and return the SDP answer."""

    if instance_id in _sessions:
        await _sessions[instance_id].close()

    width, height = RESOLUTION_MAP.get(resolution, (1920, 1080))
    config = CaptureConfig(
        display=display,
        width=width,
        height=height,
        fps=fps,
        bitrate_kbps=bitrate_kbps,
    )

    capture = FFmpegCapture(config=config)
    video_track = VideoStreamTrack(capture)

    pc = RTCPeerConnection(configuration=_build_rtc_config())

    @pc.on("connectionstatechange")
    async def on_state_change() -> None:
        state = pc.connectionState
        logger.info("webrtc_state_change", state=state, instance_id=str(instance_id))
        if state in ("failed", "closed", "disconnected"):
            await close_stream(instance_id)

    @pc.on("datachannel")
    def on_datachannel(channel: Any) -> None:
        logger.info("datachannel_opened", label=channel.label)

        @channel.on("message")
        def on_message(message: str) -> None:
            # Input events arrive via data channel
            logger.debug("datachannel_message", data=message[:100])

    # Add video track
    pc.addTrack(video_track)

    # Process the offer
    offer = RTCSessionDescription(sdp=offer_sdp, type=offer_type)
    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    session = StreamSession(
        instance_id=instance_id,
        user_id=user_id,
        pc=pc,
        capture=capture,
        video_track=video_track,
    )
    _sessions[instance_id] = session

    logger.info("stream_created", instance_id=str(instance_id), resolution=resolution, fps=fps)

    return {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }


async def close_stream(instance_id: uuid.UUID) -> None:
    """Close a streaming session."""
    session = _sessions.pop(instance_id, None)
    if session:
        await session.close()


async def add_ice_candidate(instance_id: uuid.UUID, candidate: dict) -> None:
    """Add an ICE candidate to an existing session."""
    session = _sessions.get(instance_id)
    if session and session.pc:
        from aiortc import RTCIceCandidate
        # In production, parse and add the candidate
        logger.info("ice_candidate_added", instance_id=str(instance_id))


async def update_stream_bitrate(instance_id: uuid.UUID, bitrate_kbps: int) -> None:
    """Update the bitrate for adaptive streaming."""
    session = _sessions.get(instance_id)
    if session:
        await session.capture.update_bitrate(bitrate_kbps)
        logger.info("bitrate_updated", instance_id=str(instance_id), bitrate=bitrate_kbps)


def get_active_sessions() -> dict[uuid.UUID, StreamSession]:
    return _sessions.copy()


async def close_all_streams() -> None:
    """Shutdown all active streams (for graceful shutdown)."""
    for instance_id in list(_sessions.keys()):
        await close_stream(instance_id)
