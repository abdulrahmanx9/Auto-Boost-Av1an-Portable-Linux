# Auto-Boost-Av1an Extras (Linux)

This folder contains helper scripts for additional workflows.

**Setup:** Make sure to run `chmod +x *.sh` before executing any scripts.

## Comparison Tools

| Script | Description |
|--------|-------------|
| `compare.sh` | Creates a slow.pics comparison link for your videos (not shared on slow.pics homepage) |
| `vspreview.sh` | Opens a local preview window to view video files frame-by-frame. Use for comparing quality locally or finding frame numbers for zones. Controls: Press 1,2,3 to switch videos, Ctrl+MouseWheel to zoom |

## File Fixing & Preparation

| Script | Description |
|--------|-------------|
| `simple-remux.sh` | Remuxes video/audio/subs into a clean MKV container without re-encoding |
| `lossless-intermediary.sh` | Converts troublesome video into a lossless x265 MKV intermediate |
| `forced-aspect-remux.sh` | Copies aspect ratio from source file to encoded file |
| `add-subtitles.sh` | Muxes subtitles (.ass/.srt) and fonts (.ttf/.otf) into your MKV files |

## Video Processing Scripts

| Script | Description |
|--------|-------------|
| `light-denoise.sh` | Applies DFTTest denoise via VapourSynth + x265 lossless encoding |
| `light-denoise-nvidia.sh` | GPU-accelerated denoise using NVEncC (requires NVIDIA GPU) |

## Audio Processing Scripts

| Script | Description |
|--------|-------------|
| `encode-opus-audio.sh` | Batch audio re-encoding to Opus format |

> **Note:** For standalone audio encoding, see the `audio-encoding/` folder in the root directory which includes AC3, EAC3, and Opus encoders with configurable bitrates and **new 2.1 channel support**.

## Testing & Extras

| Script | Description |
|--------|-------------|
| `create-sample.sh` | Creates a 90-second sample from a video file for testing encode settings (takes clip from 03:00-04:30) |
| `disk-usage.sh` | Reports disk usage for tools folders (Linux replacement for NTFS compress) |

## Usage Notes

### add-subtitles.sh
- **Single File Mode:** Place 1 MKV and subtitle file(s) named with the language (e.g., "French.ass")
- **Batch Mode:** Rename files using S01E01 format for automatic matching
- **Fonts:** Any .ttf/.otf files found will be attached to ALL MKVs processed

### vspreview.sh
- Useful for finding specific frame numbers when creating zones.txt files
- Press number keys 1-9 to switch between loaded video files
- Works with multiple MKV files at once for easy comparison

## Requirements

- **simple-remux.sh**: mkvtoolnix
- **create-sample.sh**: mkvtoolnix
- **add-subtitles.sh**: mkvtoolnix
- **vspreview.sh**: VapourSynth, FFMS2, SubText plugin, vspreview
- **light-denoise.sh**: VapourSynth, vsdenoise, x265, mkvtoolnix
- **light-denoise-nvidia.sh**: NVEncC (from [rigaya/NVEnc](https://github.com/rigaya/NVEnc)), mkvtoolnix
- **lossless-intermediary.sh**: VapourSynth, x265, mkvtoolnix
- **forced-aspect-remux.sh**: mkvtoolnix
- **compare.sh**: VapourSynth, FFMS2, SubText plugin

## Notes

- `compress-folders` functionality is Windows-only (uses NTFS compression).
- For filesystem-level compression on Linux, consider **btrfs** or **zfs**.
- NVEncC requires an NVIDIA GPU and must be manually installed from GitHub releases.
