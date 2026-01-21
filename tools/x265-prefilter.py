#!/usr/bin/env python3
"""
x265 Prefilter Script - Linux Port
Combined script for applying filters (Denoise/Deband/Downscale) using VapourSynth and x265.
Matches Windows v1.48/v1.49 functionality.
"""

import os
import glob
import subprocess
import shutil
import configparser
import re

# --- Path Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# Config Path: Linux_Dist/prefilter/settings.txt
CONFIG_PATH = os.path.join(ROOT_DIR, "prefilter", "settings.txt")

# Tool Paths (use system binaries)
X265_EXE = shutil.which("x265")
FFMPEG_EXE = shutil.which("ffmpeg")
MEDIAINFO_EXE = shutil.which("mediainfo")


def load_settings():
    """Loads settings from settings.txt in the prefilter folder."""
    config = configparser.ConfigParser()
    defaults = {
        "downscale": False,
        "downscale_kernel": "hermite",
        "downscale_res": "1280x720",
        "denoise": True,
        "denoise_filter": "DFTTest().denoise(src, {0.00:0.30, 0.40:0.30, 0.60:0.60, 0.80:1.50, 1.00:2.00}, planes=[0, 1, 2])",
        "deband": True,
        "deband_filter": "core.placebo.Deband(src, threshold=2.0, planes=1)",
    }

    if os.path.exists(CONFIG_PATH):
        try:
            config.read(CONFIG_PATH)
            if "x265" in config:
                sec = config["x265"]
                defaults["downscale"] = sec.getboolean("x265-downscale", fallback=False)
                defaults["downscale_kernel"] = sec.get(
                    "x265-downscale-kernel", fallback="hermite"
                )
                defaults["downscale_res"] = sec.get(
                    "x265-downscale-resolution", fallback="1280x720"
                )
                defaults["denoise"] = sec.getboolean("x265-denoise", fallback=True)
                defaults["denoise_filter"] = sec.get(
                    "x265-denoise-filter", fallback=defaults["denoise_filter"]
                )
                defaults["deband"] = sec.getboolean("x265-deband", fallback=True)
                defaults["deband_filter"] = sec.get(
                    "x265-deband-filter", fallback=defaults["deband_filter"]
                )
            else:
                print(
                    f"[Warning] [x265] section missing in {CONFIG_PATH}. Using defaults."
                )
        except Exception as e:
            print(f"[Error] reading settings.txt: {e}")
    else:
        print(f"[Error] settings.txt not found at: {CONFIG_PATH}")

    return defaults


def detect_color_args(input_file):
    """Detects color space and returns appropriate x265 arguments."""
    if not MEDIAINFO_EXE:
        return []

    is_bt709 = False
    f_prim_709, f_trans_709, f_mat_709 = False, False, False
    f_prim_601, f_trans_601, f_mat_601 = False, False, False

    try:
        cmd = [MEDIAINFO_EXE, input_file]
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        for line in res.stdout.splitlines():
            if ":" not in line:
                continue
            k, v = [x.strip() for x in line.split(":", 1)]

            if k == "Color primaries":
                if "BT.709" in v:
                    f_prim_709 = True
                elif "BT.601" in v:
                    f_prim_601 = True
            elif k == "Transfer characteristics":
                if "BT.709" in v:
                    f_trans_709 = True
                elif "BT.601" in v:
                    f_trans_601 = True
            elif k == "Matrix coefficients":
                if "BT.709" in v:
                    f_mat_709 = True
                elif "BT.601" in v:
                    f_mat_601 = True

        if f_prim_709 and f_trans_709 and f_mat_709:
            is_bt709 = True
        # Note: BT.601 detection is tracked but not used for x265 as it doesn't need explicit conversion
        _ = f_prim_601 and f_trans_601 and f_mat_601  # Suppress unused warning
    except Exception:
        pass

    if is_bt709:
        return ["--colorprim", "bt709", "--transfer", "bt709", "--colormatrix", "bt709"]
    return []


def get_resolution(input_file):
    """Gets source resolution using mediainfo."""
    if not MEDIAINFO_EXE:
        return 0, 0
    try:
        cmd = [MEDIAINFO_EXE, "--Inform=Video;%Width%x%Height%", input_file]
        result = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        res_str = result.stdout.strip()
        if "x" in res_str:
            res_str = res_str.splitlines()[0]
            match = re.match(r"(\d+)x(\d+)", res_str)
            if match:
                return int(match.group(1)), int(match.group(2))
    except Exception:
        pass
    return 0, 0


