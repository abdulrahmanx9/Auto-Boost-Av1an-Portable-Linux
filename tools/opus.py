import os
import sys
import time
import subprocess
import threading
import queue
import json
import re
import shutil
import platform
from pathlib import Path
import psutil

# ================= CONFIGURATION =================
# Detect CPU threads and leave 1 free for system responsiveness
TOTAL_THREADS = psutil.cpu_count(logical=True)
PARALLELISM = max(1, (TOTAL_THREADS if TOTAL_THREADS else 2) - 1)

IGNORE_EXTS = set()
# =================================================

# Global Queues and Locks
slot_status = ["Idle"] * PARALLELISM
files_queue = queue.Queue()
stop_display = threading.Event()

# Regex for FFMPEG progress parsing
re_ffmpeg = re.compile(r"time=\s*(\S+).*bitrate=\s*(\S+).*speed=\s*(\S+)")

# --- PATH SETUP (Cross-Platform) ---
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

# Folders
INPUT_DIR = Path("Input")
OUTPUT_DIR = Path("Output")

# Ensure Input/Output exist (if running in a context where they are expected)
if not INPUT_DIR.exists():
    try:
        INPUT_DIR.mkdir()
    except:
        pass
if not OUTPUT_DIR.exists():
    try:
        OUTPUT_DIR.mkdir()
    except:
        pass


# Helper to find binaries
def get_binary(name):
    # Try system path first
    path = shutil.which(name)
    if path:
        return path

    # Check Windows portable paths if on Windows
    if platform.system() == "Windows":
        if name == "ffmpeg":
            legacy = ROOT_DIR / "tools" / "av1an" / "ffmpeg.exe"
            if legacy.exists():
                return str(legacy)
        elif name == "opusenc":
            legacy = ROOT_DIR / "tools" / "opus" / "opusenc.exe"
            if legacy.exists():
                return str(legacy)
        elif name in ["mkvmerge", "mkvextract"]:
            legacy = ROOT_DIR / "tools" / "MKVToolNix" / f"{name}.exe"
            if legacy.exists():
                return str(legacy)

    return name  # Return name to rely on system PATH error


FFMPEG_EXE = get_binary("ffmpeg")
OPUSENC_EXE = get_binary("opusenc")
MKVMERGE_EXE = get_binary("mkvmerge")
MKVEXTRACT_EXE = get_binary("mkvextract")

# --- TEMP DIR ---
TEMP_WORK_DIR = OUTPUT_DIR / ".opus_temp"
if not TEMP_WORK_DIR.exists():
    try:
        TEMP_WORK_DIR.mkdir()
    except:
        pass

# --- HELPER FUNCTIONS ---


def run_command(cmd, capture_output=False):
    """Run a subprocess command safely."""
    try:
        cmd_str = [str(c) for c in cmd]
        if capture_output:
            return subprocess.check_output(
                cmd_str, stderr=subprocess.DEVNULL, text=True, encoding="utf-8"
            )

        subprocess.run(
            cmd_str, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )
        return True
    except Exception:
        return False


def get_track_title_string(lang_code):
    """Maps ISO 639-2 codes to Display Names."""
    lookup = {
        "jpn": "Japanese",
        "eng": "English",
        "chi": "Chinese",
        "zho": "Chinese",
        "ger": "German",
        "deu": "German",
        "fra": "French",
        "fre": "French",
        "ita": "Italian",
        "spa": "Spanish",
        "kor": "Korean",
        "rus": "Russian",
        "por": "Portuguese",
        "hin": "Hindi",
        "und": "",
    }
    return lookup.get(lang_code.lower(), "")


# --- PHASE 1: EXTRACTION ---


def get_mkv_tracks(mkv_path):
    cmd = [MKVMERGE_EXE, "-J", str(mkv_path)]
    try:
        res = run_command(cmd, capture_output=True)
        data = json.loads(res)
        return [t for t in data.get("tracks", []) if t["type"] == "audio"]
    except:
        return []


