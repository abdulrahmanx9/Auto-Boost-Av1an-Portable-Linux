#!/bin/bash
# Forced Aspect Ratio Remuxer for Linux
# --------------------------------------
# Use this script after AV1 encoding is complete.
# This script will remux files and copy over a forced aspect ratio from source files.

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TOOLS_DIR="$ROOT_DIR/tools"
PYTHON_SCRIPT="$TOOLS_DIR/forced-aspect-remux.py"

echo "==============================================================================="
echo "                           ASPECT RATIO REMUXER"
echo "==============================================================================="
echo ""
echo "Use this script after AV1 encoding is complete."
echo "This script will remux files and copy over a forced aspect ratio from"
echo "source files."
echo ""
echo "Requirements: mkvtoolnix (mkvmerge) must be installed."
echo "              sudo apt install mkvtoolnix"
echo ""
echo "The script looks for '*-output.mkv' files and their matching sources."
echo "==============================================================================="
echo ""

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "[ERROR] Could not find forced-aspect-remux.py at: $PYTHON_SCRIPT"
    exit 1
fi

# Check for mkvmerge
if ! command -v mkvmerge &> /dev/null; then
    echo "[ERROR] mkvmerge not found. Install with: sudo apt install mkvtoolnix"
    exit 1
fi

echo "Starting Python Remuxer..."
echo "-------------------------------------------------------------------------------"

python3 "$PYTHON_SCRIPT"

echo ""
echo "Process complete."
read -p "Press Enter to exit..."
