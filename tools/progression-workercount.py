import os
import sys
import psutil
import subprocess
import time
import shutil

# --- CONFIGURATION ---
# Base dir is tools/.. (which is Linux_Dist/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AV1AN_PATH = "av1an"  # Assume system av1an or in path
SAMPLE_FILE = os.path.join(BASE_DIR, "tools", "sample.mkv")
CONFIG_FILE = os.path.join(BASE_DIR, "tools", "workercount-progression.txt")


def cleanup_temp_folders():
    """Deletes temp folders and the test output file."""
    print("Cleaning up temporary test files...", file=sys.stderr)

    # 1. Clean up folders starting with a period
    try:
        for item in os.listdir(BASE_DIR):
            item_path = os.path.join(BASE_DIR, item)
            if os.path.isdir(item_path) and item.startswith("."):
                try:
                    shutil.rmtree(item_path)
                except OSError:
                    pass
    except Exception as e:
        pass

    # 2. Clean up the test output video file
    output_file = os.path.join(BASE_DIR, "sample_svt-av1.mkv")
    if os.path.exists(output_file):
        try:
            os.remove(output_file)
        except OSError:
            pass


def get_optimal_workers():
    print(
        f"Running one-time RAM test (Preset 2) on {os.path.basename(SAMPLE_FILE)}...",
        file=sys.stderr,
    )

    # 1. Start the test process with 1 worker using PRESET 2
    cmd = [
        AV1AN_PATH,
        "-i",
        SAMPLE_FILE,
        "-y",
        "--workers",
        "1",
        "--verbose",
        "-e",
        "svt-av1",
        "-v",
        " --preset 2 --crf 30 --lp 3",  # Note: Extra space in -v string for safety
    ]

    try:
        process = subprocess.Popen(cmd, cwd=BASE_DIR)
    except FileNotFoundError:
        print("Error: av1an executable not found.", file=sys.stderr)
        return 1

    max_total_rss = 0

    try:
        # Monitor for up to 20 seconds
        for _ in range(40):
            if process.poll() is not None:
                break

            try:
                current_rss = 0
                parent = psutil.Process(process.pid)
                current_rss += parent.memory_info().rss

                for child in parent.children(recursive=True):
                    try:
                        current_rss += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                if current_rss > max_total_rss:
                    max_total_rss = current_rss

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            time.sleep(0.5)
    finally:
        if process.poll() is None:
            process.kill()

    # 3. Perform Calculations
    if max_total_rss == 0:
        print("\nWarning: Could not measure RAM. Defaulting to 1 worker.")
        cleanup_temp_folders()
        return 1

    total_ram = psutil.virtual_memory().total
    cpu_threads = os.cpu_count() or 2

    # Math: Leave 10% of TOTAL RAM free
    safe_ram_limit = total_ram * 0.90

    # Calculate Max Workers by RAM
    max_workers_ram = int(safe_ram_limit / max_total_rss)

    # Calculate Max Workers by CPU (Threads / 3)
    max_workers_cpu = int(cpu_threads / 3)

    # Determine bottleneck, then SUBTRACT 1
    calculated_workers = min(max_workers_ram, max_workers_cpu)
    final_workers = max(1, calculated_workers - 1)

    print("\n------------------------------------------------")
    print(f"   - Total System RAM: {total_ram // (1024**2)} MB")
    print(f"   - Peak RAM (1 Worker, Preset 2): {max_total_rss // (1024**2)} MB")
    print(f"   - CPU Threads: {cpu_threads}")
    print(f"   - Calculated Optimal Workers (Safe - 1): {final_workers}")
    print("------------------------------------------------")

    cleanup_temp_folders()

    return final_workers


if __name__ == "__main__":
    if not os.path.exists(SAMPLE_FILE):
        print(f"Error: {SAMPLE_FILE} missing. Defaulting to 1.")
        workers = 1
    else:
        workers = get_optimal_workers()

    try:
        with open(CONFIG_FILE, "w") as f:
            f.write(f"workers={workers}\n")
        print("\nOne-time test complete. Auto worker count set.")
    except Exception as e:
        print(f"Error writing config file: {e}")
