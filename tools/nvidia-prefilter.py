#!/usr/bin/env python3
"""
NVIDIA Prefilter Script - Linux Port
Combined script for applying filters (Denoise/Deband/Downscale) using NVEncC.
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
NVENCC_EXE = shutil.which("nvencc") or shutil.which("NVEncC")
FFMPEG_EXE = shutil.which("ffmpeg")
MEDIAINFO_EXE = shutil.which("mediainfo")


def load_settings():
    """Loads settings from settings.txt in the prefilter folder."""
    config = configparser.ConfigParser()
    defaults = {
        "downscale": False,
        "downscale_algo": "hermite",
        "downscale_res": "1920x1080",
        "denoise": True,
        "denoise_filter": "vpp_fft3d=sigma=0.2",
        "deband": True,
        "deband_thr": "1",
        "deband_rad": "16",
    }

    if os.path.exists(CONFIG_PATH):
        try:
            config.read(CONFIG_PATH)
            if "NVIDIA" in config:
                sec = config["NVIDIA"]
                defaults["downscale"] = sec.getboolean(
                    "nvidia-downscale", fallback=False
                )
                defaults["downscale_algo"] = sec.get(
                    "nvidia-downscale-filter", fallback="hermite"
                )
                defaults["downscale_res"] = sec.get(
                    "nvidia-downscale-resolution", fallback="1920x1080"
                )
                defaults["denoise"] = sec.getboolean("nvidia-denoise", fallback=True)
                defaults["denoise_filter"] = sec.get(
                    "nvidia-denoise-filter", fallback="vpp_fft3d=sigma=0.2"
                )
                defaults["deband"] = sec.getboolean("nvidia-deband", fallback=True)
                defaults["deband_thr"] = sec.get(
                    "nvidia-deband-threshold", fallback="1"
                )
                defaults["deband_rad"] = sec.get("nvidia-deband-radius", fallback="16")
            else:
                print(
                    f"[Warning] [NVIDIA] section missing in {CONFIG_PATH}. Using defaults."
                )
        except Exception as e:
            print(f"[Error] reading settings.txt: {e}")
    else:
        print(f"[Error] settings.txt not found at: {CONFIG_PATH}")

    return defaults


def detect_color_args(input_file):
    """Detects color space and returns appropriate NVEncC arguments."""
    if not MEDIAINFO_EXE:
        return []

    is_bt709, is_bt601 = False, False
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
        elif f_prim_601 and f_trans_601 and f_mat_601:
            is_bt601 = True
    except Exception:
        pass

    if is_bt709:
        return ["--colormatrix", "bt709", "--colorprim", "bt709", "--transfer", "bt709"]
    elif is_bt601:
        return ["--vpp-colorspace", "matrix=smpte170m:bt709"]
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


def run_nvencc(input_file, output_file, settings, color_args):
    """Runs NVEncC with the specified filters."""
    cmd = [
        NVENCC_EXE,
        "--codec",
        "hevc",
        "--preset",
        "p4",
        "--output-depth",
        "10",
        "--lossless",
    ]

    if color_args:
        cmd.extend(color_args)

    # 1. Denoise
    if settings["denoise"]:
        filter_str = settings["denoise_filter"]
        if "vpp_fft3d=" in filter_str:
            filter_str = filter_str.replace("vpp_fft3d=", "")
        cmd.extend(["--vpp-fft3d", filter_str])

    # 2. Deband
    if settings["deband"]:
        val = f"threshold={settings['deband_thr']},radius={settings['deband_rad']}"
        cmd.extend(["--vpp-libplacebo-deband", val])

    # 3. Downscale
    if settings["downscale"]:
        algo = settings["downscale_algo"]
        res = settings["downscale_res"]
        cmd.extend(["--vpp-resize", f"algo={algo}", "--output-res", res])

    cmd.extend(["-i", input_file, "-o", output_file])

    # Try HW Decode first
    cmd_hw = cmd[:1] + ["--avhw"] + cmd[1:]
    print(f"\n[NVEncC] Processing: {input_file}")

    ret = subprocess.run(cmd_hw).returncode
    if ret != 0:
        print("\n[NVEncC] HW Decode failed. Retrying SW Decode...")
        ret = subprocess.run(cmd).returncode

    return ret == 0


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
        print("Install from: https://github.com/rigaya/NVEnc")
        return
    if not FFMPEG_EXE:
        print("Error: FFmpeg not found in PATH.")
        print("Install with: sudo apt install ffmpeg")
        return

    settings = load_settings()

    print("--- Active Settings ---")
    print(
        f"Denoise:  {'ON' if settings['denoise'] else 'OFF'} ({settings['denoise_filter']})"
    )
    print(
        f"Deband:   {'ON' if settings['deband'] else 'OFF'} (Thr:{settings['deband_thr']}, Rad:{settings['deband_rad']})"
    )
    print(
        f"Resize:   {'ON' if settings['downscale'] else 'OFF'} ({settings['downscale_res']})"
    )
    print("-----------------------")

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
        temp_vid = f"{base}.h265"
        final = f"{base}_prefilter.mkv"

        color_args = detect_color_args(mkv)

        if run_nvencc(mkv, temp_vid, settings, color_args):
            if run_ffmpeg_mux(temp_vid, mkv, final):
                print(f"Done: {final}")
                try:
                    os.remove(temp_vid)
                except Exception:
                    pass


if __name__ == "__main__":
    main()
