# One image for every labpipe job. Compose runs it with a different command per service.
FROM python:3.13-slim

# uv, pinned, copied from its official image.
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, in their own layer, so code changes don't reinstall them.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the project itself, the SQL migrations and vocabulary it loads, and the BMP sample
# the mock LIS reads.
COPY src ./src
COPY db ./db
COPY data/sample ./data/sample
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

CMD ["labpipe", "--help"]
