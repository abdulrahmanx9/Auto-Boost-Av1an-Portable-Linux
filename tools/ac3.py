import os
import sys
import time
import subprocess
import threading
import queue
import json
import re
from pathlib import Path
import psutil

# ================= CONFIGURATION =================
# Detect CPU threads and leave 1 free for system responsiveness
TOTAL_THREADS = psutil.cpu_count(logical=True)
PARALLELISM = max(1, TOTAL_THREADS - 1)

IGNORE_EXTS = set()
LOSSLESS_EXTS = {".flac", ".wav", ".thd", ".dtshd", ".pcm"}
# =================================================

# Global Queues and Locks
slot_status = ["Idle"] * PARALLELISM
files_queue = queue.Queue()
stop_display = threading.Event()

# Regex for FFMPEG progress parsing
re_ffmpeg = re.compile(r"time=\s*(\S+).*bitrate=\s*(\S+).*speed=\s*(\S+)")

# --- PATH SETUP (Relative to this script) ---
# Location: Linux_Dist/tools/ac3.py
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

# Linux: Use system binaries
FFMPEG_EXE = "ffmpeg"
FFPROBE_EXE = "ffprobe"
MKVMERGE_EXE = "mkvmerge"
MKVEXTRACT_EXE = "mkvextract"

# Settings file is now in 'audio-encoding'
SETTINGS_FILE = ROOT_DIR / "audio-encoding" / "settings-encode-ac3-audio.txt"

# --- HELPER FUNCTIONS ---


