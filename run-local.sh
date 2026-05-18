#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT_DIR"

uv sync

cd frontend
npm install
npm run build

cd "$ROOT_DIR"
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
