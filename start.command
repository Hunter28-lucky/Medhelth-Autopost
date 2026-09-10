#!/bin/bash
# ==============================================================================
# PulsePublish Local Launcher (by Krish Goswami)
# Starts the backend, checks dependencies, builds UI, and opens dashboard.
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=========================================================="
echo "  PulsePublish AI Medical/AI News Publisher"
echo "  Developed by Krish Goswami"
echo "=========================================================="

# 1. Setup Virtualenv if needed
if [ ! -d "backend/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv backend/venv
    ./backend/venv/bin/pip install --upgrade pip
    ./backend/venv/bin/pip install -r backend/requirements.txt
fi

# 2. Build Frontend UI if dist doesn't exist
if [ ! -d "frontend/dist" ]; then
    echo "Building dashboard frontend..."
    cd frontend && npm install && npm run build && cd ..
fi

# 3. Start Backend Server
echo "Starting PulsePublish engine on http://127.0.0.1:8081..."
echo "Developer Login Key: krish@dev2026"
echo "Press CTRL+C to stop."

PYTHONPATH=. ./backend/venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8081
