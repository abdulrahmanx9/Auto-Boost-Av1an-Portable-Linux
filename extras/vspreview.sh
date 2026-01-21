#!/bin/bash
# =============================================================================
#                            VSPREVIEW TOOL
# =============================================================================
# Opens vspreview for viewing your MKV files. Useful for comparing files 
# locally or finding frame numbers for zones txt files.
#
# CONTROLS:
#   - Press 1, 2, 3, etc. to switch between loaded videos
#   - Use Ctrl+MouseWheel to zoom in and out
# =============================================================================

echo "Place your mkv file(s) in this folder then run this script."
echo "It will open vspreview for viewing your mkv files."
echo ""
echo "CONTROLS:"
echo "  - Press 1, 2, 3, etc. to switch between loaded videos"
echo "  - Use Ctrl+MouseWheel to zoom in and out"
echo ""
read -p "Press Enter to continue..."

# Change to script directory
cd "$(dirname "$0")"

# Get path to the tools directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS_DIR="$(dirname "$SCRIPT_DIR")/tools"

# Check for Python script
if [ ! -f "$TOOLS_DIR/vspreview-dispatch.py" ]; then
    echo "[ERROR] Could not find vspreview-dispatch.py in tools folder."
    exit 1
fi

# Run the dispatcher script
python3 "$TOOLS_DIR/vspreview-dispatch.py"

# Cleanup (failsafe if Python crashes)
rm -f *.ffindex *.vpy 2>/dev/null
rm -rf .vsjet 2>/dev/null

clear
