#!/bin/bash
# =============================================================================
#                            CREATE SAMPLE SCRIPT
# =============================================================================
# Creates a 90-second sample from your MKV file for testing encode settings.
# Clip is taken from the 03:00 to 04:30 timestamp.
# =============================================================================

echo "Place your mkv file in this folder and run this. It will create a 90 second"
echo "sample mkv you can use for testing different encode settings."
echo ""
read -p "Press Enter to continue..."

# Change to script directory
cd "$(dirname "$0")"

# Check for mkvmerge
if ! command -v mkvmerge &> /dev/null; then
    echo "[ERROR] mkvmerge not found. Please install mkvtoolnix:"
    echo "        sudo apt install mkvtoolnix"
    exit 1
fi

# Find the first MKV file in the current directory
INPUT_FILE=$(find . -maxdepth 1 -name "*.mkv" -type f | head -n 1)

if [ -z "$INPUT_FILE" ]; then
    echo "[ERROR] No .mkv files found in this folder."
    exit 1
fi

# Get just the filename for the output
BASENAME=$(basename "$INPUT_FILE")
OUTPUT_FILE="sample_${BASENAME}"

echo ""
echo "Processing: $INPUT_FILE"
echo ""

# Run mkvmerge
# --no-audio: drops audio tracks
# --split parts:00:03:00-00:04:30: keeps a 90 second section (3min to 4:30min)
mkvmerge -o "$OUTPUT_FILE" --no-audio --split parts:00:03:00-00:04:30 "$INPUT_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "[SUCCESS] Sample created: $OUTPUT_FILE"
else
    echo ""
    echo "[FAILURE] Something went wrong."
fi
