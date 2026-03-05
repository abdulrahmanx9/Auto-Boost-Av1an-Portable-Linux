import os
import subprocess
import time
import sys
import threading

# Configuration
# On Linux, usually "du" is used to check sizes.
# "compact" is Windows-only. We will just report sizes.
FOLDERS_TO_CHECK = ["VapourSynth", "tools"]


def get_dir_size(path):
    total = 0
    try:
        # Use simple os.walk to be cross-platform python
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                total += os.path.getsize(fp)
    except Exception:
        pass
    return total


def format_size(size_bytes):
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def main():
    print("Checking disk usage for tools...")

    total_bytes = 0
    file_count = 0

    for folder in FOLDERS_TO_CHECK:
        if os.path.exists(folder):
            c = 0
            size = 0
            for root, dirs, files in os.walk(folder):
                for f in files:
                    c += 1
                    fp = os.path.join(root, f)
                    size += os.path.getsize(fp)

            print(f"Folder '{folder}': {c} files, {format_size(size)}")
            total_bytes += size
            file_count += c
        else:
            print(f"Folder '{folder}' not found (skipped).")

    print("-" * 60)
    print(f"Total Files: {file_count}")
    print(f"Total Size:  {format_size(total_bytes)}")
    print("-" * 60)
    print("NOTE: 'compact' compression is Windows-specific.")
    print("On Linux, use filesystem compression (btrfs/zfs) or standard archives.")
    print("-" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
