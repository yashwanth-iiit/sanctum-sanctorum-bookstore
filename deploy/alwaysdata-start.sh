#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
SANCTUM_DATA_DIR="${SANCTUM_DATA_DIR:-$HOME/sanctum-data}"
mkdir -p "$SANCTUM_DATA_DIR"
export SANCTUM_DATABASE_URL="sqlite:///$SANCTUM_DATA_DIR/sanctum.db"
export PYTHONDONTWRITEBYTECODE=1
exec .venv/bin/uvicorn app.main:app --host "${IP:?Hosting IP is required}" --port "${PORT:?Hosting PORT is required}"