def generate_vpy(input_mkv, output_vpy, settings):
    """Generates VapourSynth script for filtering."""
    escaped_input = os.path.abspath(input_mkv)

    script_content = f"""
import vapoursynth as vs
from vstools import initialize_clip, finalize_clip
from vsdenoise import DFTTest

core = vs.core
core.max_cache_size = 4096

# Source
src = core.ffms2.Source(r'{escaped_input}')
src = initialize_clip(src)
"""

    # 1. Denoise
    if settings["denoise"]:
        script_content += f"""
# Denoise
try:
    src = {settings["denoise_filter"]}
except Exception as e:
    print(f"Error in Denoise filter: {{e}}")
"""

    # 2. Deband
    if settings["deband"]:
        script_content += f"""
# Deband
try:
    src = {settings["deband_filter"]}
except Exception as e:
    print(f"Error in Deband filter: {{e}}")
"""

    # 3. Downscale
    if settings["downscale"]:
        w, h = map(int, settings["downscale_res"].split("x"))
        kernel = settings["downscale_kernel"].lower()

        filter_map = {
            "hermite": "hermite",
            "bilinear": "triangle",
            "bicubic": "catmull_rom",
            "spline36": "spline36",
            "lanczos": "lanczos",
            "mitchell": "mitchell",
        }
        pl_filter = filter_map.get(kernel, "hermite")

        script_content += f"""
# Downscale
src = core.placebo.Resample(src, {w}, {h}, filter="{pl_filter}")
"""

    script_content += """
final = finalize_clip(src)
final.set_output(0)
"""

    with open(output_vpy, "w", encoding="utf-8") as f:
        f.write(script_content)


def run_x265(vpy_file, output_hevc, color_args):
    """Runs x265 lossless encoding."""
    cmd = [
        X265_EXE,
        "--input",
        vpy_file,
        "--y4m",
        "--preset",
        "superfast",
        "--output-depth",
        "10",
        "--lossless",
        "--level-idc",
        "0",
    ]

    if color_args:
        cmd.extend(color_args)

    cmd.extend(["--output", output_hevc])

    # We need to pipe from vspipe to x265
    vspipe_cmd = ["vspipe", "-c", "y4m", vpy_file, "-"]

    print(f"\n[x265] Encoding: {vpy_file}")

    try:
        # Use vspipe to feed x265
        vspipe_proc = subprocess.Popen(vspipe_cmd, stdout=subprocess.PIPE)
        x265_cmd = [
            X265_EXE,
            "--input",
            "-",
            "--y4m",
            "--preset",
            "superfast",
            "--output-depth",
            "10",
            "--lossless",
            "--level-idc",
            "0",
        ]
        if color_args:
            x265_cmd.extend(color_args)
        x265_cmd.extend(["--output", output_hevc])

        x265_proc = subprocess.Popen(x265_cmd, stdin=vspipe_proc.stdout)
        vspipe_proc.stdout.close()
        x265_proc.communicate()

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

    settings = load_settings()

    print("--- Active Settings (x265) ---")
    print(f"Denoise:  {'ON' if settings['denoise'] else 'OFF'}")
    print(f"Deband:   {'ON' if settings['deband'] else 'OFF'}")
    print(
        f"Resize:   {'ON' if settings['downscale'] else 'OFF'} ({settings['downscale_res']})"
    )
    print("------------------------------")

    mkv_files = glob.glob("*.mkv")

    if not mkv_files:
        print("No MKV files found in this folder.")
        return

    for mkv in mkv_files:
        if "_prefilter" in mkv or "-no-video" in mkv:
            continue

        # Upscale Protection
        if settings["downscale"]:
            sw, sh = get_resolution(mkv)
            try:
                tw, th = map(int, settings["downscale_res"].split("x"))
                if sw > 0 and (tw > sw or th > sh):
                    print(
                        f"\n[!] SKIPPING {mkv}: Target {tw}x{th} > Source {sw}x{sh} (Upscaling not allowed)."
                    )
                    continue
            except Exception:
                pass

        base = os.path.splitext(mkv)[0]
        temp_vpy = f"{base}_temp.vpy"
        temp_hevc = f"{base}.hevc"
        final = f"{base}_prefilter_x265.mkv"

        color_args = detect_color_args(mkv)

        print(f"Processing: {mkv}")
        generate_vpy(mkv, temp_vpy, settings)

        if run_x265(temp_vpy, temp_hevc, color_args):
            if run_ffmpeg_mux(temp_hevc, mkv, final):
                print(f"Done: {final}")
                try:
                    os.remove(temp_vpy)
                    os.remove(temp_hevc)
                except Exception:
                    pass


if __name__ == "__main__":
    main()
