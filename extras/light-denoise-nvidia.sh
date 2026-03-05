#!/bin/bash
# Light Denoise (NVIDIA GPU) for Linux
# -------------------------------------
# Applies a light denoise using NVEncC (--vpp-fft3d sigma=0.2)
# and encodes in NVEnc lossless mode.

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TOOLS_DIR="$ROOT_DIR/tools"
PYTHON_SCRIPT="$TOOLS_DIR/light-denoise-nvencc.py"

echo "=========================================================="
echo "        Light Denoise (NVIDIA GPU) - Linux"
echo "=========================================================="
echo ""
echo "Place your .mkv files in the current directory."
echo ""
echo "This tool will apply a light denoise (--vpp-fft3d sigma=0.2)"
echo "and encode in NVEnc lossless mode."
echo ""
echo "Notes:"
echo "  - NVEnc lossless mode is near-lossless (not mathematically lossless)"
echo "  - This is faster than CPU-based filtering on supported systems"
echo "  - Lossless files can be huge. Process one file at a time."
echo "  - Requires NVIDIA GPU with NVEncC installed"
echo ""
echo "Requirements:"
echo "  - nvencc must be installed and in PATH"
echo "  - mkvtoolnix (mkvmerge) must be installed"
echo ""
echo "=========================================================="
echo ""

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "[ERROR] Could not find light-denoise-nvencc.py at: $PYTHON_SCRIPT"
    exit 1
fi

# Check for nvencc
if ! command -v nvencc &> /dev/null; then
    echo "[ERROR] nvencc not found in PATH."
    echo ""
    echo "To install NVEncC on Linux:"
    echo "  1. Download from: https://github.com/rigaya/NVEnc/releases"
    echo "  2. Extract and add to PATH, or copy to /usr/local/bin/"
    echo ""
    exit 1
fi

# Check for mkvmerge
if ! command -v mkvmerge &> /dev/null; then
    echo "[ERROR] mkvmerge not found. Install with: sudo apt install mkvtoolnix"
    exit 1
fi

echo "Starting Light Denoise Workflow..."
python3 "$PYTHON_SCRIPT"

read -p "Press Enter to exit..."
