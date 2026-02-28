"""Video capture module using FFmpeg for screen grabbing and encoding."""

from __future__ import annotations

import asyncio
import signal
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CaptureConfig:
    display: int = 99
    width: int = 1920
    height: int = 1080
    fps: int = 60
    bitrate_kbps: int = 6000
    codec: str = "h264"
    use_hw_encoding: bool = False
    hw_encoder: str = "h264_nvenc"  # h264_nvenc, h264_vaapi
    preset: str = "p1"  # NVENC: p1(fastest)-p7 / x264: ultrafast-veryslow
    tune: str = "zerolatency"
    pixel_format: str = "yuv420p"
    gop_size: int = 30  # Keyframe interval


RESOLUTION_MAP = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
}


@dataclass
class FFmpegCapture:
    """Manages FFmpeg process for screen capture and video encoding."""

    config: CaptureConfig
    process: asyncio.subprocess.Process | None = field(default=None, init=False)
    _running: bool = field(default=False, init=False)

    def _build_command(self, output: str) -> list[str]:
        """Build FFmpeg command for screen capture."""
        cfg = self.config
        encoder = cfg.hw_encoder if cfg.use_hw_encoding else "libx264"

        cmd = [
            "ffmpeg",
            "-nostdin",
            "-y",
            # Input: X11 screen grab
            "-f", "x11grab",
            "-framerate", str(cfg.fps),
            "-video_size", f"{cfg.width}x{cfg.height}",
            "-i", f":{cfg.display}",
            # Video encoding
            "-c:v", encoder,
            "-pix_fmt", cfg.pixel_format,
            "-b:v", f"{cfg.bitrate_kbps}k",
            "-maxrate", f"{int(cfg.bitrate_kbps * 1.5)}k",
            "-bufsize", f"{cfg.bitrate_kbps * 2}k",
            "-g", str(cfg.gop_size),
        ]

        if cfg.use_hw_encoding and "nvenc" in cfg.hw_encoder:
            cmd.extend([
                "-preset", cfg.preset,
                "-tune", "ull",  # Ultra low latency
                "-zerolatency", "1",
                "-rc", "cbr",
            ])
        else:
            cmd.extend([
                "-preset", "ultrafast",
                "-tune", cfg.tune,
            ])

        # Output
        cmd.extend([
            "-f", "rtp",
            "-flush_packets", "1",
            output,
        ])

        return cmd

    def _build_pipe_command(self) -> list[str]:
        """Build FFmpeg command that outputs raw H.264 NALUs to stdout."""
        cfg = self.config
        encoder = cfg.hw_encoder if cfg.use_hw_encoding else "libx264"

        cmd = [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-f", "x11grab",
            "-framerate", str(cfg.fps),
            "-video_size", f"{cfg.width}x{cfg.height}",
            "-i", f":{cfg.display}",
            "-c:v", encoder,
            "-pix_fmt", cfg.pixel_format,
            "-b:v", f"{cfg.bitrate_kbps}k",
            "-maxrate", f"{int(cfg.bitrate_kbps * 1.5)}k",
            "-bufsize", f"{cfg.bitrate_kbps * 2}k",
            "-g", str(cfg.gop_size),
        ]

        if not cfg.use_hw_encoding:
            cmd.extend(["-preset", "ultrafast", "-tune", cfg.tune])

        cmd.extend([
            "-f", "h264",
            "-"
        ])

        return cmd

    async def start_rtp(self, rtp_url: str) -> None:
        """Start FFmpeg sending RTP stream to the given URL."""
        if self._running:
            raise RuntimeError("Capture already running")

        cmd = self._build_command(rtp_url)
        logger.info("ffmpeg_starting", command=" ".join(cmd))

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        self._running = True
        logger.info("ffmpeg_started", pid=self.process.pid)

    async def start_pipe(self) -> asyncio.StreamReader | None:
        """Start FFmpeg outputting H.264 stream to a pipe (for WebRTC)."""
        if self._running:
            raise RuntimeError("Capture already running")

        cmd = self._build_pipe_command()
        logger.info("ffmpeg_pipe_starting", command=" ".join(cmd))

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._running = True
        logger.info("ffmpeg_pipe_started", pid=self.process.pid)
        return self.process.stdout

    async def stop(self) -> None:
        """Stop the FFmpeg process gracefully."""
        if self.process and self._running:
            self._running = False
            try:
                self.process.send_signal(signal.SIGINT)
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except TimeoutError:
                    self.process.kill()
                    await self.process.wait()
            except ProcessLookupError:
                pass
            logger.info("ffmpeg_stopped")

    async def update_bitrate(self, new_bitrate_kbps: int) -> None:
        """Restart with new bitrate for adaptive streaming."""
        was_running = self._running
        if was_running:
            await self.stop()
        self.config.bitrate_kbps = new_bitrate_kbps
        # Caller must restart with the appropriate output method

    @property
    def is_running(self) -> bool:
        return self._running and self.process is not None and self.process.returncode is None
