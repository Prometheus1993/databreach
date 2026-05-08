FROM python:3.11-slim

WORKDIR /app

COPY build/web/ ./static/
COPY serve.py ./serve.py

EXPOSE 3078

CMD ["python3", "-u", "serve.py", "3078", "static"]
