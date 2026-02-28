"""Prometheus metrics for monitoring the cloud gaming platform."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

# Application info
app_info = Info("cloud_gaming", "Cloud Gaming Platform")

# Active sessions
active_sessions = Gauge(
    "cloud_gaming_active_sessions",
    "Number of active gaming sessions",
)

# Active streams
active_streams = Gauge(
    "cloud_gaming_active_streams",
    "Number of active video streams",
)

# Session lifecycle
sessions_created = Counter(
    "cloud_gaming_sessions_created_total",
    "Total number of sessions created",
    ["game", "resolution"],
)

sessions_ended = Counter(
    "cloud_gaming_sessions_ended_total",
    "Total number of sessions ended",
    ["reason"],  # timeout, user_initiated, error
)

# Streaming metrics
stream_fps = Gauge(
    "cloud_gaming_stream_fps",
    "Current streaming FPS",
    ["instance_id"],
)

stream_bitrate = Gauge(
    "cloud_gaming_stream_bitrate_kbps",
    "Current stream bitrate in kbps",
    ["instance_id"],
)

stream_latency_ms = Histogram(
    "cloud_gaming_stream_latency_ms",
    "End-to-end streaming latency in milliseconds",
    buckets=[5, 10, 20, 30, 50, 75, 100, 150, 200, 500],
)

# Input metrics
input_events_total = Counter(
    "cloud_gaming_input_events_total",
    "Total input events processed",
    ["type"],  # keyboard, mouse_move, mouse_button, gamepad
)

input_latency_ms = Histogram(
    "cloud_gaming_input_latency_ms",
    "Input injection latency in milliseconds",
    buckets=[1, 2, 5, 10, 20, 50, 100],
)

# Resource usage
node_cpu_usage = Gauge(
    "cloud_gaming_node_cpu_usage_percent",
    "Node CPU usage percentage",
    ["node_id"],
)

node_memory_usage = Gauge(
    "cloud_gaming_node_memory_usage_mb",
    "Node memory usage in MB",
    ["node_id"],
)

node_gpu_usage = Gauge(
    "cloud_gaming_node_gpu_usage_percent",
    "Node GPU usage percentage",
    ["node_id"],
)

# HTTP metrics
http_requests_total = Counter(
    "cloud_gaming_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "cloud_gaming_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# WebSocket metrics
websocket_connections = Gauge(
    "cloud_gaming_websocket_connections",
    "Active WebSocket connections",
    ["type"],  # input, signaling
)

# Queue metrics
queue_length = Gauge(
    "cloud_gaming_queue_length",
    "Current game launch queue length",
)

queue_wait_time_seconds = Histogram(
    "cloud_gaming_queue_wait_time_seconds",
    "Time spent waiting in launch queue",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

# Auth metrics
auth_attempts = Counter(
    "cloud_gaming_auth_attempts_total",
    "Authentication attempts",
    ["result"],  # success, failure
)
