#!/bin/bash

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

echo "Starting Auto-Boost-Av1an with $WORKER_COUNT final-pass workers..."
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

    # Anime Higher (CRF 15) Params
    python3 tools/dispatch.py -i "$f" -o "$OUTPUT_FILE" --scenes "$SCENE_FILE" \
        --quality 15 \
        --aggressive \
        --ssimu2 "$SSIMU2_TOOL" \
        --ssimu2-cpu-workers "$SSIMU2_WORKERS" \
        --resume \
        --verbose \
        --photon-noise 2 \
        --workers "$WORKER_COUNT" \
        --fast-speed 8 \
        --final-speed 4 \
        --fast-params "--ac-bias 1.0 --complex-hvs 1 --keyint -1 --variance-boost-strength 1 --enable-dlf 2 --noise-level-thr 16000 --variance-md-bias 1 --cdef-bias 1 --luminance-qp-bias 20 --qm-min 8 --keyint -1 --tune 0 --balancing-q-bias 1 --chroma-qmc-bias 2 --filtering-noise-detection 4 --balancing-r0-based-layer-offset 0 --chroma-qm-min 10" \
        --final-params "--ac-bias 1.0 --complex-hvs 1 --keyint -1 --variance-boost-strength 1 --enable-dlf 2 --noise-level-thr 16000 --variance-md-bias 1 --cdef-bias 1 --luminance-qp-bias 20 --qm-min 8 --keyint -1 --tune 0 --balancing-q-bias 1 --chroma-qmc-bias 2 --filtering-noise-detection 4 --balancing-r0-based-layer-offset 0 --chroma-qm-min 10 --lp 3"

done

echo "Starting Muxing Process..."
python3 tools/mux.py

echo "Tagging output files..."
python3 tools/tag.py

echo "Cleaning up temporary files and folders..."
python3 tools/cleanup.py
