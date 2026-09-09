#!/usr/bin/env bash
set -e
echo "============================================"
echo "   Setting up Zoovy Environment (Linux/macOS)"
echo "============================================"

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[1/2] Creating virtual environment (.venv)..."
    python3 -m venv .venv
else
    echo "[1/2] Virtual environment (.venv) already exists."
fi

echo "[2/2] Installing Zoovy and zero-browser MCP dependencies..."
source .venv/bin/activate
pip install -e .

echo ""
echo "============================================"
echo "   Zoovy Setup Completed Successfully! (MCP Mode)"
echo "============================================"
echo "Next steps:"
echo "  1. Activate venv:  source .venv/bin/activate"
echo "  2. Run diagnosis:  zoovy doctor"
echo "  3. Download model: zoovy setup"
echo "  4. Order via MCP:  zoovy order 'Get 4 cans of diet coke'"

