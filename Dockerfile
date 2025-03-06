FROM python:3.10-slim

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /app

WORKDIR /app

ENV PYTHONPATH=/app

RUN uv sync --frozen --no-cache

CMD ["uv", "run", "api/main.py", "--host", "0.0.0.0"]
