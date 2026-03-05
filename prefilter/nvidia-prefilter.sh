#!/bin/bash
# =============================================================================
#                       NVIDIA PREFILTER SCRIPT
# =============================================================================
# Combined script for applying filters (Denoise/Deband/Downscale) using NVEncC.
# Edit settings.txt to configure filter options.
#
# - NVENC lossless mode is near-lossless.
# - NVIDIA GPU required.
# =============================================================================

echo "Place your mkv file in this folder then run this."
echo "It will apply filters (Denoise/Deband/Downscale) based on settings.txt"
echo "and encode in NVENC lossless mode h265 10-bit."
echo ""
echo "- NVENC lossless mode is near-lossless."
echo "- NVIDIA GPU required."
echo ""
read -p "Press Enter to continue..."

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TOOL_SCRIPT="$ROOT_DIR/tools/nvidia-prefilter.py"

# Check for nvencc
if ! command -v nvencc &> /dev/null && ! command -v NVEncC &> /dev/null; then
    echo "[ERROR] nvencc not found in PATH."
    echo "Install from: https://github.com/rigaya/NVEnc"
    exit 1
fi

if [ ! -f "$TOOL_SCRIPT" ]; then
    echo "[ERROR] tools/nvidia-prefilter.py not found!"
    exit 1
fi

echo "Starting NVIDIA Prefilter Workflow..."
python3 "$TOOL_SCRIPT"

# Cleanup ffindex files if any remain
rm -f *.ffindex 2>/dev/null

echo ""
echo "Done."
