#!/bin/bash
# Auto-Boost-Av1an: NVIDIA Deband Script
# Applies libplacebo deband filter using NVEncC (NVIDIA GPU required)

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TOOL_SCRIPT="$ROOT_DIR/tools/deband-nvencc.py"

echo "=================================================="
echo "NVIDIA Deband Script"
echo "=================================================="
echo "Place your .mkv files in this folder, then run this."
echo "It will apply a deband filter using libplacebo based on settings.txt"
echo "and encode in NVENC lossless mode."
echo ""
echo "- Nvenc lossless mode is near-lossless."
echo "- NVIDIA GPU required."
echo ""

# Check for nvencc
if ! command -v nvencc &> /dev/null && ! command -v NVEncC &> /dev/null; then
    echo "Error: nvencc not found in PATH."
    echo "Install from: https://github.com/rigaya/NVEnc"
    exit 1
fi

if [ ! -f "$TOOL_SCRIPT" ]; then
    echo "Error: tools/deband-nvencc.py not found!"
    exit 1
fi

echo "Starting Deband Workflow (NVIDIA)..."
python3 "$TOOL_SCRIPT"

echo ""
echo "Done."
