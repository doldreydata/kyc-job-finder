#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Check for .env
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Run: cp .env.example .env and fill in your keys."
    exit 1
fi

# Activate venv or create one
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -q -r requirements.txt
    echo "Done — run ./run.sh again"
    exit 0
fi

# Run it
echo ""
python main.py
