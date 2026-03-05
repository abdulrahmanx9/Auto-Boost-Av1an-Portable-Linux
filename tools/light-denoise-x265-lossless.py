#!/usr/bin/env python3
import os
import glob
import subprocess
import sys
import shutil
import threading
from pathlib import Path

# --- Configuration & Paths ---
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent


# Helper to find system binaries
def get_binary(name):
    path = shutil.which(name)
    if not path:
        # Fallback to local tools if structured that way
        local = SCRIPT_DIR / "av1an" / name
        if local.exists():
            return str(local)
    return path or name


X265_EXE = get_binary("x265")
MKVMERGE_EXE = get_binary("mkvmerge")
MEDIAINFO_EXE = get_binary("mediainfo")
VSPIPE_EXE = get_binary("vspipe")


def check_bt709(input_file):
    """
    Checks if the input file matches strict BT.709 standards using MediaInfo.
    """
    if not shutil.which("mediainfo"):
        return False

    found_primaries = False
    found_transfer = False
    found_matrix = False

    try:
        cmd = [MEDIAINFO_EXE, str(input_file)]
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )

        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if ":" not in line:
                    continue

                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

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


def generate_vpy(input_mkv, output_vpy):
    """
    Generates the temporary .vpy script using FFMS2 for input.
    """
    # Escaping for Python string
    escaped_input = os.path.abspath(input_mkv).replace("\\", "\\\\")

    script_content = f"""
import vapoursynth as vs
from vstools import initialize_clip, finalize_clip
from vsdenoise import DFTTest

core = vs.core
core.max_cache_size = 4096

# Using FFMS2 Source (Linux Native)
src = core.ffms2.Source(r'{escaped_input}')
src = initialize_clip(src)

denoise = DFTTest().denoise(src, {{0.00:0.30, 0.40:0.30, 0.60:0.60, 0.80:1.50, 1.00:2.00}}, planes=[0, 1, 2])

final = finalize_clip(denoise)
final.set_output(0)
"""
    with open(output_vpy, "w", encoding="utf-8") as f:
        f.write(script_content)


def run_x265_pipe(vpy_file, output_hevc, is_bt709):
    """
    Runs x265 via vspipe (Linux compatible).
    """

    # x265 Command
    x265_cmd = [
        X265_EXE,
        "--y4m",
        "--preset",
        "superfast",
        "--output-depth",
        "10",
        "--lossless",
        "--level-idc",
        "0",
        "--output",
        str(output_hevc),
        "-",  # Read from stdin
    ]

    if is_bt709:
        print("[x265] Applying BT.709 Color Flags.")
        x265_cmd.extend(
            ["--colorprim", "bt709", "--colormatrix", "bt709", "--transfer", "bt709"]
        )

    print(f"\n[x265] Encoding: {vpy_file} -> {output_hevc}")

    # VSPipe Command
    vspipe_cmd = [VSPIPE_EXE, "-y", str(vpy_file), "-"]

    try:
        # Pipe: vspipe -> x265
        p1 = subprocess.Popen(
            vspipe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        p2 = subprocess.Popen(x265_cmd, stdin=p1.stdout)

        # Allow p1 to receive a SIGPIPE if p2 exits.
        p1.stdout.close()

        p2.communicate()

        # Check return codes
        if p2.returncode == 0:
            return True
        else:
            print(f"Error: x265 failed with code {p2.returncode}")
            return False

    except Exception as e:
        print(f"Error running pipeline: {e}")
        return False


def run_mkvmerge_progress(cmd, task_name):
    """Runs mkvmerge, hiding output but showing the progress line in realtime."""
    print(f"[{task_name}] Starting...")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
    )

    while True:
        line = process.stdout.readline()
        if not line:
            break
        line = line.strip()
        if line.startswith("Progress:"):
            sys.stdout.write(f"\r[{task_name}] {line}")
            sys.stdout.flush()

    process.wait()
    sys.stdout.write("\n")
    return process.returncode == 0


def main():
    # Tools check
    if not shutil.which(X265_EXE):
        print(
            f"Error: x265 not found (checked '{X265_EXE}'). Install with 'apt install x265' or 'apt install x265-files'."
        )
        return
    if not shutil.which(VSPIPE_EXE):
        print(f"Error: vspipe not found. Is VapourSynth installed correctly?")
        return

    mkv_files = glob.glob("*.mkv")
    if not mkv_files:
        print("No .mkv files found in the current folder.")
        return

    # Check for Input folder if no mkvs in root
    # (Optional enhancement, but sticking to original script logic first)

    for mkv in mkv_files:
        if "-lightdenoise" in mkv or "-no-video" in mkv:
            continue

        base_name = os.path.splitext(mkv)[0]
        temp_vpy = f"{base_name}_temp.vpy"
        temp_hevc = f"{base_name}.hevc"
        temp_no_video = f"{base_name}-no-video.mkv"
        final_output = f"{base_name}-lightdenoise.mkv"

        print(f"==================================================")
        print(f"Processing: {mkv}")
        print(f"==================================================")

        # 1. Detect BT.709
        is_bt709 = check_bt709(mkv)

        # 2. Generate VPY
        print("[Script] Generating VapourSynth script...")
        generate_vpy(mkv, temp_vpy)

        # 3. Run x265 via Pipe
        if not run_x265_pipe(temp_vpy, temp_hevc, is_bt709):
            print(f"Error encoding {mkv}. Skipping.")
            if os.path.exists(temp_vpy):
                os.remove(temp_vpy)
            continue

        # 4. Extract Audio/Subs (No Video)
        cmd_extract = [MKVMERGE_EXE, "-o", temp_no_video, "--no-video", mkv]
        if not run_mkvmerge_progress(cmd_extract, "Extracting Audio/Subs"):
            continue

        # 5. Mux Final
        cmd_mux = [MKVMERGE_EXE, "-o", final_output, temp_hevc, temp_no_video]
        if run_mkvmerge_progress(cmd_mux, "Muxing Final File"):
            print(f"Done! Created: {final_output}")

            # Cleanup
            try:
                for f in [temp_vpy, temp_hevc, temp_no_video]:
                    if os.path.exists(f):
                        os.remove(f)
                print("Temporary files cleaned up.")
            except OSError as e:
                print(f"Warning: Cleanup failed: {e}")


if __name__ == "__main__":
    main()
