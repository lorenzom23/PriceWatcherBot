FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock /app/
RUN uv sync --locked --no-dev

COPY . .

CMD ["uv", "run", "--no-dev", "python", "main.py"]
