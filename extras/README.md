Auto-Boost-Av1an Extras (Linux)
===============================

This folder contains helper scripts for additional workflows.  
Make sure to run `chmod +x *.sh` before executing any scripts.

## Included Scripts

### 1. encode-opus-audio.sh
- Scans the `Input/` directory and the current directory for MKV files.
- Extracts audio tracks and converts them to the efficient Opus format.
- Muxes the converted audio back into the video containers in `Output/`.
- Useful for reducing file size while maintaining high audio quality.

### 2. lossless-intermediary.sh
- Converts source files into lossless intermediate formats suitable for editing.
- Uses VapourSynth for processing and export.

### 3. compare.sh
- Runs the `comp.py` script to generate comparison screenshots or metrics.
- Cleans up temporary comparison files after execution.

## Notes
- `compress-folders` is not included, as it relies on Windows NTFS compression.
- On Linux, consider filesystem-level compression (e.g. **btrfs** or **zfs**) if needed.

