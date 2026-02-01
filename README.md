# Auto-Boost-Av1an for Ubuntu

This guide explains how to set up and run Auto-Boost-Av1an on Ubuntu.

---

## Which Script Should I Choose?

Pick based on your content type and desired quality:

### 🎌 ANIME
| Script | Quality | Description |
|--------|---------|-------------|
| `run_linux_anime_crf30.sh` | **Standard** | ✅ Recommended starting point |
| `run_linux_anime_crf25.sh` | High | Higher quality, larger files |
| `run_linux_anime_crf18.sh` | Archival | Maximum quality, largest files |

### 🎬 LIVE ACTION / MOVIES / TV SHOWS
| Script | Quality | Description |
|--------|---------|-------------|
| `run_linux_live_crf30.sh` | **Standard** | ✅ Recommended starting point |
| `run_linux_live_crf25.sh` | High | Higher quality, larger files |
| `run_linux_live_crf18.sh` | Archival | Maximum quality, largest files |

### ⚽ SPORTS / FAST MOTION
| Script | Quality | Description |
|--------|---------|-------------|
| `run_linux_sports_crf33.sh` | Optimized | ✅ Best for high-motion content |

### 🚀 PROGRESSION BOOST (PER-SCENE OPTIMIZATION)
| Script | Quality | Description |
|--------|---------|-------------|
| `Progression-Boost-SSIMU2-anime.sh` | **Auto** | Analyzes each scene and optimizes settings for Anime |
| `Progression-Boost-SSIMU2-liveaction.sh` | **Auto** | Analyzes each scene and optimizes settings for Live Action |
> **Note:** Progression Boost uses SSIMULACRA2 metrics to target a visual quality score (Default: 82), adjusting bitrate (crf) on a per scene basis to target that quality score. It benchmarks your CPU/RAM on first run to set optimal workers.

> **TIP:** Start with CRF 30. If quality isn't sufficient, try CRF 25. For archival purposes, use CRF 18.

### What is CRF?
CRF stands for "Constant Rate Factor." It determines the balance between Video Quality and File Size:
- **Lower CRF** (e.g., 18) = Higher Quality, Larger File Size
- **Higher CRF** (e.g., 30) = Lower Quality, Smaller File Size

---

## Prerequisites

### Automatic Installation

For a detailed list of versions and software installed, see [DEPENDENCIES.md](DEPENDENCIES.md).


We have provided a script to automatically install all dependencies on Ubuntu/Debian.
This script needs to be run as root.

```bash
chmod +x install_deps_ubuntu.sh
sudo ./install_deps_ubuntu.sh
```

**Cleanup:**
If the installation fails or you want to undo the manual compilations (SVT-AV1, WWXD), you can run:
```bash
chmod +x cleanup_install.sh
sudo ./cleanup_install.sh
```

If you prefer to install manually, follow the steps below.

### 1. System Packages

Install basic tools, FFmpeg, and x264 (required for scene detection):

```bash
sudo apt update
sudo apt install -y ffmpeg x264 mkvtoolnix mkvtoolnix-gui python3 python3-pip git curl
```

### 2. VapourSynth

Install VapourSynth and its Python bindings.
For Ubuntu, you might need to add the `vs-repo` or use the default repositories if available (Ubuntu 24.04+ has newer versions).

```bash
sudo apt install -y vapoursynth libvapoursynth-dev python3-vapoursynth
```

### 3. Python Dependencies

Install the required Python packages:

```bash
pip3 install vsjetpack numpy rich vstools psutil
```

### 4. Av1an

The automatic installer uses the latest version from Git for feature parity.
Manual install:
```bash
cargo install --git https://github.com/rust-av/Av1an.git
```

### 5. fssimu2 (CPU Metrics)
The automated installer compiles this native Rust tool for identical Windows parity.
Manual install:
```bash
cargo install --git https://github.com/gianni-rosato/fssimu2.git
```

