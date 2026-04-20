FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    xvfb \
    xdotool \
    ffmpeg \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir pygame==2.5.2 aiohttp==3.9.5

WORKDIR /app

COPY databreach.py .
COPY server.py .
COPY static/ ./static/

EXPOSE 3078

CMD ["python3", "server.py"]
