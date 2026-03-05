# Auto-Boost-Av1an Dependencies (Linux)

This project relies on the following specific versions and forks of software. The `install_deps_ubuntu.sh` script installs these automatically.

## Core Tools

| Software | Version/Branch | Source / Notes |
| :--- | :--- | :--- |
| **Av1an** | Latest Git (Master) | [rust-av/Av1an](https://github.com/rust-av/Av1an) |
| **SVT-AV1-PSY** | Latest Git (main) | [5fish/svt-av1-psy](https://github.com/5fish/svt-av1-psy) <br> *Built with Clang, PGO, LTO, AVX512, NATIVE.* |
| **VapourSynth** | Latest Git (Master) | [vapoursynth/vapoursynth](https://github.com/vapoursynth/vapoursynth) |
| **FFmpeg** | Repository Version | Standard Ubuntu/Debian Repos (`apt install ffmpeg`) |
| **MKVToolNix** | Repository Version | Standard Ubuntu/Debian Repos (`mkvmerge`, `mkvpropedit`) |
| **x265** | Repository Version | CLI Tool (`apt install x265`) for Lossless Intermediary |
| **Opus Tools** | Repository Version | `opusenc` (`apt install opus-tools`) |
| **xclip** | Repository Version | Clipboard support for `comp.py` (`apt install xclip`) |
| **fssimu2** | Latest Git (Main) | [gianni-rosato/fssimu2](https://github.com/gianni-rosato/fssimu2) <br> *Metrics Tool (Zig Build, supports x86_64 & aarch64).* |
| **vship / FFVship** | Latest Git (Main) | [Line-fr/Vship](https://github.com/Line-fr/Vship) <br> *GPU Metrics Tool (CUDA/HIP)* |
| **NVEncC** | Manual Install | [rigaya/NVEnc](https://github.com/rigaya/NVEnc) <br> *Optional: NVIDIA GPU denoise tool* |
| **oxipng** | Latest Crates.io | `cargo install oxipng` <br> *Lossless PNG compression for comparison shots.* |

## VapourSynth Plugins

| Plugin | Version/Branch | Source | Notes |
| :--- | :--- | :--- | :--- |
| **FFMS2** | **Branch 5.0** | [FFMS/ffms2](https://github.com/FFMS/ffms2) | Pinned to 5.0 for FFmpeg 6.x compatibility. |
| **WWXD** | Latest Git | [dubhater/vapoursynth-wwxd](https://github.com/dubhater/vapoursynth-wwxd) | *Scene Detection*. Linked with `-lm`. |
| **VSZIP** | Latest Git | [dnjulek/vapoursynth-zip](https://github.com/dnjulek/vapoursynth-zip) | *Metrics (SSIMULACRA2/XPSNR)*. Built with Zig 0.15.2. |
| **SubText** | Latest Git | [vapoursynth/subtext](https://github.com/vapoursynth/subtext) | *Subtitles*. Required by `comp.py`. |

## Python Libraries (pip)

*   `vsjetpack`
*   `vstools`
*   `numpy`
*   `rich`
*   `psutil`
*   `anitopy`
*   `pyperclip`
*   `requests`
*   `requests_toolbelt`
*   `natsort`
*   `colorama`
*   `wakepy` (prevent system sleep during encoding)
*   `vsdenoise` (included in vsjetpack - DFTTest wrapper)

## Build Tools

*   **Rust**: Stable (via rustup)
*   **Zig**: **Latest Stable** (Handled automatically by VSZIP `build.sh`)
*   **mkvtoolnix-gui** (for mkvpropedit/mkvmerge)
*   **mediainfo** (CLI version, for BT.709 auto-detection)
*   **Git, CMake, Clang, NASM/YASM** (Build essentials)
