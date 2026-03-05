#!/usr/bin/env python3
"""
cropdetect.py

Unified Crop Detection Tool
- Default: Uses FFmpeg 'cropdetect' filter (Fast, Robust).
- Aggressive: Uses VapourSynth + NumPy (Pixel-perfect accuracy, slower, requires VS).

Merged from robust_autocrop.py and autocrop.py.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# --- VapourSynth / NumPy Imports (Lazy loaded or try/except to maintain portability) ---
try:
    import numpy as np
    import vapoursynth as vs

    VS_AVAILABLE = True
except ImportError:
    VS_AVAILABLE = False

# --- Constants & Regex ---
CROP_RE = re.compile(r"\bcrop=(\d+):(\d+):(\d+):(\d+)\b")
VIDEO_DEFAULT_EXTS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".m4v",
    ".webm",
    ".avi",
    ".mpg",
    ".mpeg",
    ".ts",
    ".m2ts",
    ".wmv",
}
TEMP_DIR_NAME = "cropdetect-temp"


@dataclass
class VideoInfo:
    path: Path
    width: int
    height: int
    duration: float  # seconds


@dataclass
class CropResult:
    crop: str  # "W:H:X:Y"
    w: int
    h: int
    x: int
    y: int
    confidence: float  # 0..1
    samples: int  # number of frames/segments observed
    chosen_from_limits: List[float]
    notes: str


# ============================================================================
#                               HELPER FUNCTIONS
# ============================================================================


def setup_temp_dir():
    """Deletes old temp dir if it exists, then creates a fresh one."""
    temp_path = Path(TEMP_DIR_NAME).resolve()
    if temp_path.exists():
        try:
            shutil.rmtree(temp_path)
        except Exception as e:
            print(
                f"Warning: Could not delete old temp dir {temp_path}: {e}",
                file=sys.stderr,
            )

    temp_path.mkdir(exist_ok=True)
    return temp_path


def run_cmd(cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )


def ffprobe_info(path: Path) -> Optional[VideoInfo]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height:format=duration",
        "-of",
        "json",
        str(path),
    ]
    p = run_cmd(cmd, timeout=60)
    if p.returncode != 0:
        return None

    try:
        data = json.loads(p.stdout)
        streams = data.get("streams", [])
        if not streams:
            return None
        w = int(streams[0].get("width", 0) or 0)
        h = int(streams[0].get("height", 0) or 0)
        dur = float(data.get("format", {}).get("duration", 0) or 0.0)
        if w <= 0 or h <= 0:
            return None
        return VideoInfo(path=path, width=w, height=h, duration=dur)
    except Exception:
        return None


def sample_timestamps(duration: float, n: int) -> List[float]:
    if duration and duration > 10:
        start = max(0.5, duration * 0.05)
        end = max(start + 1.0, duration * 0.95)
        if end <= start:
            return [start]
        return [start + (end - start) * (i / (n - 1)) for i in range(n)]
    return [0.5, 3.0, 8.0, 15.0][: max(1, min(n, 4))]


def area(w: int, h: int) -> int:
    return w * h


def load_settings() -> dict:
    script_dir = Path(__file__).parent.resolve()
    possible_paths = [script_dir / "settings.txt", script_dir.parent / "settings.txt"]
    settings = {}

    for p in possible_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            settings[key.strip().lower()] = val.strip()
                break  # Stop after finding first valid settings file
            except Exception:
                pass
    return settings


# ============================================================================
#                      MODE 1: DEFAULT (FFMPEG CROPDETECT)
# ============================================================================


def run_cropdetect_segment(
    video: Path, ss: float, seg: float, fps: float, limit: float, round_to: int
) -> List[Tuple[int, int, int, int]]:
    vf = f"fps={fps},format=yuv444p,cropdetect=limit={limit}:round={round_to}:reset=0"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-ss",
        f"{ss:.3f}",
        "-i",
        str(video),
        "-t",
        f"{seg:.3f}",
        "-vf",
        vf,
        "-an",
        "-sn",
        "-dn",
        "-f",
        "null",
        "-",
    ]
    p = run_cmd(cmd, timeout=max(60, int(seg * 10) + 30))
    text = (p.stderr or "") + "\n" + (p.stdout or "")
    crops = []
    for m in CROP_RE.finditer(text):
        crops.append(tuple(map(int, m.groups())))
    return crops


def choose_best_crop(
    vi: VideoInfo, observed: Counter, crop_to_limits: Dict[str, set]
) -> Optional[CropResult]:
    if not observed:
        return None
    full_area = area(vi.width, vi.height)
    best = None
    best_score = -1e18
    total = sum(observed.values())

    for crop_str, count in observed.items():
        w, h, x, y = map(int, crop_str.split(":"))
        a = area(w, h)
        if a <= 0 or a > full_area:
            continue

        freq = count / max(1, total)
        ar = a / full_area
        lim_support = len(crop_to_limits.get(crop_str, set()))
        score = (freq * 1000.0) + (ar * 50.0) + (lim_support * 15.0)

        # Penalize full frame slightly to prefer actual crops if they are prevalent
        if w == vi.width and h == vi.height and x == 0 and y == 0:
            score -= 5.0

        if score > best_score:
            best_score = score
            best = (crop_str, w, h, x, y, freq, total, lim_support)

    if best is None:
        return None

    crop_str, w, h, x, y, freq, total, lim_support = best
    limits = sorted(crop_to_limits.get(crop_str, set()))
    notes = (
        "strong"
        if lim_support >= 3
        else "moderate"
        if lim_support == 2
        else "single-threshold"
    )
    return CropResult(
        crop_str,
        w,
        h,
        x,
        y,
        freq,
        total,
        [float(v) for v in limits],
        f"{notes} agreement",
    )


def detect_ffmpeg(
    vi: VideoInfo,
    sample_count: int,
    segment_len: float,
    fps: float,
    limits: List[float],
    round_to: int,
    progress_mode: bool,
) -> Optional[CropResult]:
    timestamps = sample_timestamps(vi.duration, sample_count)
    observed: Counter = Counter()
    crop_to_limits: Dict[str, set] = defaultdict(set)
    total_steps = len(limits) * len(timestamps)
    current_step = 0

    for lim in limits:
        for ts in timestamps:
            crops = run_cropdetect_segment(vi.path, ts, segment_len, fps, lim, round_to)
            for w, h, x, y in crops:
                c = f"{w}:{h}:{x}:{y}"
                observed[c] += 1
                crop_to_limits[c].add(lim)

            if progress_mode:
                current_step += 1
                print(f"PROGRESS:{int((current_step / total_steps) * 100)}", flush=True)

    return choose_best_crop(vi, observed, crop_to_limits)


# ============================================================================
#                 MODE 2: AGGRESSIVE (VAPOURSYNTH + NUMPY)
# ============================================================================


def get_hsl_luminance(frame_rgb):
    """Replicates VB.NET ColorHSL.L: (Max + Min) / 2."""
    r, g, b = frame_rgb[:, :, 0], frame_rgb[:, :, 1], frame_rgb[:, :, 2]
    c_max = np.maximum(np.maximum(r, g), b)
    c_min = np.minimum(np.minimum(r, g), b)
    return (c_max + c_min) / 2.0


def vs_scan_frame(frame, threshold):
    width = frame.width
    height = frame.height

    # Use legacy frame access for compatibility with all VS versions
    planes = [np.asarray(frame[i]) for i in range(frame.format.num_planes)]
    img_data = np.dstack(planes)

    # img_data is float32 0.0-1.0 because we force RGBS in the generator
    lum_map = get_hsl_luminance(img_data)
    is_content = lum_map >= threshold

    rows = np.any(is_content, axis=1)
    if not np.any(rows):
        return height // 2, height // 2, width // 2, width // 2

    top = np.argmax(rows)
    bottom = np.argmax(rows[::-1])

    cols = np.any(is_content, axis=0)
    left = np.argmax(cols)
    right = np.argmax(cols[::-1])

    return left, top, right, bottom


def detect_vapoursynth(
    vi: VideoInfo, mode: int, value: int, lum_thresh_int: int, progress_mode: bool
) -> Optional[CropResult]:
    if not VS_AVAILABLE:
        print("Error: --aggressive mode requires VapourSynth module.", file=sys.stderr)
        return None

    temp_dir = Path(TEMP_DIR_NAME).resolve()

    # 1. Generate a temporary VapourSynth Script
    # We use FFMS2 to index the file into the temp directory
    index_file = temp_dir / (vi.path.name + ".ffindex")
    vpy_file = temp_dir / "temp_analysis.vpy"

    # FIX: Clean and Sanitize Paths
    # Remove Windows Long Path prefix (\\?\) if present, as it confuses some VS plugins
    raw_vid_path = str(vi.path)
    if raw_vid_path.startswith("\\\\?\\"):
        raw_vid_path = raw_vid_path[4:]
    # Use Forward Slashes to safely pass through Python string formatting without escaping hell
    vid_path_str = raw_vid_path.replace("\\", "/")

    raw_idx_path = str(index_file)
    if raw_idx_path.startswith("\\\\?\\"):
        raw_idx_path = raw_idx_path[4:]
    idx_path_str = raw_idx_path.replace("\\", "/")

    # Script content: Load -> Resize to Planar RGB Float (RGBS) -> Output
    script_content = f"""
