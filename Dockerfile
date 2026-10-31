FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 1. Зависимости (меняются редко — слой хорошо кэшируется)
COPY pyproject.toml README.md ./
RUN uv sync --no-dev --no-install-project

# 2. Код проекта
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --no-dev

# Каталог для загруженных PDF (монтируется volume из docker-compose)
RUN mkdir -p /app/data

CMD ["python", "-m", "src.main"]