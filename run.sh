#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Building frontend..."
cd frontend
npm run build

echo "Starting backend..."
cd ../backend
uv run python -m main