def extract_tracks():
    # Loop over BOTH Input directory AND current directory for flexibility
    mkvs = []
    if INPUT_DIR.exists():
        mkvs.extend(list(INPUT_DIR.glob("*.mkv")))

    # Also check current dir if it's not the root repo (users might run script inside folder)
    curr_mkvs = list(Path(".").glob("*.mkv"))
    for m in curr_mkvs:
        if m.resolve() not in [x.resolve() for x in mkvs]:
            mkvs.append(m)

    if not mkvs:
        print("No .mkv files found in Input/ or current directory.")
        return []

    print(
        f"Found {len(mkvs)} MKV files. Analyzing tracks with {PARALLELISM} workers..."
    )
    extracted_files = []

    for mkv in mkvs:
        tracks = get_mkv_tracks(mkv)
        extract_cmds = []

        # Create a temp folder for this video
        vid_temp = TEMP_WORK_DIR / mkv.stem
        vid_temp.mkdir(exist_ok=True)

        for track in tracks:
            tid = track["id"]
            lang = track["properties"].get("language", "und")

            # Determine extension
            codec_id = track["properties"].get("codec_id", "")
            codec_name = track.get("codec", "")
            full_codec_info = (codec_id + codec_name).upper()

            ext = ".unknown"
            if "AAC" in full_codec_info:
                ext = ".aac"
            elif "AC-3" in full_codec_info or "E-AC-3" in full_codec_info:
                ext = ".ac3"
            elif "DTS-HD" in full_codec_info:
                ext = ".dtshd"
            elif "DTS" in full_codec_info:
                ext = ".dts"
            elif "TRUEHD" in full_codec_info:
                ext = ".thd"
            elif "FLAC" in full_codec_info:
                ext = ".flac"
            elif "VORBIS" in full_codec_info:
                ext = ".ogg"
            elif "OPUS" in full_codec_info:
                ext = ".opus"
            elif "PCM" in full_codec_info:
                ext = ".wav"
            elif "MP3" in full_codec_info:
                ext = ".mp3"

            if ext in IGNORE_EXTS:
                continue

            out_name = vid_temp / f"{mkv.stem}_track{tid}_{lang}{ext}"

            if not out_name.exists():
                extract_cmds.extend([f"{tid}:{out_name}"])

            extracted_files.append(out_name)

        if extract_cmds:
            print(f"Extracting from {mkv.name}...")
            cmd = [MKVEXTRACT_EXE, "tracks", str(mkv)] + extract_cmds
            run_command(cmd)
        else:
            print(f"Skipping extraction for {mkv.name} (files exist).")

    return extracted_files


# --- PHASE 2: DISPLAY ---


def display_loop():
    # Only write to STDOUT
    if sys.stdout.isatty():
        sys.stdout.write("\n" * PARALLELISM)
        while not stop_display.is_set():
            sys.stdout.write(f"\033[{PARALLELISM}A")
            for i in range(PARALLELISM):
                line = slot_status[i]
                clean_line = line[:110].ljust(110)
                sys.stdout.write(f"\r{clean_line}\n")
            sys.stdout.flush()
            time.sleep(0.1)


# --- PHASE 3: WORKERS ---


