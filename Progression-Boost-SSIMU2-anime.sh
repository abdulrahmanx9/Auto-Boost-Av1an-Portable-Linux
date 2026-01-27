#!/bin/bash

# Notepad++ is suggested for editing this file.
ssimu2_quality="82"
echo "You may use a text editor to edit this file to adjust ssimu2_quality="
echo ""
echo "SSIMULACRA2 measures video quality the way your eyes actually see it. This script uses those measurements to"
echo "automatically pick the best compression settings for each scene in your video, keeping quality"
echo "consistent throughout."
echo ""
echo "Note: This script has been specifically designed by Miss Ashenlight to operate at svt-av1 preset 2 which is"
echo "slower and higher quality. This is not merely a suggestion, the results depend on it and changing it would"
echo "cause inaccuracy."
echo ""
echo "Quality scores provided by SSIMULACRA2 author for images, not video:"
echo ""
echo "Normal TV viewing distance:"
echo "80 = Very high quality"
echo "85 = Excellent quality"
echo "90 = Visually lossless"
echo "100 = Mathematically lossless (not recommended for encoding video)"
echo ""
echo "Do not use this on noisy sources including anime episodes with grainy flashbacks,"
echo "it will result in potentially huge files."
echo ""
read -p "Press Enter to continue..."

# Cleanup old markers
rm -f tools/bat*.txt

# --- STEP 0A: CREATE BATCH MARKER ---
echo ""
# Creating a marker ending in .sh.txt so python script can detect it
touch "tools/bat-used-Progression-Boost-SSIMU2-anime.sh.txt"

# --- STEP 0B: SET TEMP PATH ---
# In Linux, we assume tools are installed or relative.
# Use standard PATH. If you have a local VapourSynth/Av1an env, ensure it's active.
export PATH="$PWD/tools/av1an:$PWD/tools/MKVToolNix:$PATH"

# --- STEP 1A: WORKER COUNT CHECK (ENCODE) ---
if [ -f "tools/workercount-progression.txt" ]; then
    # Read the worker count from the config file
    # Format: workers=4
    source "tools/workercount-progression.txt"
    WORKER_COUNT=$workers
else
    echo ""
    echo "-------------------------------------------------------------------------------"
    echo "Progression-Boost First Run Detected: Calculating optimal encode worker count..."
    echo "-------------------------------------------------------------------------------"
    python3 "tools/progression-workercount.py"
    rm -f tools/*.lwi
    
    # Reload config after generation
    source "tools/workercount-progression.txt"
    WORKER_COUNT=$workers
    
    echo ""
    echo "Encode worker count calculated."
fi

# --- STEP 1B: WORKER COUNT CHECK (SSIMU2) ---
if [ -f "tools/workercount-ssimu2.txt" ]; then
    # Read config
    # Format: 
    # tool=vs-hip
    # workercount=4
    source "tools/workercount-ssimu2.txt"
    SSIMU2_TOOL=$tool
    SSIMU2_WORKERS=$workercount
else
    echo ""
    echo "-------------------------------------------------------------------------------"
    echo "First Run Detected: Calculating optimal SSIMU2 settings..."
    echo "-------------------------------------------------------------------------------"
    echo "Checking GPU support (vs-hip) and CPU benchmarks..."
    python3 "tools/ssimu2-workercount.py"
    
    # Read config after generation
    source "tools/workercount-ssimu2.txt"
    SSIMU2_TOOL=$tool
    SSIMU2_WORKERS=$workercount
    
    echo ""
    echo "av1an worker count and SSIMU2 benchmark complete."
    echo "You may edit workercount-progression.txt workercount-ssimu2.txt, or delete these .txt files if you want to run the benchmark again."
    read -p "Press Enter to continue..."
fi

# --- STEP 2: RENAMING ---

echo "Starting Renaming Process..."
python3 "tools/rename.py"

# --- STEP 3: PYTHON AUTOMATION ---

echo "Starting Progressive Boost"

# Loop through all *-source.mkv files
for f in *-source.mkv; do
    # Check if file exists to avoid loop running on literal string if no match
    [ -e "$f" ] || continue
    
    echo ""
    echo "-------------------------------------------------------------------------------"
    
    # Base name calculation: "MyVideo-source.mkv" -> "MyVideo"
    base_name="${f%-source.mkv}"
    output_name="${base_name}-av1.mkv"
    
    if [ -f "$output_name" ]; then
        echo "Skipping encoding for \"$f\" - Output found."
    else
        echo "Processing \"$f\"..."
        echo "-------------------------------------------------------------------------------"
        
        # Stage 1: Calculate metrics
        # CALLING DISPATCH SCRIPT TO UPDATE QUALITY SETTINGS FIRST
        python3 "tools/progression-dispatch-Basic-SSIMU2.py" -i "$f" --output-scenes "${f}.scenes.json"
        
        echo ""
        
        # Stage 2: Encode using Av1an
        echo "Starting Av1an Encode..."
        # Note: Using 'av1an' command directly from PATH or relative
        # Using -w $WORKER_COUNT (from config)
        av1an -i "$f" --no-defaults --photon-noise 2 -w "$WORKER_COUNT" -s "${f}.scenes.json" -o "$output_name"
    fi
done

# --- STEP 4: TAGGING ---
python3 "tools/progression-tag.py"

# --- STEP 5: MUXING ---
echo "Starting Muxing Process..."
python3 "tools/progression-mux.py"

echo "All tasks finished."
read -p "Press Enter to continue..."

# --- STEP 6: CLEANUP ---
echo "Cleaning up temporary files and folders..."
python3 "tools/cleanup.py"
