#!/bin/bash
# Auto-Boost-Av1an: Comparison Script
# Runs VapourSynth comparison via tools/comp.py

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TOOL_SCRIPT="$ROOT_DIR/tools/comp.py"

if [ ! -f "$TOOL_SCRIPT" ]; then
    echo "Error: tools/comp.py not found!"
    exit 1
fi

echo "Launching comparison script..."
python3 "$TOOL_SCRIPT"

echo "Comparisons complete."
echo "Cleaning up generated cache..."

# Cleanup
rm -f generated* *.lwi 2>/dev/null
rm -rf Comparisons screens 2>/dev/null
