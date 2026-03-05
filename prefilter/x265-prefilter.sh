#!/bin/bash
# =============================================================================
#                         x265 PREFILTER SCRIPT
# =============================================================================
# Combined script for applying filters (Denoise/Deband/Downscale) using 
# VapourSynth and x265 lossless encoding.
# Edit settings.txt to configure filter options.
#
# - Lossless files can be huge.
# - CPU encoding is slower than NVIDIA GPU.
# =============================================================================

echo "Place your mkv file in this folder then run this."
echo "It will apply filters (Denoise/Deband/Downscale) based on settings.txt"
echo "and encode in x265 lossless 10-bit mode (CPU)."
echo ""
echo "- Lossless files can be huge."
echo "- CPU encoding is slower than NVIDIA GPU."
echo ""
read -p "Press Enter to continue..."

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TOOL_SCRIPT="$ROOT_DIR/tools/x265-prefilter.py"

# Check for x265
if ! command -v x265 &> /dev/null; then
    echo "[ERROR] x265 not found in PATH."
    echo "Install with: sudo apt install x265"
    exit 1
fi

if [ ! -f "$TOOL_SCRIPT" ]; then
    echo "[ERROR] tools/x265-prefilter.py not found!"
    exit 1
fi

echo "Starting x265 Prefilter Workflow..."
python3 "$TOOL_SCRIPT"

# Cleanup ffindex files if any remain
rm -f *.ffindex 2>/dev/null

echo ""
echo "Done."
