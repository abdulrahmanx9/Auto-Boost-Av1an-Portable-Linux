import os
import subprocess
import glob
import json
import sys

# Path to mkvmerge executable (System path for Linux)
MKVMERGE = "mkvmerge"


def get_video_properties(file_path):
    """
    Uses mkvmerge -J to get the video track ID and display dimensions/aspect ratio.
    """
    cmd = [MKVMERGE, "-J", file_path]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            check=True,
        )
        data = json.loads(result.stdout)

        for track in data.get("tracks", []):
            if track.get("type") == "video":
                props = track.get("properties", {})
                track_id = track.get("id")

                # Check for display_dimensions (e.g., "1920x1080")
                display_dim = props.get("display_dimensions")

                if track_id is not None and display_dim:
                    return track_id, display_dim

        return None, None
    except Exception as e:
        print(f"[ERROR] Failed to read JSON from {file_path}: {e}")
        return None, None


def process_files():
    # Target files produced by mux.py usually end in -output.mkv
    target_files = glob.glob("*-output.mkv")

    if not target_files:
        print("No '*-output.mkv' files found in the current directory.")
        return

    print(
        f"Found {len(target_files)} files to check. Starting aspect ratio correction...\n"
    )

    for target_file in target_files:
        # Determine the likely source filename
        # Expectation: "Video-source.mkv" -> "Video-output.mkv"
        base_name = target_file.replace("-output.mkv", "")

        possible_sources = [f"{base_name}-source.mkv", f"{base_name}.mkv"]
        source_file = None

        for p in possible_sources:
            if os.path.exists(p):
                source_file = p
                break

        if not source_file:
            print(f"[SKIP] No source file found for: {target_file}")
            continue

        print(f"Processing: {target_file}")
        print(f"   Source : {source_file}")

        # 1. Get Aspect Ratio from Source
        track_id, display_dim = get_video_properties(source_file)

        if not display_dim:
            print("   [SKIP] Could not detect display dimensions in source file.")
            continue

        # 2. Construct Output Filename
        final_output = target_file.replace(".mkv", "-forcedaspect.mkv")

        # 3. Mux with forced aspect ratio
        # We need to find the video track ID in the TARGET file to apply the flag to it.
        target_tid, _ = get_video_properties(target_file)
        if target_tid is None:
            target_tid = 0

        # Format: --aspect-ratio TID:W/H
        width, height = display_dim.split("x")
        aspect_ratio_arg = f"{target_tid}:{width}/{height}"

        print(f"   Applying Aspect Ratio: {width}/{height} (Track {target_tid})")

        cmd_remux = [
            MKVMERGE,
            "-o",
            final_output,
            "--aspect-ratio",
            aspect_ratio_arg,
            target_file,
        ]

        try:
            subprocess.run(cmd_remux, check=True)
            print(f"   [DONE] Created: {final_output}\n")
        except subprocess.CalledProcessError:
            print(f"   [FAIL] Error remuxing {target_file}\n")


if __name__ == "__main__":
    process_files()
