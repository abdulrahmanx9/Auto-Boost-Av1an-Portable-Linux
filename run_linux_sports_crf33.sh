#!/bin/bash

# Auto-Boost-Av1an: Sports / High-Motion Content (CRF 33)
# Optimized for high-motion content with extra temporal filtering

# Set the current working directory to the script's directory
cd "$(dirname "$0")"

# Create marker for tagging
touch "tools/sh-used-$(basename "$0").txt"

WORKER_COUNT=4

# --- STEP 1B: WORKER COUNT CHECK (SSIMU2) ---
CONFIG_FILE="tools/workercount-ssimu2.txt"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "First Run Detected: Calculating optimal SSIMU2 settings..."
    python3 "tools/ssimu2-workercount.py"
fi

if [ -f "$CONFIG_FILE" ]; then
    SSIMU2_TOOL=$(grep "^tool=" "$CONFIG_FILE" | cut -d= -f2 | tr -d '\r')
    SSIMU2_WORKERS=$(grep "^workercount=" "$CONFIG_FILE" | cut -d= -f2 | tr -d '\r')
else
    SSIMU2_TOOL="vs-zip"
    SSIMU2_WORKERS=4
fi

echo "Starting Auto-Boost-Av1an (Sports / High-Motion CRF 33) with $WORKER_COUNT final-pass workers..."
echo "SSIMU2 Mode: $SSIMU2_TOOL | SSIMU2 Workers: $SSIMU2_WORKERS"

mkdir -p Input Output
shopt -s nullglob

for f in Input/*.mkv; do
    filename=$(basename -- "$f")
    stem="${filename%.*}"
    OUTPUT_FILE="Output/${stem}-av1.mkv"
    SCENE_FILE="${f%.*}_scenedetect.json"

    # --- Fast-pass: Use Progressive-Scene-Detection JSON to skip av1an scene detection ---
    if [ -f "$SCENE_FILE" ]; then
        echo ""
        echo "-------------------------------------------------------------------------------"
        echo "Scene JSON found for \"$f\" - skipping scene detection."
        echo "-------------------------------------------------------------------------------"
    else
        echo ""
        echo "-------------------------------------------------------------------------------"
        echo "Detecting scenes for \"$f\"..."
        echo "-------------------------------------------------------------------------------"
        python3 tools/Progressive-Scene-Detection.py -i "$f" -o "$SCENE_FILE"
    fi

    echo ""
    echo "-------------------------------------------------------------------------------"
    echo "Processing \"$f\"..."
    echo "-------------------------------------------------------------------------------"

    # Sports / High-Motion (CRF 33) Params
    # Uses --tf-strength 3 for better temporal filtering on fast motion content
    python3 tools/dispatch.py -i "$f" -o "$OUTPUT_FILE" --scenes "$SCENE_FILE" \
        --quality 33 \
        --autocrop \
        --ssimu2 "$SSIMU2_TOOL" \
        --ssimu2-cpu-workers "$SSIMU2_WORKERS" \
        --resume \
        --verbose \
        --photon-noise 6 \
        --workers "$WORKER_COUNT" \
        --fast-speed 8 \
        --final-speed 4 \
        --fast-params "--ac-bias 0.6 --complex-hvs 1 --sharp-tx 0 --sharpness 1 --tf-strength 3 --keyint -1 --variance-boost-strength 1 --variance-octile 7 --enable-dlf 2 --tune 3" \
        --final-params "--ac-bias 0.6 --complex-hvs 1 --sharp-tx 0 --sharpness 1 --tf-strength 3 --keyint -1 --variance-boost-strength 1 --variance-octile 7 --enable-dlf 2 --tune 3 --lp 3"

done

# --- STEP 4: MUXING ---
echo "Starting Muxing Process..."
python3 tools/mux.py

# --- STEP 5: TAGGING ---
echo "Tagging output files..."
python3 tools/tag.py

# --- STEP 6: CLEANUP ---
echo "Cleaning up temporary files and folders..."
python3 tools/cleanup.py
