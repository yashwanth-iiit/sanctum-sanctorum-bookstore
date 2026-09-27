FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.10 /uv /bin/uv

WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-cache

COPY app ./app
COPY frontend ./frontend
COPY deploy ./deploy
RUN useradd --uid 10001 --create-home sanctum && mkdir -p /data && chown sanctum:sanctum /data

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    SANCTUM_DATABASE_URL=sqlite:////data/sanctum.db
USER sanctum
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health', timeout=3)"
CMD ["sh", "deploy/start.sh"]
