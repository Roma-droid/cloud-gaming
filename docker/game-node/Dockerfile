# Game node container — provides a virtual display and runs games
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    xdotool \
    ffmpeg \
    pulseaudio \
    mesa-utils \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for running games
RUN useradd -ms /bin/bash gamer

# Startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER gamer
WORKDIR /home/gamer

ENV DISPLAY=:99
ENV RESOLUTION=1920x1080
ENV COLOR_DEPTH=24

ENTRYPOINT ["/entrypoint.sh"]