### 5b. vship / FFVship (GPU Metrics)
The automated installer compiles this from source for GPU-accelerated metrics.
Requires NVIDIA (CUDA) or AMD (HIP) drivers.
Manual install: *See [Line-fr/Vship](https://github.com/Line-fr/Vship)*


### 5. SVT-AV1

The automatic installer compiles **SVT-AV1-PSY** (Psycho-visual fork) with Clang and PGO/LTO optimizations for best quality and speed on Linux.
Manual install (Recommended Build Command):
```bash
git clone https://github.com/5fish/svt-av1-psy
cd svt-av1-psy
mkdir -p Build/linux && cd Build/linux
cmake ../.. -G"Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DSVT_AV1_PGO=ON -DSVT_AV1_LTO=ON
make -j $(nproc)
sudo make install
```
Ensure `SvtAv1EncApp` is in your PATH.

### 6. VapourSynth Plugins

The script relies on the following plugins:
1.  **FFMS2**: For video loading.
2.  **WWXD**: For scene detection (required by `Progressive-Scene-Detection.py`).
3.  **VSZIP**: For metrics calculation (fallback if `fssimu2` is missing).

**Install FFMS2:**
```bash
sudo apt install -y libffms2-4 libffms2-dev
# OR compile from source (recommended for latest ffmpeg support)
```

**Install WWXD (Critical Fix):**
You MUST link against the math library.
```bash
git clone https://github.com/dubhater/vapoursynth-wwxd.git
cd vapoursynth-wwxd
gcc -o libwwxd.so -fPIC -shared -O3 -Wall -Wextra -I. -I/usr/local/include/vapoursynth src/*.c -lm
sudo cp libwwxd.so /usr/local/lib/vapoursynth/
```

**Install VSZIP (Metrics):**
We recommend using the automated build script provided in the repository.
```bash
git clone https://github.com/dnjulek/vapoursynth-zip.git vszip
cd vszip/build-help
chmod +x build.sh
./build.sh
# Ensure the plugin is in your VapourSynth path (e.g., /usr/local/lib/vapoursynth)
sudo cp ../zig-out/lib/libvszip.so /usr/local/lib/vapoursynth/
```

*Alternatively, you can install the `fssimu2` binary and place it in your PATH to avoid needing `vszip`.*


## Verification

To verify that the installation was successful, run the following commands:

```bash
# Check Core Tools
ffmpeg -version | head -n 1
mkvmerge --version
python3 --version
mediainfo --version

# Check VapourSynth
vspipe --version
python3 -c "import vapoursynth; print(f'VapourSynth Core: {vapoursynth.core.version()}')"

# Check Encoders
av1an --version
SvtAv1EncApp --help | grep "SVT"

# Check Metrics Tools
zig version
fssimu2 --version || echo "fssimu2 not installed (optional - will use vs-zip fallback)"
FFVship --help | head -n 1 || echo "FFVship (GPU) not installed"

# Check VapourSynth Plugins
python3 -c "from vapoursynth import core; print('WWXD:', hasattr(core, 'wwxd')); print('VSZIP:', hasattr(core, 'vszip'))"
```
## Usage

### 3. Usage

1.  Place your source files (e.g., `.mkv` or `.mp4`) into the `Input/` folder.
    *   *Note: The script will create this folder automatically if it doesn't exist.*
    *   *Note: Files do NOT need to be renamed to `*-source.mkv` anymore.*
2.  Make the scripts executable (if not already):
    ```bash
    chmod +x run_linux_anime_*.sh
    chmod +x run_linux_live_*.sh
    ```
3.  Run the script variant of your choice.
    *   Your final encoded files will appear in the `Output/` folder.
We provide variants based on content type (Anime vs Live Action) and quality. All scripts support **Auto-BT.709 Detection**.

**Anime Variants:**
*   **Standard (CRF 30)**: `./run_linux_anime_crf30.sh` - Balanced speed/quality (Tune 3).
*   **High (CRF 25)**: `./run_linux_anime_crf25.sh` - Slower, Tune 0.
*   **Highest (CRF 18)**: `./run_linux_anime_crf18.sh` - Aggressive boosting.

**Live Action Variants (Auto-Crop Enabled):**
*   **Standard (CRF 30)**: `./run_linux_live_crf30.sh` - Auto-crop, Tune 3.
*   **High (CRF 25)**: `./run_linux_live_crf25.sh` - Tune 3, Variance Boost 2.
*   **Highest (CRF 18)**: `./run_linux_live_crf18.sh` - Maximum fidelity.

**Sports / High-Motion Content:**
*   **Low Quality (CRF 33)**: `./run_linux_sports_crf33.sh` - Optimized for high-motion content with extra temporal filtering.

The script will:
1.  Detect Scene Changes.
2.  Start Av1an with the optimized parameters.
3.  Automatically calculate worker count based on your hardware (on first run).
4.  Run Auto-Boost-Av1an (Fast Pass -> Metrics -> Zones -> Final Encode).
5.  Mux audio/subtitles back.
6.  Tag the output file.
7.  Cleanup temporary files.
8.  Final outputs are in the `Output/` folder.

## Audio Encoding (Standalone)

We include an `audio-encoding/` folder for batch audio conversion workflows:

| Script | Description |
|--------|-------------|
| `encode-ac3-audio.sh` | Converts audio tracks to **AC3** (Dolby Digital) - for legacy devices |
| `encode-eac3-audio.sh` | Converts audio tracks to **EAC3** (Dolby Digital Plus) - recommended |
| `encode-eac3-audio.sh` | Converts audio tracks to **EAC3** (Dolby Digital Plus) - recommended |
| `encode-opus-audio.sh` | Converts audio tracks to **Opus** - best quality/size ratio |

> **2.1 Channel Support:** `encode-opus-audio.sh` (192k) and `encode-ac3-audio.sh` (320k) now support 2.1 channel detection and optimization.


*Usage:*
```bash
cd audio-encoding
# Place your .mkv files in this folder
./encode-eac3-audio.sh
```

Settings files (`settings-encode-*.txt`) control bitrates per channel configuration.

## Extras (Linux)

We include an `extras/` folder with helper scripts for advanced workflows:

| Script | Description |
|--------|-------------|
| `encode-opus-audio.sh` | Legacy audio encoding (use `audio-encoding/` instead) |
| `lossless-intermediary.sh` | Converts video to lossless 10-bit x265 intermediates |
| `compare.sh` | Generates comparison screenshots via `comp.py` |
| `light-denoise.sh` | Applies DFTTest denoise + x265 lossless encoding |
| `light-denoise-nvidia.sh` | GPU-accelerated NVEncC denoise (NVIDIA required) |
| `forced-aspect-remux.sh` | Copies aspect ratio from source to encoded output |
| `disk-usage.sh` | Reports disk usage (Linux replacement for NTFS compress) |

*Usage:*
```bash
cd extras
./light-denoise.sh
```

## Prefilter (Deband Scripts)

The `prefilter/` folder contains scripts for applying deband filters before encoding:

| Script | Description |
|--------|-------------|
| `nvidia-deband.sh` | NVIDIA GPU deband using NVEncC + libplacebo |
| `x265-lossless-deband.sh` | CPU deband using VapourSynth + x265 lossless |

Edit `prefilter/settings.txt` to customize filter settings.

*Requirements:*
- For NVIDIA scripts: NVEncC installed and in PATH
- For x265 scripts: VapourSynth with placebo plugin, x265

## Troubleshooting

-   **Missing Tools**: Ensure `av1an`, `SvtAv1EncApp`, `ffmpeg`, `mkvmerge`, `mkvpropedit` are in your PATH.
-   **VapourSynth Errors**: Ensure you have the required plugins (`ffms2`) installed and accessible to VapourSynth.
-   **Permissions**: Ensure you have write permissions in the folder.

## Files Required

If you are moving this project to a Linux machine, you only need the following files. You can ignore the `VapourSynth` folder and the `.exe` files in `tools/`.

**Root Directory:**
-   `Auto-Boost-Av1an.py`
-   `run_linux_anime_crf30.sh` (and all other .sh variants)
-   `README.md` (renamed to README_LINUX.md if distributing standalone)

**Tools Directory (`tools/`):**
-   `tools/dispatch.py` (New)
-   `tools/cropdetect.py` (auto-crop support)
-   `tools/ac3.py` (AC3 audio encoder)
-   `tools/eac3.py` (EAC3 audio encoder)
-   `tools/opus.py` (Opus audio encoder)
-   `tools/forced-aspect-remux.py` (aspect ratio fixer)
-   `tools/light-denoise-nvencc.py` (NVIDIA GPU denoise)
-   `tools/light-denoise-x265-lossless.py` (CPU denoise)
-   `tools/detect_grainy_flashbacks-beta.py` (flashback detection)
-   `tools/comp.py` (video comparison tool)
-   `tools/Progressive-Scene-Detection.py`
-   `tools/cleanup.py`
-   `tools/mux.py`
-   `tools/rename.py`
-   `tools/tag.py`
-   `tools/workercount.py`
-   `tools/sample.mkv`
-   `tools/iso200-grain.tbl`

*Note: The Windows binaries (av1an.exe, mkvmerge.exe, etc.) and the VapourSynth folder are NOT needed on Linux.*

## Code Modification Log

To support Linux, the following changes were made to the original codebase:
- **Automated Installer**: `install_deps_ubuntu.sh` automates the entire setup (System packages, VapourSynth, Av1an, SVT-AV1-PSY, WWXD, VSZIP).
    - *Note*: **VSZIP** (VapourSynth-ZIP) plugin and its dependency (Zig compiler) are now **automatically downloaded and installed** by the script.
- **Code Adaptation**: Python scripts were modified to use `shutil.which` for finding executables (`av1an`, `mkvmerge`, etc.) instead of hardcoded Windows paths.
- **Path Handling**: Windows-style paths (backslashes) were replaced or handled using Python's cross-platform `pathlib` or `os.path` where necessary.

### 1. `Auto-Boost-Av1an.py`
-   **Tool Path Resolution**: Modified to use `platform.system()` to detect the OS.
    -   **Windows**: Continues to use relative paths to the portable `tools\` folder (e.g., `tools\av1an\av1an.exe`).
    -   **Linux**: Uses `shutil.which()` to find `av1an` and `fssimu2` in the system PATH.

### 2. `tools/mux.py` & `tools/tag.py` & `tools/dispatch.py`
-   **MKVToolNix Paths**: Modified to use `platform.system()` and `shutil.which()`.
    -   **Windows**: Uses bundled `tools\MKVToolNix\mkvmerge.exe` and `mkvpropedit.exe`.
    -   **Linux**: Expects `mkvmerge` and `mkvpropedit` to be installed and available in the system PATH.
-   **Batch Detection (`tag.py`)**: Updated `get_active_batch_filename` to detect the new `sh-used-run.sh.txt` marker file created by the Linux shell script.
-   **Dispatch (`dispatch.py`)**: Ported to utilize linux `mediainfo` for BT.709 detection and inject parameters to `Auto-Boost-Av1an.py`.

### 3. New Files
-   **`run_linux_crf30.sh`** (and variants): Bash scripts created to verify worker count, rename files, run scene detection, execute the main Python script (via dispatch), and perform muxing/tagging/cleanup. Replaces `batch.bat` and others on Linux.
-   **`README_LINUX.md`**: This documentation file.
