#!/bin/bash

# av1an-batch-anime-crf30.sh
# Direct Av1an encode — Anime CRF 30, single pass (no Auto-Boost).
# Place source files in Input/, encoded output goes to Output/.

cd "$(dirname "$0")"

touch "tools/sh-used-$(basename "$0").txt"

WORKER_COUNT=4

# --- STEP 1A: WORKER COUNT CHECK ---
CONFIG_FILE="tools/workercount-config.txt"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "First Run Detected: Calculating optimal encode worker count..."
    python3 "tools/workercount.py"
fi

if [ -f "$CONFIG_FILE" ]; then
    WORKER_COUNT=$(grep "^workers=" "$CONFIG_FILE" | cut -d= -f2 | tr -d '\r')
fi

echo "Starting Av1an Batch (Anime CRF 30) with $WORKER_COUNT workers..."

mkdir -p Input Output
shopt -s nullglob

for f in Input/*.mkv Input/*.mp4 Input/*.m2ts; do
    [ -f "$f" ] || continue
    filename=$(basename -- "$f")
    stem="${filename%.*}"

    OUTPUT_FILE="Output/${stem}-av1.mkv"

    if [ -f "$OUTPUT_FILE" ]; then
        echo "Skipping \"$f\" — output already exists."
        continue
    fi

    echo "==============================================================================="
    echo "Processing \"$f\"..."
    echo "-------------------------------------------------------------------------------"

    # Anime Standard (CRF 30) — v1.66 5fish svt-av1-psy, single pass
    python3 tools/av1an-dispatch.py \
        -i "$f" \
        -o "$OUTPUT_FILE" \
        --quality 30 \
        --photon-noise 2 \
        --workers "$WORKER_COUNT" \
        --final-speed 4 \
        --final-params "--lp 3 --tune 0 --hbd-mds 1 --keyint 305 --noise-level-thr 16000 --lineart-psy-bias 4 --texture-psy-bias 2 --filtering-noise-detection 4"

done

# --- CLEANUP ---
echo "Cleaning up temporary files and folders..."
python3 tools/cleanup.py

echo "All tasks finished."