def get_audio_channels(filepath):
    cmd = [
        FFMPEG_EXE,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=channels",
        "-of",
        "csv=p=0",
        str(filepath),
    ]
    try:
        return subprocess.check_output(
            [str(c) for c in cmd], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except:
        return "2"


def worker_flac(slot_id):
    """Converts source audio to FLAC (Intermediate)."""
    while True:
        try:
            input_file = files_queue.get_nowait()
        except queue.Empty:
            break

        output_file = input_file.with_suffix(".flac")
        fname = input_file.name[:25]
        slot_status[slot_id] = f"{slot_id + 1}: [FLAC] {fname}.. Starting"

        cmd = [
            FFMPEG_EXE,
            "-y",
            "-i",
            str(input_file),
            "-c:a",
            "flac",
            "-sample_fmt",
            "s16",
            "-compression_level",
            "0",
            str(output_file),
        ]

        try:
            proc = subprocess.Popen(
                [str(c) for c in cmd],
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
            while True:
                chunk = proc.stderr.read(256)
                if not chunk and proc.poll() is not None:
                    break
                if chunk:
                    match = re_ffmpeg.search(chunk)
                    if match:
                        t, b, s = match.groups()
                        slot_status[slot_id] = (
                            f"{slot_id + 1}: [FLAC] {fname}.. T:{t} Spd:{s}"
                        )
        except Exception as e:
            slot_status[slot_id] = f"{slot_id + 1}: [Err] {str(e)[:20]}"
            continue

        files_queue.task_done()
    slot_status[slot_id] = f"{slot_id + 1}: Idle"


def worker_opus(slot_id):
    """Encodes FLAC to Opus."""
    while True:
        try:
            input_file = files_queue.get_nowait()
        except queue.Empty:
            break

        output_file = input_file.with_suffix(".opus")
        fname = input_file.name[:25]

        slot_status[slot_id] = f"{slot_id + 1}: [OPUS] {fname}.. Probing"
        channels = get_audio_channels(input_file)

        # Bitrate Strategy
        bitrate = "128"
        try:
            ch_int = int(channels)
            if ch_int >= 8:
                bitrate = "320"
            elif ch_int >= 6:
                bitrate = "256"
            elif ch_int >= 2:
                bitrate = "128"
            else:
                bitrate = "96"
        except:
            bitrate = "128"

        slot_status[slot_id] = f"{slot_id + 1}: [OPUS] {fname}.. Init"

        # Check if opusenc exists, else use ffmpeg
        use_ffmpeg = False
        if "opusenc" not in OPUSENC_EXE and not Path(OPUSENC_EXE).exists():
            use_ffmpeg = True

        if use_ffmpeg:
            cmd = [
                FFMPEG_EXE,
                "-y",
                "-i",
                str(input_file),
                "-c:a",
                "libopus",
                "-b:a",
                f"{bitrate}k",
                str(output_file),
            ]
        else:
            cmd = [OPUSENC_EXE, "--bitrate", bitrate, str(input_file), str(output_file)]

        try:
            proc = subprocess.Popen(
                [str(c) for c in cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )

            while True:
                chunk = proc.stderr.read(10)  # Opusenc writes to stderr
                if not chunk and proc.poll() is not None:
                    break

                if chunk and not use_ffmpeg:
                    match = re.search(r"(\d+)%", chunk)
                    if match:
                        pct = match.group(1)
                        slot_status[slot_id] = f"{slot_id + 1}: [OPUS] {fname}.. {pct}%"
                elif use_ffmpeg and chunk:
                    # Simple ffmpeg progress
                    match = re_ffmpeg.search(chunk)
                    if match:
                        t, b, s = match.groups()
                        slot_status[slot_id] = f"{slot_id + 1}: [OPUS-FF] {fname}.. {t}"

        except Exception as e:
            slot_status[slot_id] = f"{slot_id + 1}: [Err] {str(e)[:20]}"
            continue

        files_queue.task_done()
    slot_status[slot_id] = f"{slot_id + 1}: Idle"


def run_phase(files, worker_func, name):
    if not files:
        return
    print(f"\n--- Starting {name} ({len(files)} files) ---")

    for f in files:
        files_queue.put(f)
    for i in range(PARALLELISM):
        slot_status[i] = "Waiting..."

    stop_display.clear()
    d_thread = threading.Thread(target=display_loop, daemon=True)
    d_thread.start()

    threads = []
    for i in range(PARALLELISM):
        t = threading.Thread(target=worker_func, args=(i,))
        t.start()
        threads.append(t)

    files_queue.join()
    stop_display.set()
    d_thread.join()
    for t in threads:
        t.join()

    if sys.stdout.isatty():
        sys.stdout.write(f"\033[{PARALLELISM}B")
    print(f"{name} Complete.")


# --- PHASE 4: MUXING ---


def mux_final_files():
    # Scan both INPUT and CWD for source MKVs
    source_mkvs = {}

    def scan_for_sources(folder):
        for m in folder.glob("*.mkv"):
            source_mkvs[m.stem] = m

    if INPUT_DIR.exists():
        scan_for_sources(INPUT_DIR)
    scan_for_sources(Path("."))

    print(f"\n--- Starting Muxing Phase ---")
    files_processed = 0

    # Iterate source files we found
    for stem, mkv_path in source_mkvs.items():
        # Look for processed audio in temp dir
        vid_temp = TEMP_WORK_DIR / stem
        if not vid_temp.exists():
            continue

        audio_files = list(vid_temp.glob("*.opus"))
        if not audio_files:
            continue

        # Sort tracks by ID (filename pattern: name_trackID_lang.opus)
        # re pattern: .*_track(\d+)_([a-zA-Z0-9]+)\.opus
        tracks_to_mux = []
        pattern = re.compile(r".*_track(\d+)_([a-zA-Z0-9]+)\.opus$")

        for af in audio_files:
            match = pattern.match(af.name)
            if match:
                tracks_to_mux.append(
                    {"path": af, "id": int(match.group(1)), "lang": match.group(2)}
                )

        tracks_to_mux.sort(key=lambda x: x["id"])

        # Decide output path
        # If input was in Input/, put in Output/
        # If input was in ., put in Output/ (if Output exists) or ./opus-output
        if "Input" in str(mkv_path.parent):
            output_file = OUTPUT_DIR / mkv_path.name
        else:
            local_out = Path("opus-output")
            local_out.mkdir(exist_ok=True)
            output_file = local_out / mkv_path.name

        print(f"Muxing: {mkv_path.name} -> {output_file}")

        # Build command
        cmd = [MKVMERGE_EXE, "-o", str(output_file), "--no-audio", str(mkv_path)]

        for t in tracks_to_mux:
            title = get_track_title_string(t["lang"])
            cmd.extend(
                [
                    "--language",
                    f"0:{t['lang']}",
                    "--track-name",
                    f"0:{title} (Opus)",
                    str(t["path"]),
                ]
            )

        if run_command(cmd):
            files_processed += 1
        else:
            print("  > Error during muxing.")

    print(f"\nAll done. Processed {files_processed} videos.")

    # Cleanup Temp
    try:
        if TEMP_WORK_DIR.exists():
            shutil.rmtree(TEMP_WORK_DIR)
            print("Temp files cleaned up.")
    except:
        print("Warning: Could not clean up temp files.")


# --- MAIN ENTRY ---


def main():
    try:
        extracted = extract_tracks()

        to_flac = [f for f in extracted if f.suffix != ".flac" and f.suffix != ".opus"]
        to_opus = [f for f in extracted if f.suffix == ".flac"]

        if to_flac:
            run_phase(to_flac, worker_flac, "Converting to Intermediate FLAC")
            for f in to_flac:
                to_opus.append(f.with_suffix(".flac"))

        if to_opus:
            valid_opus_inputs = [f for f in to_opus if f.exists()]
            run_phase(valid_opus_inputs, worker_opus, "Encoding to Opus")

        mux_final_files()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting safely.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nAn unexpected error occurred: {e}")
        # import traceback
        # traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
