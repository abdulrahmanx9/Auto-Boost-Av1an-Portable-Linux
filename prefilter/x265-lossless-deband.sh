#!/bin/bash
# Auto-Boost-Av1an: x265 Lossless Deband Script
# Applies VapourSynth placebo deband filter with x265 lossless encoding

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TOOL_SCRIPT="$ROOT_DIR/tools/deband-x265-lossless.py"

echo "=================================================="
echo "x265 Lossless Deband Script"
echo "=================================================="
echo "Place your .mkv files in this folder, then run this."
echo "It will apply a deband filter using VapourSynth placebo"
echo "based on settings.txt and encode in x265 lossless mode."
echo ""
echo "- Uses CPU encoding (no GPU required)."
echo "- Requires VapourSynth with placebo plugin."
echo ""

# Check for dependencies
if ! command -v x265 &> /dev/null; then
    echo "Error: x265 not found in PATH."
    echo "Install with: sudo apt install x265"
    exit 1
fi

if ! command -v vspipe &> /dev/null; then
    echo "Error: vspipe (VapourSynth) not found in PATH."
    echo "Ensure VapourSynth is installed correctly."
    exit 1
fi

if [ ! -f "$TOOL_SCRIPT" ]; then
    echo "Error: tools/deband-x265-lossless.py not found!"
    exit 1
fi

echo "Starting Deband Workflow (x265 Lossless)..."
python3 "$TOOL_SCRIPT"

echo ""
echo "Done."
