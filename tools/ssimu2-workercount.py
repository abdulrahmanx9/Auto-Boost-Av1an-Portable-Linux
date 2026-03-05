#!/usr/bin/env python3
import os
import sys
import psutil
import subprocess
import time
import shutil
import concurrent.futures
import gc
import platform
import random
from pathlib import Path
import vapoursynth as vs

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).parent.parent.resolve()
TOOLS_DIR = BASE_DIR / "tools"
SAMPLE_FILE = TOOLS_DIR / "sample.mkv"
CONFIG_FILE = TOOLS_DIR / "workercount-ssimu2.txt"
TEMP_DIR = TOOLS_DIR / "ssimu2_bench_temp"

# Benchmark Settings
SKIP = 3

try:
    from vstools import core, clip_async_render
except ImportError:
    print("Error: vstools not found.", file=sys.stderr)
    sys.exit(1)


def cleanup_temp_files():
    """Removes temporary benchmark files and directories."""
    # 1. Clear VS Cache
    try:
        if hasattr(vs.core, "clear_cache"):
            vs.core.clear_cache()
    except:
        pass
    gc.collect()

    # 2. Remove Benchmark Temp Dir
    if TEMP_DIR.exists():
        try:
            shutil.rmtree(TEMP_DIR)
        except:
            pass

    # 3. Remove Index Files
    for ext in [".ffindex", ".lwi", ".json"]:
        f = SAMPLE_FILE.with_suffix(SAMPLE_FILE.suffix + ext)
        if f.exists():
            try:
                f.unlink()
            except:
                pass


def run_fast_pass():
    print("Generating benchmark assets (Fast Pass)...", file=sys.stderr)
    output_file = TEMP_DIR / "sample_fastpass.mkv"
    if not TEMP_DIR.exists():
        TEMP_DIR.mkdir()

    vpy_content = f"""
import vapoursynth as vs
core = vs.core
src = core.ffms2.Source(source=r"{SAMPLE_FILE}")
src.set_output()
"""
    vpy_path = TEMP_DIR / "source.vpy"
    with open(vpy_path, "w") as f:
        f.write(vpy_content)

    av1an_exe = shutil.which("av1an")
    if not av1an_exe:
        print("Error: av1an executable not found in PATH.", file=sys.stderr)
        return None

    cmd = [
        av1an_exe,
        "-i",
        str(vpy_path),
        "-e",
        "svt-av1",
        "-c",
        "mkvmerge",
        "-w",
        "1",
        "--split-method",
        "none",
        "-v",
        "--preset 10 --crf 35",
        "-o",
        str(output_file),
    ]

    try:
        print("-" * 50)
        # On Linux, usually safe to run without shell=True for simple lists
        subprocess.run(cmd, check=True, cwd=TEMP_DIR)
        print("-" * 50)
        return output_file
    except subprocess.CalledProcessError:
        print("Error: Fast pass generation failed.", file=sys.stderr)
        return None


# --- WORKER CALCULATION ---
def calculate_optimal_count(fps, rss_per_worker):
    if fps <= 0:
        return 1
    total_ram = psutil.virtual_memory().total
    cpu_threads = os.cpu_count()
    safe_ram = total_ram * 0.85
    if rss_per_worker <= 0:
        rss_per_worker = 100 * 1024 * 1024
    max_workers_ram = int(safe_ram / rss_per_worker)
    max_workers = min(max_workers_ram, cpu_threads)
    return max(1, max_workers)


# --- BENCHMARK FUNCTIONS ---


