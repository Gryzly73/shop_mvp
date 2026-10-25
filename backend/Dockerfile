FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

EXPOSE 8000
CMD ["uv", "run", "--no-dev", "--frozen", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
