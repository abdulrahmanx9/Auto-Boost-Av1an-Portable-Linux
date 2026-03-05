# Audio Encoding Tools (Linux)

This folder contains batch scripts for converting audio tracks to various formats independently of video encoding.

## Features

- **Batch Processing**: Converts all audio tracks in `.mkv` files within this folder.
- **Configurable Bitrates**: Uses `settings-encode-*-audio.txt` files to define quality per channel count.
- **2.1 Channel Support** (New in v1.51/v1.9.0-linux): Specifically detects 3-channel audio (2.1) and applies optimized bitrates.

## Scripts

| Script | Format | Description |
|--------|--------|-------------|
| `encode-opus-audio.sh` | **Opus** | High efficiency, widely supported. Default 2.1 bitrate: **192k**. |
| `encode-ac3-audio.sh` | **AC3** | Dolby Digital. Maximum compatibility. Default 2.1 bitrate: **320k**. |
| `encode-eac3-audio.sh` | **EAC3** | Dolby Digital Plus. Better quality/size than AC3. |

## Configuration

You can customize the target bitrates by editing the corresponding text file:

- `settings-encode-opus-audio.txt`
- `settings-encode-ac3-audio.txt`
- `settings-encode-eac3-audio.txt`

### Example Settings (Opus)

```ini
Above 5.1=320
5.1=256
2.1=192
2.0=128
```

- **Above 5.1**: 7.1, 6.1, etc.
- **5.1**: Standard Surround
- **2.1**: Stereo + LFE (New detection logic)
- **2.0**: Stereo / Mono

## Usage

1. Place your `.mkv` files containing audio tracks into this folder.
2. Run the desired script:
   ```bash
   chmod +x encode-opus-audio.sh
   ./encode-opus-audio.sh
   ```
3. Output files will be created in the `Output` subfolder (or alongside source depending on script logic).