def load_settings():
    """Reads the settings file for bitrates. Returns a dictionary with defaults if missing."""
    defaults = {"Above 5.1": "640", "5.1": "448", "2.1": "320", "2.0": "192"}

    if not SETTINGS_FILE.exists():
        print(f"Warning: Settings file not found at {SETTINGS_FILE}. Using defaults.")
        return defaults

    try:
        with open(SETTINGS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                defaults[key.strip()] = val.strip()
    except Exception as e:
        print(f"Error reading settings file: {e}. Using defaults.")

    return defaults


BITRATE_SETTINGS = load_settings()


def run_command(cmd, capture_output=False):
    """Run a subprocess command safely without bleeding stderr to console."""
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


def run_with_progress(cmd):
    """Run a command (mkvextract/mkvmerge) and parse stdout for 'Progress: %' only."""
    try:
        process = subprocess.Popen(
            [str(c) for c in cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )

        current_line = []
        while True:
            char = process.stdout.read(1)
            if not char and process.poll() is not None:
                break

            if char:
                if char in ("\r", "\n"):
                    line = "".join(current_line).strip()
                    if line.startswith("Progress:"):
                        sys.stdout.write(f"\r    {line}")
                        sys.stdout.flush()
                    current_line = []
                else:
                    current_line.append(char)

        print()
        return process.returncode == 0
    except Exception as e:
        print(f"    Error during execution: {e}")
        return False


def get_track_title_string(lang_code):
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


def get_user_choice():
    print("\n" + "=" * 50)
    print("      AC3 AUDIO ENCODER - SELECTION MENU")
    print("=" * 50)
    print("1. Encode ONLY Lossless audio to AC3 (Recommended)")
    print("   (Processing: FLAC, PCM/WAV, TrueHD, DTS-HD)")
    print("   (Preserves: EAC3, AAC, DTS Core, Vorbis as-is)")
    print("\n2. Encode ALL audio tracks to AC3")
    print("   (Warning: Causes generational loss on AC3/AAC/DTS)")
    print("=" * 50)

    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice == "1":
            return 1
        elif choice == "2":
            return 2
        print("Invalid input. Please enter 1 or 2.")


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
    mkvs = list(Path(".").glob("*.mkv"))
    if not mkvs:
        print("No .mkv files found in the current directory.")
        return []

    print(f"Found {len(mkvs)} MKV files. Analyzing tracks...")
    extracted_files = []

    for mkv in mkvs:
        tracks = get_mkv_tracks(mkv)
        extract_cmds = []

        for track in tracks:
            tid = track["id"]
            lang = track["properties"].get("language", "und")

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

            if ext in IGNORE_EXTS:
                continue

            out_name = f"{mkv.stem}_track{tid}_{lang}{ext}"

            if not Path(out_name).exists():
                extract_cmds.extend([f"{tid}:{out_name}"])

            extracted_files.append(Path(out_name))

        if extract_cmds:
            print(f"Extracting from {mkv.name}...")
            cmd = [MKVEXTRACT_EXE, "tracks", str(mkv)] + extract_cmds
            run_with_progress(cmd)

    return extracted_files


# --- PHASE 2: DISPLAY ---


def display_loop():
    last_line_count = 0
    sys.stdout.write("\n")

    while not stop_display.is_set():
        active_slots = [s for s in slot_status if s != "Idle"]
        current_line_count = len(active_slots)

        if last_line_count > 0:
            sys.stdout.write(f"\033[{last_line_count}A")

        for line in active_slots:
            clean_line = line[:110]
            sys.stdout.write(f"\r{clean_line}\033[K\n")

        if current_line_count < last_line_count:
            sys.stdout.write("\033[J")

        last_line_count = current_line_count
        sys.stdout.flush()
        time.sleep(0.1)

    if last_line_count > 0:
        sys.stdout.write(f"\033[{last_line_count}A")
        sys.stdout.write("\033[J")
    sys.stdout.flush()


# --- PHASE 3: WORKERS ---


def get_audio_channels(filepath):
    cmd = [
        FFPROBE_EXE,
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


def worker_ac3(slot_id):
    while True:
        try:
            input_file = files_queue.get_nowait()
        except queue.Empty:
            break

        output_file = input_file.with_suffix(".ac3")
        fname = input_file.name[:25]

        slot_status[slot_id] = f"{slot_id + 1}: [AC3] {fname}.. Probing"
        channels = get_audio_channels(input_file)

        bitrate_val = BITRATE_SETTINGS.get("2.0", "192")  # Default
        try:
            ch_int = int(channels)
            if ch_int > 6:
                bitrate_val = BITRATE_SETTINGS.get("Above 5.1", "640")
            elif ch_int >= 6:
                bitrate_val = BITRATE_SETTINGS.get("5.1", "448")
            elif ch_int >= 3:
                bitrate_val = BITRATE_SETTINGS.get("2.1", "320")
            else:
                bitrate_val = BITRATE_SETTINGS.get("2.0", "192")
        except:
            pass

        bitrate_str = f"{bitrate_val}k"

        slot_status[slot_id] = (
            f"{slot_id + 1}: [AC3] {fname}.. Init ({channels}ch @ {bitrate_str})"
        )

        # FFMPEG Command: No FLAC intermediary, direct convert
        cmd = [
            FFMPEG_EXE,
            "-y",
            "-i",
            str(input_file),
            "-c:a",
            "ac3",
            "-b:a",
            bitrate_str,
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
                            f"{slot_id + 1}: [AC3] {fname}.. T:{t} Spd:{s} ({channels}ch)"
                        )
        except Exception as e:
            slot_status[slot_id] = f"{slot_id + 1}: [Err] {str(e)[:20]}"
            continue

        files_queue.task_done()
    slot_status[slot_id] = "Idle"


def run_phase(files, worker_func, name):
    if not files:
        return
    print(f"\n--- Starting {name} ({len(files)} files) ---")

    for f in files:
        files_queue.put(f)
    for i in range(PARALLELISM):
        slot_status[i] = "Idle"

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

    print(f"{name} Complete.")


# --- PHASE 4: MUXING ---


def get_track_delay_ms(mkv_path, track_id):
    temp_ts = Path(f"temp_delay_{mkv_path.stem}_{track_id}.txt")
    delay = 0
    try:
        cmd = [MKVEXTRACT_EXE, "timestamps_v2", str(mkv_path), f"{track_id}:{temp_ts}"]
        run_command(cmd)

        if temp_ts.exists():
            with open(temp_ts, "r") as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        val = float(line)
                        delay = int(val)
                        break
                    except:
                        pass
    except:
        pass
    finally:
        if temp_ts.exists():
            try:
                os.remove(temp_ts)
            except:
                pass

    return delay


def mux_final_files():
    current_dir = Path.cwd()
    output_dir = current_dir / "ac3-output"
    output_dir.mkdir(exist_ok=True)

    print(f"\n--- Starting Muxing Phase ---")
    files_processed = 0

    for mkv_path in current_dir.glob("*.mkv"):
        safe_stem = re.escape(mkv_path.stem)

        # Matches:  Video_track1_eng.ac3  OR  Video_track1_eng.thd
        pattern = re.compile(
            rf"^{safe_stem}_track(\d+)_([a-zA-Z0-9]+)\.([a-zA-Z0-9]+)$"
        )

        track_candidates = {}

        for f in current_dir.iterdir():
            match = pattern.match(f.name)
            if match:
                t_num = int(match.group(1))
                lang = match.group(2)
                ext = match.group(3).lower()

                if t_num not in track_candidates:
                    track_candidates[t_num] = {"lang": lang, "ac3": None, "orig": None}

                if ext == "ac3":
                    track_candidates[t_num]["ac3"] = f
                else:
                    track_candidates[t_num]["orig"] = f

        if not track_candidates:
            print(f"Skipping {mkv_path.name} (No audio tracks identified)")
            continue

        output_file = output_dir / mkv_path.name
        print(f"Muxing: {mkv_path.name}")

        subtitle_flags = []
        try:
            cmd = [MKVMERGE_EXE, "-J", str(mkv_path)]
            res = run_command(cmd, capture_output=True)
            file_info = json.loads(res)
            for track in file_info.get("tracks", []):
                if track.get("type") == "subtitles":
                    tid = track.get("id")
                    subtitle_flags.extend(["--compression", f"{tid}:zlib"])
        except:
            pass

        cmd = [MKVMERGE_EXE, "-o", str(output_file)]
        cmd.extend(subtitle_flags)
        cmd.append("--no-audio")
        cmd.append(str(mkv_path))

        sorted_ids = sorted(track_candidates.keys())

        for tid in sorted_ids:
            cand = track_candidates[tid]
            lang = cand["lang"]

            # Logic: Prefer AC3, fallback to ORIGINAL
            final_path = cand["ac3"] if cand["ac3"] else cand["orig"]

            if not final_path:
                continue

            title = get_track_title_string(lang)
            title_flag = title if title else lang

            is_ac3 = final_path.suffix == ".ac3"

            delay_ms = get_track_delay_ms(mkv_path, tid)
            delay_str = ""
            if delay_ms != 0:
                delay_str = f" [Delay: {delay_ms}ms]"
                cmd.extend(["--sync", f"0:{delay_ms}"])

            display_str = "AC3" if is_ac3 else f"Original ({final_path.suffix})"

            print(f"  + Track {tid}: {title_flag} [{display_str}]{delay_str}")

            cmd.extend(
                [
                    "--language",
                    f"0:{lang}",
                    "--track-name",
                    f"0:{title_flag}",
                    str(final_path),
                ]
            )

        if run_with_progress(cmd):
            files_processed += 1
        else:
            print("  > Error during muxing (check logs).")

    print(f"\nAll done. Processed {files_processed} videos into 'ac3-output'.")


# --- MAIN ENTRY ---


def main():
    try:
        mode = get_user_choice()

        # 1. Extract ALL tracks
        extracted = extract_tracks()

        to_encode_candidates = []

        if mode == 2:
            # Mode 2: Encode Everything
            to_encode_candidates = extracted
        else:
            # Mode 1: Lossless Only
            for f in extracted:
                if f.suffix in LOSSLESS_EXTS:
                    to_encode_candidates.append(f)

        # Filter: Remove files that are already .ac3
        to_ac3 = []

        print("\nPreparing files for AC3 conversion...")
        for f in to_encode_candidates:
            if f.suffix == ".ac3":
                pass  # Already ac3
            else:
                to_ac3.append(f)

        if to_ac3:
            # No FLAC intermediary needed for ffmpeg->ac3
            run_phase(to_ac3, worker_ac3, "Encoding to AC3")

        mux_final_files()

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting safely.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nAn unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
