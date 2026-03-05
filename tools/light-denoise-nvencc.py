import os
import glob
import subprocess
import sys
import shutil

# --- Configuration & Paths ---
# Tools are expected to be in PATH on Linux
NVENCC_EXE = "nvencc"
MKVMERGE_EXE = "mkvmerge"


def run_nvencc(input_file, output_h265):
    """Runs NVEncC with fallback logic."""
    cmd_base = [
        NVENCC_EXE,
        "--codec",
        "h265",
        "--preset",
        "p2",
        "--output-depth",
        "10",
        "--lossless",
        "--vpp-fft3d",
        "sigma=0.2",
        "-i",
        input_file,
        "-o",
        output_h265,
    ]

    # Try with --avhw (Hardware Decode) first
    cmd_primary = cmd_base[:1] + ["--avhw"] + cmd_base[1:]
    print(f"\n[NVEncC] Processing: {input_file} (Attempt 1: With --avhw)")
    print("Command:", " ".join(cmd_primary))

    # Run with full output visible to user
    result = subprocess.run(cmd_primary)

    if result.returncode == 0:
        return True

    # Fallback without --avhw
    print(f"\n[NVEncC] Attempt 1 failed. Retrying without --avhw...")
    print("Command:", " ".join(cmd_base))
    result = subprocess.run(cmd_base)

    return result.returncode == 0


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

        # Mkvmerge progress lines usually start with "Progress:"
        if line.startswith("Progress:"):
            # Print over the same line (\r) to create a progress bar effect
            sys.stdout.write(f"\r[{task_name}] {line}")
            sys.stdout.flush()

    process.wait()
    sys.stdout.write("\n")  # New line after progress finishes

    if process.returncode != 0:
        print(f"[{task_name}] Error occurred.")
        return False
    return True


def main():
    # Work in the directory where the script was called
    work_dir = os.getcwd()

    # Verify tools exist before starting
    if shutil.which(NVENCC_EXE) is None:
        print(f"Error: {NVENCC_EXE} not found in PATH.")
        return
    if shutil.which(MKVMERGE_EXE) is None:
        print(f"Error: {MKVMERGE_EXE} not found in PATH.")
        print("Install it with: sudo apt install mkvtoolnix")
        return

    mkv_files = glob.glob("*.mkv")

    if not mkv_files:
        print("No .mkv files found in the current folder.")
        return

    for mkv in mkv_files:
        # Skip files we've already generated to avoid loops
        if "-lightdenoise" in mkv or "-no-video" in mkv:
            continue

        base_name = os.path.splitext(mkv)[0]
        temp_h265 = f"{base_name}.h265"
        temp_no_video = f"{base_name}-no-video.mkv"
        final_output = f"{base_name}-lightdenoise.mkv"

        print(f"==================================================")
        print(f"Processing: {mkv}")
        print(f"==================================================")

        # 1. Run NVEncC
        if not run_nvencc(mkv, temp_h265):
            print(f"Skipping {mkv} due to NVEncC errors.")
            continue

        # 2. Extract non-video tracks (Audio/Subs/Chapters)
        # mkvmerge -o "input-no-video.mkv" --no-video "input.mkv"
        cmd_extract = [MKVMERGE_EXE, "-o", temp_no_video, "--no-video", mkv]
        if not run_mkvmerge_progress(cmd_extract, "Extracting Audio/Subs"):
            continue

        # 3. Mux final file
        # mkvmerge -o output.mkv video.h265 input-no-video.mkv
        cmd_mux = [MKVMERGE_EXE, "-o", final_output, temp_h265, temp_no_video]
        if run_mkvmerge_progress(cmd_mux, "Muxing Final File"):
            print(f"Done! Created: {final_output}")

            # Cleanup temp files
            try:
                if os.path.exists(temp_h265):
                    os.remove(temp_h265)
                if os.path.exists(temp_no_video):
                    os.remove(temp_no_video)
                print("Temporary files cleaned up.")
            except OSError as e:
                print(f"Warning: Could not clean up temp files: {e}")


if __name__ == "__main__":
    main()
