#!/bin/bash
# Auto-Boost-Av1an: Lossless Intermediary Workflow
# Creates lossless intermediate files for editing/processing

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TOOL_SCRIPT="$ROOT_DIR/tools/lossless-intermediary.py"

if [ ! -f "$TOOL_SCRIPT" ]; then
    echo "Error: tools/lossless-intermediary.py not found!"
    exit 1
fi

echo "Launching Lossless Intermediary Script..."
python3 "$TOOL_SCRIPT"

echo ""
# Cleanup index files
rm -f *.ffindex *.vpy 2>/dev/null
echo "Done."
