#!/usr/bin/env python3
"""
Mux Script - Linux Port
Muxes AV1 encoded video with audio/subs from source.
Includes VFR (Variable Frame Rate) support.
"""

import os
import subprocess
import glob
import sys
import json
import shutil

# Tool paths (use system binaries)
MKVMERGE = shutil.which("mkvmerge") or "mkvmerge"
MKVEXTRACT = shutil.which("mkvextract") or "mkvextract"
MKVPROPEDIT = shutil.which("mkvpropedit") or "mkvpropedit"
MEDIAINFO = shutil.which("mediainfo") or "mediainfo"


def run_command(cmd, status_label):
    """
    Runs a command hidden, parsing output to update a single progress line.
    """
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    print(f"{status_label}: Starting...          ", end="\r")
    sys.stdout.flush()

    for line in process.stdout:
        line = line.strip()
        if line.startswith("Progress:"):
            percent = line.split(":")[-1].strip()
            print(f"{status_label}: {percent}          ", end="\r")
            sys.stdout.flush()

    process.wait()

    if process.returncode != 0:
        print(f"\n[ERROR] Command failed: {' '.join(cmd)}")
        raise subprocess.CalledProcessError(process.returncode, cmd)

    print(f"{status_label}: Done.          ")


def force_vfr_metadata(file_path, status_label):
    """
    Uses mkvpropedit to remove the 'DefaultDuration' element from video tracks.
    Removing DefaultDuration prevents tools like MediaInfo from treating the
    stream as CFR purely from metadata.
    """
    if not shutil.which("mkvpropedit"):
        print("[WARN] mkvpropedit not found. Skipping metadata edit.")
        return

    video_track_count = get_video_track_count(file_path) or 1

    cmd = [MKVPROPEDIT, "--parse-mode", "full", file_path]
    for i in range(1, video_track_count + 1):
        cmd.extend(["--edit", f"track:v{i}", "--delete", "default-duration"])

    print(f"{status_label}: Updating...          ", end="\r")
    sys.stdout.flush()

    try:
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        print(f"{status_label}: Done.          ")
    except subprocess.CalledProcessError as e:
        print(f"[WARN] Failed to edit properties: {e}")


def get_video_track_id(source_file):
    """
    Uses mkvmerge to find the ID of the video track for extraction.
    Returns: track_id (int) or None if not found.
    """
    cmd = [MKVMERGE, "-J", source_file]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", check=True
        )
        data = json.loads(result.stdout)

        for track in data.get("tracks", []):
            if track.get("type") == "video":
                return track.get("id")
    except Exception as e:
        print(f"[WARN] Failed to get track ID: {e}")

    return None


def get_video_track_count(source_file):
    """
    Uses mkvmerge JSON output to count the number of video tracks in a file.
    """
    cmd = [MKVMERGE, "-J", source_file]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", check=True
        )
        data = json.loads(result.stdout)
        count = 0
        for track in data.get("tracks", []):
            if track.get("type") == "video":
                count += 1
        return count
    except Exception:
        return 1


def check_vfr_mediainfo(source_file):
    """
    Uses MediaInfo to check if the video has a Variable frame rate mode.
    """
    if not shutil.which("mediainfo"):
        return False

    cmd = [MEDIAINFO, source_file]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", check=True
        )

        # Parse output for "Frame rate mode : Variable"
        for line in result.stdout.splitlines():
            if "frame rate mode" in line.lower() and "variable" in line.lower():
                return True

    except Exception as e:
        print(f"[WARN] MediaInfo check failed: {e}")

    return False