def benchmark_gpu_vship(encoded_file):
    """
    Benchmarks vs-hip on Linux. Unlike Windows, we don't manage DLLs.
    We just check if the plugin is loaded and usable.
    """
    if not hasattr(core, "vship"):
        return -1

    print("   Benchmarking GPU (vs-hip)...", file=sys.stderr)

    # Subprocess for isolation
    bench_script = f"""
import sys
import time
import vapoursynth as vs
try:
    from vstools import core, clip_async_render
except:
    sys.exit(0)

core = vs.core
SKIP = {SKIP}

try:
    # We strip path details for safety, re-loading paths
    src = core.ffms2.Source(source=r"{SAMPLE_FILE}").resize.Bicubic(format=vs.RGB24, matrix_in_s="709")[::SKIP]
    enc = core.ffms2.Source(source=r"{encoded_file}").resize.Bicubic(format=vs.RGB24, matrix_in_s="709")[::SKIP]
    
    # Init vship
    res = core.vship.SSIMULACRA2(src, enc, numStream = 3)
    
    start = time.time()
    frames = [0]
    duration = 10.0
    
    def p(n, t):
        frames[0] = n
        elapsed = time.time() - start
        if elapsed > duration: raise KeyboardInterrupt
        
    try:
        clip_async_render(res, outfile=None, progress=p)
    except:
        pass
        
    elapsed = time.time() - start
    fps = frames[0] / elapsed if elapsed > 0 else 0
    print(f"FPS:{{fps}}")
except Exception as e:
    print(f"ERROR:{{e}}")
"""
    try:
        res = subprocess.run(
            [sys.executable, "-c", bench_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=BASE_DIR,
        )
        for line in res.stdout.splitlines():
            if line.startswith("FPS:"):
                return float(line.split(":")[1])
    except:
        pass
    return 0


def benchmark_cpu_fssimu2(encoded_file):
    fssimu2_exe = shutil.which("fssimu2")
    if not fssimu2_exe:
        return 0, 1

    print("   Benchmarking CPU (fssimu2 - Single Worker)...", file=sys.stderr)

    fps_1, rss = _run_fssimu2_internal(
        1, encoded_file, duration=5, exe_path=fssimu2_exe
    )
    if fps_1 <= 0:
        return 0, 1

    opt_workers = calculate_optimal_count(fps_1, rss)

    print(f"   Benchmarking CPU (fssimu2 - {opt_workers} Workers)...", file=sys.stderr)
    fps_opt, _ = _run_fssimu2_internal(
        opt_workers, encoded_file, duration=10, exe_path=fssimu2_exe
    )

    return fps_opt, opt_workers


def _run_fssimu2_internal(workers, encoded_file, duration, exe_path):
    import numpy as np

    src_full = core.ffms2.Source(source=str(SAMPLE_FILE))
    enc_full = core.ffms2.Source(source=str(encoded_file))

    ref = src_full.resize.Bicubic(format=vs.RGB24, matrix_in_s="709")[::SKIP]
    dist = enc_full.resize.Bicubic(format=vs.RGB24, matrix_in_s="709")[::SKIP]

    total_frames = len(ref)

    def write_pam(frame, filepath):
        packed = np.dstack(
            (np.asarray(frame[0]), np.asarray(frame[1]), np.asarray(frame[2]))
        ).tobytes()
        header = (
            f"P7\nWIDTH {frame.width}\nHEIGHT {frame.height}\nDEPTH 3\nMAXVAL 255\nTUPLTYPE RGB\nENDHDR\n"
        ).encode()
        with open(filepath, "wb") as f:
            f.write(header)
            f.write(packed)

    def process_frame(n):
        r_path = TEMP_DIR / f"ref_{n}.pam"
        d_path = TEMP_DIR / f"dist_{n}.pam"
        try:
            write_pam(ref.get_frame(n), r_path)
            write_pam(dist.get_frame(n), d_path)
            # Linux: shell=False is usually safer/better if lists are used
            subprocess.run(
                [str(exe_path), str(r_path), str(d_path)],
                capture_output=True,
                check=True,
            )
        finally:
            try:
                r_path.unlink(missing_ok=True)
            except:
                pass
            try:
                d_path.unlink(missing_ok=True)
            except:
                pass
        return n

    start = time.time()
    frames = 0
    max_rss = 0
    test_count = min(500, total_frames)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(process_frame, n): n for n in range(test_count)}
            for f in concurrent.futures.as_completed(futs):
                f.result()
                frames += 1
                elapsed = time.time() - start
                prog = min(100.0, (elapsed / duration) * 100)
                sys.stderr.write(f"\r      Progress: {prog:.1f}% ")

                if frames % 5 == 0:
                    try:
                        max_rss = max(
                            max_rss, psutil.Process(os.getpid()).memory_info().rss
                        )
                    except:
                        pass

                if elapsed > duration:
                    ex.shutdown(wait=False, cancel_futures=True)
                    break
    except:
        sys.stderr.write("\n")
        return 0, 0

    sys.stderr.write("\n")
    elapsed = time.time() - start
    fps = frames / elapsed if elapsed > 0 else 0
    del ref, dist, src_full, enc_full
    return fps, max_rss


