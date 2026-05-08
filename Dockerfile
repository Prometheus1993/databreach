FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Stack:
#   xvfb                       - virtual X display the game renders into
#   x11vnc                     - VNC server reading that display
#   novnc                      - HTML/JS VNC client served at /novnc/
#   matchbox-window-manager    - tiny WM so the pygame window is borderless
#   libsdl2-*                  - pygame's runtime deps
#   python3-* + pygame/aiohttp - game + the WebSocket bridge in server.py
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    xvfb \
    x11vnc \
    novnc \
    matchbox-window-manager \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    fonts-liberation \
    fonts-dejavu-core \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir pygame==2.5.2 aiohttp==3.9.5

WORKDIR /app

COPY databreach.py .
COPY server.py .
COPY static/ ./static/

EXPOSE 3078

CMD ["python3", "-u", "server.py"]