import vapoursynth as vs
core = vs.core
# Try loading via ffms2 (standard for staxrip/portables)
try:
    clip = core.ffms2.Source(source=r"{vid_path_str}", cachefile=r"{idx_path_str}")
except AttributeError:
    # Fallback to lsmas if ffms2 missing
    try:
        clip = core.lsmas.LWLibavSource(source=r"{vid_path_str}", cache=0)
    except AttributeError:
        # Final fallback: explicit load (unlikely needed in portable, but safe)
        raise RuntimeError("Neither ffms2 nor lsmas plugins found.")

# Resize to Planar RGB Float for NumPy analysis
# This ensures 0.0-1.0 range and 3 separate planes
clip = clip.resize.Bicubic(format=vs.RGBS, matrix_in_s="709")
clip.set_output()
"""
    try:
        with open(vpy_file, "w", encoding="utf-8") as f:
            f.write(script_content)
    except Exception as e:
        print(f"Error creating temp VPY: {e}", file=sys.stderr)
        return None

    # 2. Execute VapourSynth Environment
    # We must run this within the current python process to use the 'autocrop' logic
    try:
        from runpy import run_path

        # Run the generated script
        run_path(str(vpy_file))

        # Get Output (Safe Fallback Logic)
        try:
            clip = vs.get_output(0)
        except (AttributeError, KeyError, ValueError):
            # Fallback for different VS API versions
            outputs = vs.get_outputs()
            if not outputs:
                raise RuntimeError("No output clip found.")
            clip = outputs[0]

        if isinstance(clip, tuple) or hasattr(clip, "clip"):
            clip = clip.clip

        # 3. Determine Frames to Analyze (Logic from autocrop.py)
        frame_count = clip.num_frames
        fps = clip.fps_num / clip.fps_den

        # Defaults from autocrop.py inputs
        start_t = 1000
        end_t = 1000

        start_frame = min(start_t, frame_count // 4)
        end_frame = max(frame_count - 1 - end_t, frame_count * 3 // 4)

        considered = end_frame - start_frame
        interval = 1

        if mode == 1:
            interval = considered // value
        elif mode == 2:
            interval = value
        elif mode == 3:
            interval = int(value * fps)

        interval = max(1, interval)
        if considered > 0:
            interval = min(interval, considered // 5)

        analyze_frames = []
        curr = start_frame + ((considered - ((considered // interval) * interval)) // 2)
        while curr < end_frame:
            analyze_frames.append(curr)
            curr += interval

        # 4. Analyze Loop
        lum_thresh_float = lum_thresh_int / 10000.0

        min_left = clip.width
        min_top = clip.height
        min_right = clip.width
        min_bottom = clip.height

        total_frames = len(analyze_frames)

        for i, fnum in enumerate(analyze_frames):
            if progress_mode:
                # Flush ensures the parent process sees the update immediately
                print(f"PROGRESS:{int((i / total_frames) * 100)}", flush=True)
            elif i % 5 == 0:
                sys.stdout.write(f"\\rVS Analysis: {int((i / total_frames) * 100)}%   ")
                sys.stdout.flush()

            frame = clip.get_frame(fnum)
            l, t, r, b = vs_scan_frame(frame, lum_thresh_float)

            min_left = min(min_left, l)
            min_top = min(min_top, t)
            min_right = min(min_right, r)
            min_bottom = min(min_bottom, b)

            # Optimization: Stop if full frame found
            if min_left == 0 and min_top == 0 and min_right == 0 and min_bottom == 0:
                break

        if progress_mode:
            print("PROGRESS:100", flush=True)
        else:
            sys.stdout.write("\\rVS Analysis: Done.      \\n")

        # 5. Format Result
        final_w = clip.width - min_left - min_right
        final_h = clip.height - min_top - min_bottom
        crop_str = f"{final_w}:{final_h}:{min_left}:{min_top}"

        return CropResult(
            crop=crop_str,
            w=final_w,
            h=final_h,
            x=min_left,
            y=min_top,
            confidence=1.0,
            samples=len(analyze_frames),
            chosen_from_limits=[],
            notes="VapourSynth Aggressive Scan",
        )

    except Exception as e:
        # Print actual exception to stderr so it can be debugged if needed
        print(f"VapourSynth Error: {e}", file=sys.stderr)
        return None


# ============================================================================
#                                   MAIN
# ============================================================================


def find_videos(paths: List[str], recursive: bool, exts: set) -> List[Path]:
    vids: List[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            if recursive:
                for f in pp.rglob("*"):
                    if f.is_file() and f.suffix.lower() in exts:
                        vids.append(f)
            else:
                for f in pp.iterdir():
                    if f.is_file() and f.suffix.lower() in exts:
                        vids.append(f)
        else:
            if pp.is_file():
                vids.append(pp)
    seen = set()
    out = []
    for v in vids:
        r = v.resolve()
        if r not in seen:
            seen.add(r)
            out.append(v)
    return out


def main() -> int:
    # 1. Setup Temp Folder
    setup_temp_dir()

    # 2. Parse Args
    ap = argparse.ArgumentParser(
        description="Robust Crop Detect (FFmpeg & VapourSynth)"
    )
    ap.add_argument("inputs", nargs="+", help="Video files/dirs")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument(
        "--extensions",
        default=",".join(sorted(e.lstrip(".") for e in VIDEO_DEFAULT_EXTS)),
    )
    ap.add_argument("--samples", type=int, default=15, help="FFmpeg mode samples")
    ap.add_argument(
        "--segment", type=float, default=2.5, help="FFmpeg mode segment seconds"
    )
    ap.add_argument("--fps", type=float, default=3.0)
    ap.add_argument("--round", dest="round_to", type=int, default=2)
    ap.add_argument(
        "--aggressive",
        action="store_true",
        help="Use VapourSynth+NumPy (Slower, precise)",
    )
    ap.add_argument("--out", default="crops.csv")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--progress-mode", action="store_true", help=argparse.SUPPRESS)

    args = ap.parse_args()
    settings = load_settings()
    crop_mode = settings.get("crop", "auto").lower()

    # Manual Crop overrides
    manual_crop = {"top": 0, "bottom": 0, "left": 0, "right": 0}
    if crop_mode == "manual":
        for k in manual_crop:
            try:
                manual_crop[k] = int(settings.get(k, 0))
            except:
                pass

    exts = {
        ("." + e.strip().lower().lstrip("."))
        for e in args.extensions.split(",")
        if e.strip()
    }
    videos = find_videos(args.inputs, args.recursive, exts)

    if not videos:
        print("No videos found.", file=sys.stderr)
        return 2

    results_rows = []
    json_results = []

    for idx, vp in enumerate(videos, 1):
        vi = ffprobe_info(vp)
        if not vi:
            continue

        if not args.progress_mode:
            print(f"[{idx}/{len(videos)}] {vp.name} ({vi.width}x{vi.height})")

        res = None

        if crop_mode == "manual":
            mw = vi.width - manual_crop["left"] - manual_crop["right"]
            mh = vi.height - manual_crop["top"] - manual_crop["bottom"]
            if mw <= 0 or mh <= 0:
                mw, mh = vi.width, vi.height
            res = CropResult(
                f"{mw}:{mh}:{manual_crop['left']}:{manual_crop['top']}",
                mw,
                mh,
                manual_crop["left"],
                manual_crop["top"],
                1.0,
                1,
                [],
                "Manual",
            )
            if args.progress_mode:
                print("PROGRESS:100", flush=True)

        elif args.aggressive:
            # --- VapourSynth Mode ---
            res = detect_vapoursynth(
                vi,
                mode=3,
                value=15,
                lum_thresh_int=1000,
                progress_mode=args.progress_mode,
            )

        else:
            # --- FFmpeg Mode ---
            limits = [0.06, 0.08, 0.12, 0.18, 0.25, 0.35]
            res = detect_ffmpeg(
                vi,
                args.samples,
                args.segment,
                args.fps,
                limits,
                args.round_to,
                args.progress_mode,
            )

        # Fallback
        if not res:
            res = CropResult(
                f"{vi.width}:{vi.height}:0:0",
                vi.width,
                vi.height,
                0,
                0,
                0.0,
                0,
                [],
                "Failed/Full",
            )

        row = {
            "file": str(vp),
            "width": vi.width,
            "height": vi.height,
            "duration_sec": round(vi.duration, 3),
            "crop": res.crop,
            "crop_w": res.w,
            "crop_h": res.h,
            "crop_x": res.x,
            "crop_y": res.y,
            "confidence": round(res.confidence, 4),
            "samples_seen": res.samples,
            "limits_agreed": ",".join(f"{x:.2f}" for x in res.chosen_from_limits),
            "notes": res.notes,
            "ffmpeg_apply": f'-vf "crop={res.crop}"',
        }
        results_rows.append(row)
        json_results.append(row)

        if not args.progress_mode:
            print(f"  -> {res.crop} ({res.notes})")

    # Output Writing
    out_csv = Path(args.out)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    keys = [
        "file",
        "width",
        "height",
        "duration_sec",
        "crop",
        "crop_w",
        "crop_h",
        "crop_x",
        "crop_y",
        "confidence",
        "samples_seen",
        "limits_agreed",
        "notes",
        "ffmpeg_apply",
    ]

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in results_rows:
            w.writerow(r)

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(json_results, indent=2), encoding="utf-8"
        )

    if not args.progress_mode:
        print(f"Done. Saved to {out_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
