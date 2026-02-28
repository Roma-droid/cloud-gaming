"""Unit tests for video capture module."""

from __future__ import annotations

import pytest

from backend.streaming.capture import CaptureConfig, FFmpegCapture, RESOLUTION_MAP


class TestCaptureConfig:
    def test_default_config(self):
        cfg = CaptureConfig()
        assert cfg.width == 1920
        assert cfg.height == 1080
        assert cfg.fps == 60
        assert cfg.codec == "h264"

    def test_custom_config(self):
        cfg = CaptureConfig(width=1280, height=720, fps=30, bitrate_kbps=3000)
        assert cfg.width == 1280
        assert cfg.bitrate_kbps == 3000


class TestResolutionMap:
    def test_720p(self):
        assert RESOLUTION_MAP["720p"] == (1280, 720)

    def test_1080p(self):
        assert RESOLUTION_MAP["1080p"] == (1920, 1080)

    def test_1440p(self):
        assert RESOLUTION_MAP["1440p"] == (2560, 1440)


class TestFFmpegCapture:
    def test_build_command(self):
        cfg = CaptureConfig(display=99, width=1920, height=1080, fps=60, bitrate_kbps=6000)
        capture = FFmpegCapture(config=cfg)
        cmd = capture._build_command("rtp://127.0.0.1:5000")

        assert "ffmpeg" in cmd
        assert "-f" in cmd
        assert "x11grab" in cmd
        assert ":99" in cmd
        assert "rtp://127.0.0.1:5000" in cmd

    def test_build_pipe_command(self):
        cfg = CaptureConfig(display=42, fps=30)
        capture = FFmpegCapture(config=cfg)
        cmd = capture._build_pipe_command()

        assert cmd[-1] == "-"
        assert "h264" in cmd
        assert ":42" in cmd

    def test_hw_encoding_command(self):
        cfg = CaptureConfig(use_hw_encoding=True, hw_encoder="h264_nvenc")
        capture = FFmpegCapture(config=cfg)
        cmd = capture._build_command("rtp://127.0.0.1:5000")

        assert "h264_nvenc" in cmd

    def test_not_running_initially(self):
        capture = FFmpegCapture(config=CaptureConfig())
        assert not capture.is_running
