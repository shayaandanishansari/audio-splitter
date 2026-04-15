# Installation & Build Guide

This guide covers running Audio Splitter from source, building a standalone executable, and how the CI pipeline produces release binaries.

---

## Quick Start (From Source)

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/audio-splitter.git
cd audio-splitter
```

### 2. Set up a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python main.py
```

---

## Runtime Dependencies

Audio Splitter relies on two external components that are **not** Python packages:

### 1. `ffmpeg` — Required for audio loading and export

`pydub` (the library handling audio decode and splitting) shells out to the `ffmpeg` binary. Without it, MP3/WAV loading and chunk export will fail.

**Installing ffmpeg:**

| Platform | Command |
|---|---|
| Windows | `winget install ffmpeg` or `choco install ffmpeg` |
| macOS | `brew install ffmpeg` |
| Ubuntu/Debian | `sudo apt install ffmpeg` |
| Arch Linux | `sudo pacman -S ffmpeg` |

Verify installation:
```bash
ffmpeg -version
```

### 2. Faster-Whisper model — Required for transcription

When you load an audio file, transcription starts automatically in the background. This uses the [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) library, which downloads the Whisper model weights on first use.

- **Default model**: `base` (~140 MB download)
- **Where it's cached**:
  - Windows: `%LOCALAPPDATA%\huggingface\hub\`
  - Linux: `~/.cache/huggingface/hub/`
  - macOS: `~/Library/Caches/huggingface/hub/`
- **After the first download**: transcription works fully offline

**Pre-download the model (optional but recommended):**

Run this once before launching the app to cache the model ahead of time:

```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
```

You'll see progress bars as the model downloads. After that, transcription starts instantly.

**Using a different model size:**

Edit the `DEFAULT_MODEL` constant in `core/transcriber.py`:

| Model | Size | Speed | Accuracy |
|---|---|---|---|
| `tiny` | ~75 MB | Fastest | Lower |
| `base` | ~140 MB | Fast | Good (default) |
| `small` | ~460 MB | Moderate | Better |
| `medium` | ~1.5 GB | Slow | Best |

Larger models are slower but produce more accurate transcripts, especially for noisy audio or accented speech.

---

## Building a Standalone Executable

### With PyInstaller (manual build)

```bash
pip install pyinstaller
pyinstaller build.spec
```

Output: `dist/AudioSplitter.exe` (Windows) or `dist/AudioSplitter` (Linux/macOS)

This binary includes all Python dependencies and UI assets. However:

- **`ffmpeg` is NOT bundled** — it must be available on the target system's PATH, or placed alongside the `.exe`
- **Whisper model is NOT bundled** — it downloads at first transcription run

### Bundling ffmpeg (recommended for releases)

To make the `.exe` fully self-contained for the splitting feature, bundle a static `ffmpeg` binary:

1. Download a static ffmpeg build for your platform (e.g., from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/))
2. Place `ffmpeg.exe` in the project root (or a `bin/` folder)
3. Update `build.spec` to include it in the `datas` or `binaries` field:

```python
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[('ffmpeg.exe', '.')],  # bundles ffmpeg into the .exe
    datas=[('assets', 'assets')],
    # ...
)
```

4. In your code, point `pydub` to the bundled ffmpeg:

```python
import sys
from pathlib import Path
from pydub import AudioSegment

if getattr(sys, 'frozen', False):
    # Running as compiled .exe — use bundled ffmpeg
    ffmpeg_path = Path(sys._MEIPASS) / 'ffmpeg.exe'
    AudioSegment.converter = str(ffmpeg_path)
```

5. Rebuild: `pyinstaller build.spec --clean`

The resulting `.exe` will work for splitting without requiring a system ffmpeg. Transcription still downloads the Whisper model at runtime (expected behavior).

---

## CI/CD — Automatic Builds on Every Push

Audio Splitter uses GitHub Actions (`.github/workflows/build-release.yml`) to build release binaries automatically on every push to `main`.

### How it works

1. **Version tag** — generates a dev version like `v0.1.0-dev-20260415-abc1234`
2. **Windows build** — runs on `windows-latest`, installs ffmpeg via `choco`, builds with PyInstaller
3. **Linux build** — runs on `ubuntu-latest`, installs ffmpeg via `apt`, builds with PyInstaller
4. **Release** — creates or updates a GitHub Release with the binaries as downloadable assets

### What's in the release

| File | Platform | Notes |
|---|---|---|
| `AudioSplitter.exe` | Windows | Double-click to run. Requires system ffmpeg for full functionality. |
| `AudioSplitter` | Linux | Run with `./AudioSplitter`. Requires `chmod +x` and system ffmpeg. |

### Building locally with the same config

The CI installs ffmpeg before building, so the build environment matches a real user setup. If you want to test locally:

```bash
# Install ffmpeg first
# Then build
pip install -r requirements.txt pyinstaller
pyinstaller build.spec --clean
```

---

## Troubleshooting

### "ffmpeg not found" or audio export fails

- Verify ffmpeg is installed: `ffmpeg -version`
- If using a bundled build, check that `ffmpeg.exe` is in the same directory as the `.exe`
- On Windows, try adding ffmpeg to your PATH or restarting the app

### Transcription never starts or crashes

- Check internet connection (model download needs network)
- Pre-download the model manually (see above) to verify it works
- Check disk space — the `base` model needs ~140 MB cached + ~300 MB temporary

### Windows SmartScreen warning on the .exe

- This is normal for unsigned builds
- Click **"More info" → "Run anyway"**
- The app is safe — it's just Windows flagging an unknown publisher

### App crashes on startup with no error

- Run from a terminal to see the traceback:
  ```bash
  dist\AudioSplitter.exe
  ```
- Common causes: missing Visual C++ redistributable (install [VCRedist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)), or corrupted Whisper model cache

---

## From Source vs Standalone

| Feature | From Source | Standalone .exe |
|---|---|---|
| Requires Python | Yes (3.12+) | No |
| Requires ffmpeg | Yes | Yes (unless bundled) |
| Whisper model | Downloads on first run | Downloads on first run |
| Editable code | Yes | No |
| Quick to start dev | `pip install -r requirements.txt` | N/A |
| Best for | Development, customization | Distribution, end users |
