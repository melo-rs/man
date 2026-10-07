FROM python:3.14-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_SYNC=1
ENV UV_NO_CACHE=1
ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app

COPY pyproject.toml .
COPY uv.lock .

RUN uv sync --locked

COPY . .

CMD ["uv", "run", "uvicorn", "man.app:app", "--host", "0.0.0.0", "--port", "10000"]