def benchmark_cpu_vszip(encoded_file):
    print("   Benchmarking CPU (vs-zip - Single Worker)...", file=sys.stderr)
    fps_1, rss = _run_vszip_internal(1, encoded_file, duration=5)
    if fps_1 <= 0:
        return 0, 1

    opt_workers = calculate_optimal_count(fps_1, rss)
    print(f"   Benchmarking CPU (vs-zip - {opt_workers} Workers)...", file=sys.stderr)
    fps_opt, _ = _run_vszip_internal(opt_workers, encoded_file, duration=10)

    return fps_opt, opt_workers


def _run_vszip_internal(workers, encoded_file, duration):
    if not hasattr(core, "vszip"):
        return 0, 0
    core.num_threads = workers

    src = core.ffms2.Source(source=str(SAMPLE_FILE)).resize.Bicubic(
        format=vs.RGB24, matrix_in_s="709"
    )[::SKIP]
    enc = core.ffms2.Source(source=str(encoded_file)).resize.Bicubic(
        format=vs.RGB24, matrix_in_s="709"
    )[::SKIP]

    try:
        res = core.vszip.SSIMULACRA2(src, enc)
    except:
        return 0, 0

    start = time.time()
    frames = [0]
    max_rss = [0]

    def p(n, t):
        frames[0] = n
        elapsed = time.time() - start
        prog = min(100.0, (elapsed / duration) * 100)
        sys.stderr.write(f"\r      Progress: {prog:.1f}% ")

        if n % 10 == 0:
            try:
                max_rss[0] = max(
                    max_rss[0], psutil.Process(os.getpid()).memory_info().rss
                )
            except:
                pass
        if elapsed > duration:
            raise KeyboardInterrupt

    try:
        clip_async_render(res, outfile=None, progress=p)
    except:
        pass

    sys.stderr.write("\n")
    elapsed = time.time() - start
    fps = frames[0] / elapsed if elapsed > 0 else 0
    del res, src, enc
    return fps, max_rss[0]


if __name__ == "__main__":
    try:
        cleanup_temp_files()
        encoded_file = run_fast_pass()
        if not encoded_file:
            raise RuntimeError("Fast pass failed")

        results = []

        # 1. Test vs-hip (GPU)
        fps_gpu = benchmark_gpu_vship(encoded_file)
        if fps_gpu > 0:
            print(f"   [vs-hip]        FPS: {fps_gpu:.2f}", file=sys.stderr)
            results.append(
                {"tool": "vs-hip", "variant": "gpu", "fps": fps_gpu, "workers": 1}
            )

        # 2. Test fssimu2
        fps_fs, w_fs = benchmark_cpu_fssimu2(encoded_file)
        if fps_fs > 0:
            print(
                f"   [fssimu2]       FPS: {fps_fs:.2f} | Workers: {w_fs}",
                file=sys.stderr,
            )
            results.append(
                {"tool": "fssimu2", "variant": "cpu", "fps": fps_fs, "workers": w_fs}
            )

        # 3. Test vs-zip
        fps_zip, w_zip = benchmark_cpu_vszip(encoded_file)
        if fps_zip > 0:
            print(
                f"   [vs-zip]        FPS: {fps_zip:.2f} | Workers: {w_zip}",
                file=sys.stderr,
            )
            results.append(
                {"tool": "vs-zip", "variant": "cpu", "fps": fps_zip, "workers": w_zip}
            )

        if not results:
            print("All benchmarks failed. Defaulting to vs-zip.", file=sys.stderr)
            # Default to vs-zip as it's the safest on Linux
            with open(CONFIG_FILE, "w") as f:
                f.write("tool=vs-zip\nworkercount=4")
            sys.exit(0)

        # FIND WINNER
        winner = max(results, key=lambda x: x["fps"])
        print(f"\nWinner: {winner['tool']} | FPS: {winner['fps']:.2f}", file=sys.stderr)

        # WRITE CONFIG
        with open(CONFIG_FILE, "w") as f:
            f.write(f"tool={winner['tool']}\n")
            f.write(f"workercount={winner['workers']}\n")

    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        with open(CONFIG_FILE, "w") as f:
            f.write("tool=vs-zip\nworkercount=4")
    finally:
        cleanup_temp_files()
