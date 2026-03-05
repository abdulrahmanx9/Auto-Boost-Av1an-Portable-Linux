# Auto-Boost-Av1an Prefilter Scripts (Linux)

This folder contains prefiltering scripts for applying denoise, deband, and downscale filters 
before encoding with Auto-Boost-Av1an.

## Available Scripts

### Combined Prefilter Scripts (v1.49+)
These combined scripts support denoise, deband, AND downscaling based on settings.txt:

| Script | Description |
|--------|-------------|
| `nvidia-prefilter.sh` | Apply denoise/deband/downscale using NVEncC (NVIDIA GPU required) |
| `x265-prefilter.sh` | Apply denoise/deband/downscale using VapourSynth + x265 lossless |

### Legacy Deband-Only Scripts
- **nvidia-deband.sh**: Apply libplacebo deband filter using NVEncC
- **x265-lossless-deband.sh**: Apply placebo deband filter using VapourSynth and x265

## Configuration

Edit `settings.txt` to customize filter settings:

### NVIDIA Section
```ini
[NVIDIA]
nvidia-downscale=False
nvidia-downscale-filter=hermite
nvidia-downscale-resolution=1920x1080
nvidia-denoise=True
nvidia-denoise-filter=vpp_fft3d=sigma=0.2
nvidia-deband=True
nvidia-deband-threshold=1
nvidia-deband-radius=16
```

### x265 Section
```ini
[x265]
x265-downscale=False
x265-downscale-kernel=hermite
x265-downscale-resolution=1920x1080
x265-denoise=True
x265-denoise-filter=DFTTest().denoise(src, {0.00:0.30, ...}, planes=[0, 1, 2])
x265-deband=False
x265-deband-filter=core.placebo.Deband(src, threshold=2.0, planes=1)
```

### Available Downscale Kernels
- `hermite`: Hermite-weighted averaging (recommended for anime)
- `bilinear`: Bilinear (triangle) averaging
- `bicubic`: Bicubic interpolation
- `spline36`: Spline interpolation (recommended for live action)
- `lanczos`: Lanczos reconstruction
- `mitchell`: Mitchell-Netravalia cubic spline

## Usage

1. Place your `.mkv` files in this folder
2. Edit `settings.txt` to configure filters
3. Run the appropriate script:
   - `./nvidia-prefilter.sh` (GPU with full filtering)
   - `./x265-prefilter.sh` (CPU with full filtering)
4. Output files will be created with `_prefilter` suffix

## Upscale Protection

The scripts will automatically skip files if the target resolution is larger than
the source resolution (upscaling is not allowed).

## Requirements

### For NVIDIA scripts:
- NVEncC installed and in PATH (https://github.com/rigaya/NVEnc)
- FFmpeg installed (`sudo apt install ffmpeg`)
- MediaInfo installed (`sudo apt install mediainfo`)
- NVIDIA GPU with NVENC support

### For x265 scripts:
- VapourSynth installed with FFMS2 and placebo plugins
- vsdenoise and vstools Python packages
- x265 installed (`sudo apt install x265`)
- vspipe installed
- FFmpeg installed (`sudo apt install ffmpeg`)
- MediaInfo installed (`sudo apt install mediainfo`)
