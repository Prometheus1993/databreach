FROM python:3.11-slim

WORKDIR /app

COPY build/web/ ./static/

RUN python3 -c "import http.server"

EXPOSE 3078

CMD ["python3", "-m", "http.server", "3078", "--directory", "static"]