def mux_files():
    # Determine input/output directories
    output_dir = "Output"
    input_dir = "Input"

    # Fallback to current dir if no Output folder found
    if not os.path.exists(output_dir):
        output_dir = "."
        input_dir = "."

    av1_files = glob.glob(os.path.join(output_dir, "*-av1.mkv"))

    if not av1_files:
        print("No *-av1.mkv files found to mux.")
        return

    print(f"Found {len(av1_files)} '-av1.mkv' files. Starting muxing process...\n")

    for av1_file in av1_files:
        filename = os.path.basename(av1_file)
        base_name = filename.replace("-av1.mkv", "")

        # Check for matching source file in Input folder
        possible_sources = [
            os.path.join(input_dir, f"{base_name}.mkv"),
            os.path.join(input_dir, f"{base_name}.mp4"),
            os.path.join(input_dir, f"{base_name}.m2ts"),
            os.path.join(input_dir, f"{base_name}-source.mkv"),
        ]
        source_mkv = None
        for path in possible_sources:
            if os.path.exists(path):
                source_mkv = path
                break

        if not source_mkv:
            print(f"[SKIP] Source file not found for: {filename}")
            continue

        temp_mkv = os.path.join(output_dir, f"{base_name}_temp_no_video.mkv")
        final_output = os.path.join(output_dir, f"{base_name}-output.mkv")
        timestamp_file = os.path.join(output_dir, f"{base_name}_timestamps.txt")

        try:
            # Step 0: Detect VFR using MediaInfo
            is_vfr = check_vfr_mediainfo(source_mkv)
            timestamps_args = []

            # Steps: 1.ExtractAudio -> 2.Merge -> 3.Metadata(PropEdit)
            # If VFR: + ExtractTimestamps = 4 Total
            total_steps = 4 if is_vfr else 2
            current_step = 1

            if is_vfr:
                # Green text for detection
                print(
                    "\033[92mVariable framerate detected, applying timecodes...\033[0m"
                )

                # Get track ID (usually 0, but safest to ask mkvmerge)
                vid_track_id = get_video_track_id(source_mkv) or 0

                # Extract timestamps from the SOURCE video track
                cmd_extract_ts = [
                    MKVEXTRACT,
                    source_mkv,
                    "timestamps_v2",
                    f"{vid_track_id}:{timestamp_file}",
                ]
                run_command(
                    cmd_extract_ts,
                    f"[{base_name}] Step {current_step}/{total_steps} (Timecodes)",
                )
                current_step += 1

                # Prepare args for the final mux
                if os.path.exists(timestamp_file):
                    av1_track_id = get_video_track_id(av1_file) or 0
                    timestamps_args = [
                        "--timestamps",
                        f"{av1_track_id}:{timestamp_file}",
                    ]

            # Step 1 (or 2): Extract Audio/Subs (No Video) from source
            cmd_step1 = [MKVMERGE, "-o", temp_mkv, "--no-video", source_mkv]
            run_command(
                cmd_step1,
                f"[{base_name}] Step {current_step}/{total_steps} (Extract)",
            )
            current_step += 1

            # Step 2 (or 3): Mux AV1 + Audio/Subs + (Optional) Timestamps
            cmd_step2 = [MKVMERGE, "-o", final_output]

            # Timestamps args MUST come BEFORE the AV1 input file
            cmd_step2.extend(timestamps_args)
            cmd_step2.append(av1_file)

            # Add Audio/Subs source
            cmd_step2.append(temp_mkv)

            run_command(
                cmd_step2, f"[{base_name}] Step {current_step}/{total_steps} (Merge)  "
            )
            current_step += 1

            # Step 3 (or 4): Force Variable Frame Rate Mode (Metadata)
            if is_vfr:
                force_vfr_metadata(
                    final_output,
                    f"[{base_name}] Step {current_step}/{total_steps} (VFR Fix)",
                )

            # Cleanup temp mux files
            if os.path.exists(temp_mkv):
                os.remove(temp_mkv)
            if os.path.exists(timestamp_file):
                os.remove(timestamp_file)

            # Delete intermediate AV1 file after successful mux (mirrors Windows behavior)
            if os.path.exists(final_output) and os.path.exists(av1_file):
                print(f"[{base_name}] Deleting intermediate AV1 file...")
                try:
                    os.remove(av1_file)
                    print(f"[{base_name}] Deleted: {os.path.basename(av1_file)}")
                except OSError as e:
                    print(f"[{base_name}] [WARN] Could not delete intermediate file: {e}")

        except subprocess.CalledProcessError:
            print(f"\n[FAIL] Could not process {base_name}. Skipping.")


if __name__ == "__main__":
    mux_files()
