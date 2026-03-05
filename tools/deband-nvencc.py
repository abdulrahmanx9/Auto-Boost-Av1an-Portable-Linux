#!/usr/bin/env python3
"""
Deband using NVEncC (NVIDIA GPU required)
Linux Port: Uses system FFmpeg for muxing instead of MKVToolNix
"""

import os
import glob
import subprocess
import sys
import shutil
import configparser

# --- Configuration & Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)  # Go up one level from 'tools'

# Config Path: Linux_Dist/prefilter/settings.txt
CONFIG_PATH = os.path.join(ROOT_DIR, "prefilter", "settings.txt")

# Tool Paths (use system binaries)
NVENCC_EXE = shutil.which("nvencc") or shutil.which("NVEncC")
FFMPEG_EXE = shutil.which("ffmpeg")


def load_settings():
    """Loads settings from settings.txt with fallback defaults."""
    config = configparser.ConfigParser()

    defaults = {"filter_command": "--vpp-libplacebo-deband threshold=4.0,radius=16"}

    if os.path.exists(CONFIG_PATH):
        try:
            config.read(CONFIG_PATH)
            if "NVIDIA_DEBAND" in config:
                if "filter_command" in config["NVIDIA_DEBAND"]:
                    defaults["filter_command"] = config["NVIDIA_DEBAND"][
                        "filter_command"
                    ]
            else:
                print(
                    f"[Warning] [NVIDIA_DEBAND] section not found in {CONFIG_PATH}. Using default."
                )
        except Exception as e:
            print(f"[Warning] Could not read settings.txt: {e}. Using default.")
    else:
        print(f"[Warning] Settings file not found at {CONFIG_PATH}. Using default.")

    return defaults


def run_nvencc(input_file, output_h265, settings):
    """Runs NVEncC with fallback logic."""

    filter_args = settings["filter_command"].split()

    cmd_base = [
        NVENCC_EXE,
        "--codec",
        "hevc",
        "--preset",
        "p4",
        "--output-depth",
        "10",
        "--lossless",
    ]

    cmd_base.extend(filter_args)

    cmd_base.extend(["-i", input_file, "-o", output_h265])

    # Try with --avhw (Hardware Decode) first
    cmd_primary = cmd_base[:1] + ["--avhw"] + cmd_base[1:]
    print(f"\n[NVEncC] Processing: {input_file} (Attempt 1: With --avhw)")
    print("Command:", " ".join(cmd_primary))

    result = subprocess.run(cmd_primary)

    if result.returncode == 0:
        return True

    # Fallback without --avhw
    print(f"\n[NVEncC] Attempt 1 failed. Retrying without --avhw...")
    print("Command:", " ".join(cmd_base))
    result = subprocess.run(cmd_base)

    return result.returncode == 0


def run_ffmpeg_mux(video_file, audio_source, output_file):
    """Muxes video with audio/subs from source using FFmpeg."""
    print(f"[FFmpeg] Muxing: {output_file}")

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i",
        video_file,
        "-i",
        audio_source,
        "-map",
        "0:v:0",
        "-map",
        "1:a?",
        "-map",
        "1:s?",
        "-c",
        "copy",
        output_file,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[FFmpeg] Error: {result.stderr}")
        return False
    return True


def main():
    if not NVENCC_EXE:
        print("Error: NVEncC not found in PATH.")
        print("Install it from: https://github.com/rigaya/NVEnc")
        return
    if not FFMPEG_EXE:
        print("Error: FFmpeg not found in PATH.")
        print("Install with: sudo apt install ffmpeg")
        return

    # Load Settings
    settings = load_settings()
    print("--- Loaded Settings ---")
    print(f"Filter: {settings['filter_command']}")
    print("-----------------------")

    mkv_files = glob.glob("*.mkv")

    if not mkv_files:
        print("No .mkv files found in the current folder.")
        return

    for mkv in mkv_files:
        if "-deband" in mkv:
            continue

        base_name = os.path.splitext(mkv)[0]
        temp_h265 = f"{base_name}.h265"
        final_output = f"{base_name}-deband.mkv"

        print(f"==================================================")
        print(f"Processing: {mkv}")
        print(f"==================================================")

        # 1. Run NVEncC
        if not run_nvencc(mkv, temp_h265, settings):
            print(f"Skipping {mkv} due to NVEncC errors.")
            continue

        # 2. Mux with FFmpeg
        if run_ffmpeg_mux(temp_h265, mkv, final_output):
            print(f"Done! Created: {final_output}")

            try:
                if os.path.exists(temp_h265):
                    os.remove(temp_h265)
                print("Temporary files cleaned up.")
            except OSError as e:
                print(f"Warning: Could not clean up temp files: {e}")


if __name__ == "__main__":
    main()
