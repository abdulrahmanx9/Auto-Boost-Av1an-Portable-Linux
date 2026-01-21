#!/usr/bin/env python3
"""
Add Subtitles Script - Linux Port
Muxes subtitles (.ass/.srt) and fonts (.ttf/.otf) into MKV files.
"""

import os
import glob
import subprocess
import re
import sys
import shutil

# --- CONFIGURATION ---
# Mapping filename tags to ISO 639-1 (2-letter) codes where possible.
# The script uses Regex Word Boundaries, so "en" matches "file.en.srt" but NOT "broken.srt"
LANG_MAP = {
    # English
    "english": "en",
    "eng": "en",
    "en": "en",
    # Japanese
    "japanese": "ja",
    "jpn": "ja",
    "jp": "ja",
    # French
    "french": "fr",
    "fre": "fr",
    "fra": "fr",
    "fr": "fr",
    # German
    "german": "de",
    "ger": "de",
    "deu": "de",
    "de": "de",
    # Spanish
    "spanish": "es",
    "spa": "es",
    "es": "es",
    # Italian
    "italian": "it",
    "ita": "it",
    "it": "it",
    # Russian
    "russian": "ru",
    "rus": "ru",
    "ru": "ru",
    # Chinese
    "chinese": "zh",
    "chi": "zh",
    "zho": "zh",
    "zh": "zh",
    # Portuguese
    "portuguese": "pt",
    "por": "pt",
    "pt": "pt",
    # Korean
    "korean": "ko",
    "kor": "ko",
    "ko": "ko",
    # Arabic
    "arabic": "ar",
    "ara": "ar",
    "ar": "ar",
    # Default (Undetermined)
    "default": "und",
}


def get_lang_code(filename):
    """
    Derives language code from filename using strict word boundaries.
    Example: 'French.ass' -> 'fr', 'frozen.ass' -> 'und' (ignores partial match)
    """
    lower_name = filename.lower()

    for key, code in LANG_MAP.items():
        if key == "default":
            continue

        # Regex: \b matches word boundaries (spaces, periods, underscores, dashes, start/end of string)
        # matches: "French", ".fr.", "_en_", " eng "
        pattern = r"\b" + re.escape(key) + r"\b"

        if re.search(pattern, lower_name):
            return code

    return "und"


def find_mkvmerge():
    """Finds mkvmerge in the system PATH."""
    path = shutil.which("mkvmerge")
    if path:
        return path
    print("[ERROR] Could not find mkvmerge. Please install mkvtoolnix:")
    print("        sudo apt install mkvtoolnix")
    sys.exit(1)


def process_files(mkvmerge, mkv_input, subtitle_files, font_files):
    """Constructs and runs the mkvmerge command."""

    folder = os.path.dirname(mkv_input)
    filename = os.path.splitext(os.path.basename(mkv_input))[0]
    output_file = os.path.join(folder, f"{filename}_muxed.mkv")

    # Base command
    cmd = [mkvmerge, "-o", output_file, mkv_input]

    # Add Fonts
    for font in font_files:
        cmd.extend(["--attach-file", font])

    # Add Subtitles
    for sub in subtitle_files:
        sub_filename = os.path.basename(sub)
        track_title = os.path.splitext(sub_filename)[0]

        # Clean S01E01 from track title if present
        s_e_match = re.search(r"[sS]\d+[eE]\d+[\.]?", track_title)
        if s_e_match:
            clean_title = track_title.replace(s_e_match.group(0), "")
            clean_title = clean_title.strip(" .-_")
            if clean_title:
                track_title = clean_title

        lang = get_lang_code(sub_filename)

        # Options must precede the input file they apply to
        # 0 refers to track ID 0 of the subtitle file (which is the sub track)
        cmd.extend(["--language", f"0:{lang}", "--track-name", f"0:{track_title}", sub])

    print(f"    ... Muxing {len(subtitle_files)} subs and {len(font_files)} fonts.")

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        print(f"    [SUCCESS] Created: {os.path.basename(output_file)}")
    except subprocess.CalledProcessError:
        print(f"    [FAILURE] Error processing {os.path.basename(mkv_input)}")


def main():
    # 1. GET TARGET DIRECTORY
    if len(sys.argv) > 1:
        # Strip quotes just in case the shell passed them weirdly
        target_dir = sys.argv[1].strip('"')
    else:
        target_dir = os.getcwd()

    mkvmerge_exe = find_mkvmerge()

    print(f"Scanning directory: {target_dir}")

    # 2. GATHER FILES
    mkvs = glob.glob(os.path.join(target_dir, "*.mkv"))
    subs = glob.glob(os.path.join(target_dir, "*.ass")) + glob.glob(
        os.path.join(target_dir, "*.srt")
    )
    fonts = glob.glob(os.path.join(target_dir, "*.ttf")) + glob.glob(
        os.path.join(target_dir, "*.otf")
    )

    # Remove already muxed files from the list
    mkvs = [f for f in mkvs if "_muxed" not in f]

    if not mkvs:
        print("[ERROR] No .mkv files found.")
        print("Ensure your .mkv files are in the same folder as the .sh file.")
        return

    # --- Scenario 1: Single MKV Mode ---
    if len(mkvs) == 1:
        mkv_file = mkvs[0]
        print(f"\n[Single File Mode] Processing: {os.path.basename(mkv_file)}")

        # In single mode, we take ALL subtitles found in that folder
        matched_subs = subs

        if not matched_subs and not fonts:
            print("No subtitles or fonts found to add.")
            return

        process_files(mkvmerge_exe, mkv_file, matched_subs, fonts)

    # --- Scenario 2: Batch Mode (SxxExx) ---
    else:
        print(f"\n[Batch Mode] Found {len(mkvs)} MKVs. matching via SxxExx...")

        for mkv_file in mkvs:
            basename = os.path.basename(mkv_file)
            # Regex to find S01E01 or s01e01
            match = re.search(r"[sS](\d+)[eE](\d+)", basename)

            if match:
                s_e_string = match.group(0).lower()  # e.g. s01e01
                print(f"  > Matched Episode code: {s_e_string} in {basename}")

                # Find subs that contain this code
                current_subs = []
                for sub in subs:
                    if s_e_string in os.path.basename(sub).lower():
                        current_subs.append(sub)

                if current_subs or fonts:
                    process_files(mkvmerge_exe, mkv_file, current_subs, fonts)
                else:
                    print(
                        f"    [Skipping] No matching subtitles or fonts found for {basename}"
                    )
            else:
                print(f"  [Warning] Could not detect SxxExx in: {basename}. Skipping.")


if __name__ == "__main__":
    main()
