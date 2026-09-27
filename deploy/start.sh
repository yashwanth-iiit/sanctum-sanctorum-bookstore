#!/bin/sh
set -eu

# exec forwards shutdown signals to the single application process.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
