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
    echo "[1/3] Creating virtual environment (.venv)..."
    python3 -m venv .venv
else
    echo "[1/3] Virtual environment (.venv) already exists."
fi

echo "[2/3] Installing Zoovy and zero-browser MCP dependencies..."
source .venv/bin/activate
pip install -e .

echo "[3/3] Adding Zoovy to PATH..."
BIN_DIR="$(pwd)/.venv/bin"
USER_BIN="$HOME/.local/bin"

mkdir -p "$USER_BIN"
ln -sf "$BIN_DIR/zoovy" "$USER_BIN/zoovy"
chmod +x "$USER_BIN/zoovy"

for RC in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    if [ -f "$RC" ]; then
        if ! grep -q '\.local/bin' "$RC" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC"
        fi
    fi
done

echo ""
echo "============================================"
echo "   Zoovy Setup Completed Successfully! (MCP Mode)"
echo "============================================"
echo "Zoovy CLI linked to: $USER_BIN/zoovy"
if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
    echo "[NOTE] $USER_BIN is not yet in your current shell PATH."
    echo "       Run: export PATH=\"\$HOME/.local/bin:\$PATH\" or open a new terminal."
else
    echo "[OK] zoovy is ready to use directly in your PATH!"
fi
echo ""
echo "Next steps:"
echo "  1. Run diagnosis:  zoovy doctor"
echo "  2. Download model: zoovy setup"
echo "  3. Order via MCP:  zoovy order 'Get 4 cans of diet coke'"

