#!/bin/bash
# Wrapper script for Light Denoise Tool
# Uses x265 (lossless) and DFTTest (VapourSynth)

# Set up paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TOOLS_DIR="$ROOT_DIR/tools"
PYTHON_SCRIPT="$TOOLS_DIR/light-denoise-x265-lossless.py"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

echo "=========================================================="
echo "    Auto-Boost-Av1an (Linux) - Light Denoise Tool"
echo "=========================================================="
echo "This tool will apply a light DFTTest denoise using Vspipe"
echo "and encode to Lossless x265."
echo ""
echo "It processes all .mkv files in the CURRENT directory."
echo "=========================================================="

# Run the python script
python3 "$PYTHON_SCRIPT" "$@"

read -p "Press Enter to exit..."
