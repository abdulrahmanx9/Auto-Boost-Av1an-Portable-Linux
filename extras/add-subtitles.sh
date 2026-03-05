#!/bin/bash
# =============================================================================
#                            SUBTITLE MUXER
# =============================================================================
# Adds subtitles (.ass/.srt) and fonts (.ttf/.otf) to your MKV files.
#
# [1] SINGLE FILE MODE:
#     If you have one MKV and one subtitle file (e.g., "French.ass"),
#     the script will simply combine them. The subtitle track will be named
#     "French" and tagged as French language.
#
# [2] BATCH MODE (MULTIPLE EPISODES):
#     If you have multiple episodes, rename them using S01E01 format.
#     The script will automatically match files:
#       * MKV: "MyShow.S01E01.1080p.mkv"
#       * SUB: "S01E01.French.ass"
#
# [FONTS]:
#     Any .ttf or .otf files found in this folder will be attached
#     to EVERY MKV processed.
# =============================================================================

echo "==============================================================================="
echo "                           SUBTITLE MUXER"
echo "==============================================================================="
echo ""
echo "This tool adds subtitles (.ass/.srt) and fonts (.ttf/.otf) to your MKV files."
echo ""
echo "[1] SINGLE FILE MODE:"
echo "    If you have one MKV and one subtitle file (e.g., \"French.ass\"),"
echo "    the script will simply combine them."
echo ""
echo "[2] BATCH MODE (MULTIPLE EPISODES):"
echo "    Rename files using S01E01 format for automatic matching."
echo ""
echo "[FONTS]:"
echo "    Any .ttf or .otf files found will be attached to ALL MKVs."
echo ""
echo "Use subtitles made for your source: JPBD subs for a JPBD encode, etc."
echo ""
read -p "Press any key to start..."

# Change to script directory (this is the target directory)
cd "$(dirname "$0")"
TARGET_DIR="$(pwd)"

# Get path to the tools directory (one level up from extras)
TOOLS_DIR="$(dirname "$TARGET_DIR")/tools"

# Check for Python script
if [ ! -f "$TOOLS_DIR/add-subtitles.py" ]; then
    echo "[ERROR] Could not find add-subtitles.py in tools folder."
    exit 1
fi

# Run the Python script and pass the target directory
python3 "$TOOLS_DIR/add-subtitles.py" "$TARGET_DIR"

echo ""
echo "Process complete."
