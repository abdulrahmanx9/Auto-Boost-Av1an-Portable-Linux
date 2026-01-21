#!/bin/bash
# =============================================================================
#                            SIMPLE REMUX TOOL
# =============================================================================
# This tool "remuxes" your video files. It takes the video, audio, and 
# subtitles etc from your file and packages them cleanly into a new MKV 
# container.
#
# WHY USE THIS?
# 1. It fixes "problematic" headers or container errors that might cause 
#    your encoder to crash.
# 2. It does NOT re-encode (no quality loss).
# 3. It is very fast.
#
# SUPPORTED FILES: .mkv, .mp4, .m2ts
# =============================================================================

echo "========================================================"
echo "                SIMPLE REMUX TOOL"
echo "========================================================"
echo ""
echo "WHAT THIS DOES:"
echo "This tool remuxes your video files into clean MKV containers."
echo ""
echo "WHY USE THIS?"
echo "1. Fixes problematic headers/container errors"
echo "2. No re-encoding (no quality loss)"
echo "3. Very fast"
echo ""
echo "SUPPORTED FILES: .mkv, .mp4, .m2ts"
echo ""
read -p "Press Enter to start scanning for files..."

# Change to script directory
cd "$(dirname "$0")"

# Check for mkvmerge
if ! command -v mkvmerge &> /dev/null; then
    echo ""
    echo "[ERROR] mkvmerge not found. Please install mkvtoolnix:"
    echo "        sudo apt install mkvtoolnix"
    exit 1
fi

count=0

echo ""
echo "Scanning for files..."
echo "--------------------------------------------------------"

shopt -s nullglob

# Loop through supported extensions
for file in *.mkv *.mp4 *.m2ts; do
    # Skip files that are already remuxes
    if [[ "$file" == *"_remux.mkv" ]]; then
        continue
    fi
    
    ((count++))
    
    BASENAME="${file%.*}"
    OUTPUT_FILE="${BASENAME}_remux.mkv"
    
    echo ""
    echo "[Processing File #$count]"
    echo "Input:  $file"
    echo "Output: $OUTPUT_FILE"
    
    # Run mkvmerge
    mkvmerge -o "$OUTPUT_FILE" "$file"
    
    if [ $? -eq 0 ]; then
        echo "[STATUS] Success!"
    else
        echo "[STATUS] Failed."
    fi
done

echo ""
echo "--------------------------------------------------------"
if [ $count -eq 0 ]; then
    echo "No suitable files (.mkv, .mp4, .m2ts) found to remux."
else
    echo "All operations complete. Processed $count file(s)."
fi
