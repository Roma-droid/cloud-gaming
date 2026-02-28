#!/bin/bash
set -e

# Start virtual framebuffer
Xvfb ${DISPLAY} -screen 0 ${RESOLUTION}x${COLOR_DEPTH:-24} -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for display to be ready
sleep 1

# Start PulseAudio for audio
pulseaudio --start --exit-idle-time=-1 2>/dev/null || true

echo "Virtual display started at ${DISPLAY} with resolution ${RESOLUTION}"

# Launch the game if specified
if [ -n "${GAME_LAUNCH_CMD}" ]; then
    echo "Launching game: ${GAME_LAUNCH_CMD}"
    eval "${GAME_LAUNCH_CMD}" &
    GAME_PID=$!
fi

# Graceful shutdown handler
cleanup() {
    echo "Shutting down..."
    [ -n "${GAME_PID}" ] && kill ${GAME_PID} 2>/dev/null
    kill ${XVFB_PID} 2>/dev/null
    exit 0
}

trap cleanup SIGTERM SIGINT

# Keep container running
wait ${XVFB_PID}
