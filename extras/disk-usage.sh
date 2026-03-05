#!/bin/bash
# Disk Usage Checker for Linux
# -----------------------------
# Note: NTFS "compact" compression is Windows-only.
# This script reports disk usage instead.

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TOOLS_DIR="$ROOT_DIR/tools"
PYTHON_SCRIPT="$TOOLS_DIR/compress-folders.py"

echo "=========================================================="
echo "           Disk Usage Checker (Linux)"
echo "=========================================================="
echo ""
echo "NOTE: The Windows version uses NTFS 'compact' compression"
echo "which is not available on Linux."
echo ""
echo "This script will report disk usage for the tools folder."
echo "For compression on Linux, consider:"
echo "  - btrfs/zfs filesystem compression"
echo "  - tar/gzip/xz archives"
echo ""
echo "=========================================================="
echo ""

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "[ERROR] Could not find compress-folders.py at: $PYTHON_SCRIPT"
    exit 1
fi

# Change to root directory for proper path resolution
cd "$ROOT_DIR"

python3 "$PYTHON_SCRIPT"

read -p "Press Enter to exit..."
