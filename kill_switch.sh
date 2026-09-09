#!/usr/bin/env bash
# Zoovy Emergency Kill Switch & Resource Cleanup
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_ZOOVY="$HOME/.zoovy"

echo "🛑 Zoovy Emergency Kill Switch"
echo "Terminating lingering Zoovy processes..."

pkill -f "python.*zoovy" 2>/dev/null || true
pkill -f "ollama.*serve" 2>/dev/null || true

if [ "$1" == "--all" ] || [ "$1" == "-a" ]; then
    echo "Purging .venv and ~/.zoovy..."
    rm -rf "$SCRIPT_DIR/.venv" 2>/dev/null || true
    rm -rf "$HOME_ZOOVY" 2>/dev/null || true
fi

echo "✓ Zoovy processes and resources released."
