#!/usr/bin/env python3
"""
Deband using VapourSynth + x265 Lossless
Linux Port: Uses system FFmpeg and x265
"""

import os
import glob
import subprocess
import sys
import shutil
import configparser

# --- Configuration & Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# Config Path
CONFIG_PATH = os.path.join(ROOT_DIR, "prefilter", "settings.txt")

# Tool Paths (use system binaries)
X265_EXE = shutil.which("x265")
FFMPEG_EXE = shutil.which("ffmpeg")
MEDIAINFO_EXE = shutil.which("mediainfo")


def load_settings():
    """Loads settings from settings.txt with fallback defaults."""
    config = configparser.ConfigParser()

    defaults = {
        "vapoursynth_deband": "core.placebo.Deband(src, threshold=2.0, planes=1)"
    }

    if os.path.exists(CONFIG_PATH):
        try:
            config.read(CONFIG_PATH)
            if "x265_DEBAND" in config:
                if "vapoursynth_deband" in config["x265_DEBAND"]:
                    defaults["vapoursynth_deband"] = config["x265_DEBAND"][
                        "vapoursynth_deband"
                    ]
            else:
                print(
                    f"[Warning] [x265_DEBAND] section not found in {CONFIG_PATH}. Using default."
                )
        except Exception as e:
            print(f"[Warning] Could not read settings.txt: {e}. Using default.")
    else:
        print(f"[Warning] Settings file not found at {CONFIG_PATH}. Using default.")

    return defaults


def check_bt709(input_file):
    """Check if file is BT.709 colorspace."""
    if not MEDIAINFO_EXE:
        return False

    found_primaries = False
    found_transfer = False
    found_matrix = False

    try:
        cmd = [MEDIAINFO_EXE, input_file]
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key, value = key.strip(), value.strip()
                if key == "Color primaries" and value == "BT.709":
                    found_primaries = True
                elif key == "Transfer characteristics" and value == "BT.709":
                    found_transfer = True
                elif key == "Matrix coefficients" and value == "BT.709":
                    found_matrix = True
            if found_primaries and found_transfer and found_matrix:
                return True
    except Exception as e:
        print(f"[Warning] MediaInfo execution failed: {e}")
    return False


def generate_vpy(input_mkv, output_vpy, deband_cmd):
    """Generates the temporary .vpy script."""
    escaped_input = os.path.abspath(input_mkv).replace("\\", "\\\\")

    script_content = f"""
import vapoursynth as vs
from vstools import initialize_clip, finalize_clip

core = vs.core
core.max_cache_size = 1024

# Using FFMS2 Source for Linux
src = core.ffms2.Source(r'{escaped_input}')
src = initialize_clip(src)

# Injected Deband Command from settings.txt
deband = {deband_cmd}

final = finalize_clip(deband)
final.set_output(0)
"""
    with open(output_vpy, "w", encoding="utf-8") as f:
        f.write(script_content)


def run_x265(vpy_file, output_hevc, is_bt709):
    """Runs x265 encoding via VapourSynth pipe."""

    # Get frame info from vspipe
    vspipe_cmd = ["vspipe", "-y", vpy_file, "-"]
    x265_cmd = [
        X265_EXE,
        "--preset",
        "superfast",
        "--output-depth",
        "10",
        "--lossless",
        "--level-idc",
        "0",
        "-o",
        output_hevc,
        "-",
        "--y4m",
    ]

    if is_bt709:
        print("[x265] Applying BT.709 Color Flags.")
        x265_cmd.extend(
            ["--colorprim", "bt709", "--colormatrix", "bt709", "--transfer", "bt709"]
        )

    print(f"\n[x265] Encoding: {vpy_file} -> {output_hevc}")

    try:
        vspipe_proc = subprocess.Popen(
            vspipe_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        x265_proc = subprocess.Popen(x265_cmd, stdin=vspipe_proc.stdout)
        vspipe_proc.stdout.close()
        x265_proc.wait()
        return x265_proc.returncode == 0
    except Exception as e:
        print(f"[x265] Error: {e}")
        return False


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
    if not X265_EXE:
        print("Error: x265 not found in PATH.")
        print("Install with: sudo apt install x265")
        return
    if not FFMPEG_EXE:
        print("Error: FFmpeg not found in PATH.")
        print("Install with: sudo apt install ffmpeg")
        return

    # Check vspipe
    if not shutil.which("vspipe"):
        print("Error: vspipe not found in PATH.")
        print("Ensure VapourSynth is installed correctly.")
        return

    # Load Settings
    settings = load_settings()
    print("--- Loaded Settings ---")
    print(f"Filter: {settings['vapoursynth_deband']}")
    print("-----------------------")

    mkv_files = glob.glob("*.mkv")
    if not mkv_files:
        print("No .mkv files found in the current folder.")
        return

    for mkv in mkv_files:
        if "-deband" in mkv:
            continue

        base_name = os.path.splitext(mkv)[0]
        temp_vpy = f"{base_name}_temp.vpy"
        temp_hevc = f"{base_name}.hevc"
        final_output = f"{base_name}-deband.mkv"

        print(f"==================================================")
        print(f"Processing: {mkv}")
        print(f"==================================================")

        # 1. Detect BT.709
        is_bt709 = check_bt709(mkv)

        # 2. Generate VPY
        print("[Script] Generating VapourSynth script...")
        generate_vpy(mkv, temp_vpy, settings["vapoursynth_deband"])

        # 3. Run x265
        if not run_x265(temp_vpy, temp_hevc, is_bt709):
            print(f"Error encoding {mkv}. Skipping.")
            if os.path.exists(temp_vpy):
                os.remove(temp_vpy)
            continue

        # 4. Mux Final
        if run_ffmpeg_mux(temp_hevc, mkv, final_output):
            print(f"Done! Created: {final_output}")

            try:
                for f in [temp_vpy, temp_hevc]:
                    if os.path.exists(f):
                        os.remove(f)
                print("Temporary files cleaned up.")
            except OSError as e:
                print(f"Warning: Cleanup failed: {e}")


if __name__ == "__main__":
    main()
