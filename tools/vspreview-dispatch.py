#!/usr/bin/env python3
"""
VSPreview Dispatch Script - Linux Port
Generates a VPY script for multiple MKV files and launches vspreview.
"""

import os
import glob
import sys
import subprocess
import shutil


def cleanup(vpy_file):
    """Cleans up generated VPY files, .vsjet folder, and .ffindex files."""
    # Delete the generated .vpy file used for the session
    if vpy_file and os.path.exists(vpy_file):
        try:
            os.remove(vpy_file)
        except OSError:
            pass

    # Delete all other .vpy files in the folder (cleanup for stale files)
    for f in glob.glob("*.vpy"):
        try:
            os.remove(f)
        except OSError:
            pass

    # Delete .vsjet folder
    if os.path.exists(".vsjet"):
        try:
            shutil.rmtree(".vsjet")
        except OSError:
            pass

    # Delete .ffindex files
    for f in glob.glob("*.ffindex"):
        try:
            os.remove(f)
        except OSError:
            pass


def create_vpy_script(mkv_files):
    """Generates the .vpy script content based on found MKV files."""

    # 1. Header and Style Definition
    # We define the ASS style string here to be written into the VPY file
    lines = [
        "import vapoursynth as vs",
        "core = vs.core",
        "",
        "# Define an ASS-style string with Alignment=7 (top-left)",
        'ass_style = ",".join([',
        '    "Arial", "24",',
        '    "&H00FFFFFF", "&H000000FF", "&H00000000", "&H00000000",',
        '    "0", "0", "0", "0",',
        '    "100", "100",',
        '    "0", "0",',
        '    "1", "2", "0", "7",',
        '    "10", "10", "10",',
        '    "1"',
        "])",
        "",
    ]

    # 2. Logic to handle one or multiple files
    vpy_filename = "preview.vpy"

    for i, mkv in enumerate(mkv_files):
        # Escape backslashes for the script string (use forward slashes on Linux)
        mkv_path = os.path.abspath(mkv)

        # Get just the filename (e.g., "video.mkv") for the label
        file_label = os.path.basename(mkv)

        lines.append(f"# Loading file: {file_label}")
        lines.append(f'clip{i} = core.ffms2.Source(source="{mkv_path}")')

        # Add the subtitle with the filename
        lines.append(
            f'clip{i} = core.sub.Subtitle(clip{i}, text=["{file_label}"], style=ass_style)'
        )

        # Set output. Note: set_output(0) corresponds to pressing '1' in vspreview
        lines.append(f"clip{i}.set_output({i})")
        lines.append("")

    return vpy_filename, "\n".join(lines)


def main():
    # 1. Scan for MKV files in the current directory
    mkv_files = glob.glob("*.mkv")

    if not mkv_files:
        print("No .mkv files found in this folder.")
        print(
            "Please ensure your MKV files are in the 'extras' folder alongside vspreview.sh"
        )
        input("Press Enter to exit...")
        return

    # 2. Generate the .vpy script
    vpy_filename, script_content = create_vpy_script(mkv_files)

    print(f"Generating script: {vpy_filename} for {len(mkv_files)} file(s)...")
    with open(vpy_filename, "w", encoding="utf-8") as f:
        f.write(script_content)

    # 3. Execute vspreview
    cmd = [sys.executable, "-m", "vspreview", vpy_filename]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running vspreview: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        # 4. Cleanup on exit
        print("Cleaning up temporary files...")
        cleanup(vpy_filename)


if __name__ == "__main__":
    main()
