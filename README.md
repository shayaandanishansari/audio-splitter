# Audio Splitter

A desktop GUI application for visually splitting audio files at user-defined points. Load an audio file, see the waveform, drag split markers to fine-tune cut positions, and export the result as separate chunk files. Transcription runs automatically in the background using a local Whisper model — no API key needed.

Built with **PySide6** for a native desktop experience.

---

## Features

- **Visual waveform display** — full audio waveform with a gradient visualization
- **Draggable split markers** — freely position markers to define exact cut points; no snapping, full manual control
- **Live playhead** — red playhead moves in real-time during playback so you can preview before cutting
- **Timer display** — shows the selected marker's timestamp, or the playhead time when no marker is selected
- **Linked chunk/duration controls** — set number of output chunks or target duration per chunk (HH/MM/SS); both stay in sync and redistribute markers automatically
- **Auto-transcription** — transcript generated in the background on file load using a local Whisper model; saved as `<stem>.txt` alongside the audio file
- **Reset** — one click restores evenly-spaced markers after manual adjustments
- **Non-destructive splitting** — ffmpeg stream copy means no re-encoding; splits are instant and bit-perfect
- **Format preservation** — output format always matches the input (MP3 → MP3, WAV → WAV)

---

## Screenshot

*(Add a screenshot or GIF here once available)*

---

## Requirements

- Python **3.13+**
- `ffmpeg` installed on your system (`winget install ffmpeg` on Windows)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/audio-splitter.git
cd audio-splitter

# Create a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Pre-download the Whisper model (recommended)

On first use, faster-whisper downloads the `base` model (~150MB). Run this once to cache it before launching the app:

```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
```

After this, transcription works fully offline.

---

## Usage

```bash
python main.py
```

1. Click **📄 File** to select an audio file (MP3 or WAV)
2. The waveform appears and transcription starts automatically in the background
3. Adjust **Chunks** or **Duration (HH/MM/SS)** to set split points — markers are placed evenly
4. **Drag markers** left or right to fine-tune exact cut positions
5. Use **▶ / ⏸** to preview audio and verify marker positions
6. Click **↺ Reset** to restore markers to their evenly-spaced defaults at any time
7. Click **✓** to split and export — files are saved into a subfolder in the output directory

### Output structure

```
<output_folder>/
└── <audio_stem>/
    ├── <stem>_001.mp3
    ├── <stem>_002.mp3
    └── ...
```

The output folder defaults to the same directory as the input file. You can override it via the **📁 Output Folder** button.

### Transcription

When a file is loaded, a transcript is automatically generated using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — entirely local, no API key, no internet required after the initial model download.

Saved alongside the audio as `<stem>.txt`:

```
[00:00.00] Hello everyone, welcome back to the podcast.
[00:04.83] Today we're going to be talking about something really interesting.
[00:09.12] Let's get into it.
```

Transcription always outputs in the **original language** of the audio (no auto-translation).

Status is shown in the UI: `⏳ Loading audio...` → `⏳ Transcribing...` → `✓ Transcript saved → filename.txt`

---

## Building a Standalone Executable

```bash
pip install pyinstaller
pyinstaller build.spec
```

Output: `dist/AudioSplitter.exe` — fully self-contained, no Python installation required on the target machine.

Note: ffmpeg must still be available on the target machine, or bundled manually via the `build.spec` `binaries` field.

---

## Architecture

```
audio_splitter/
├── main.py                  # Entry point
├── core/                    # UI-agnostic — no PySide6 imports
│   ├── audio.py             # Audio loading and waveform extraction (ffmpeg + soundfile + numpy)
│   ├── player.py            # Playback engine (sounddevice)
│   ├── splitter.py          # Splitting logic (ffmpeg subprocess, stream copy)
│   └── transcriber.py       # Whisper transcription, singleton model, saves <stem>.txt
├── ui/
│   ├── main_window.py       # Root window, background workers, signal wiring
│   ├── waveform_widget.py   # Custom QPainter widget — waveform, markers, playhead
│   ├── controls_bar.py      # Play/pause, timer, reset, confirm
│   └── input_panel.py       # File/folder pickers, chunks/duration controls
├── utils/
│   └── time_format.py       # Timestamp formatting (seconds → MM:SS.cs)
├── build.spec               # PyInstaller spec
├── CLAUDE.md                # Full project brief and agent API design
└── LICENSE.md               # LM Stick Non-Commercial License
```

All heavy operations (file loading, transcription, splitting) run on background QThreads — the UI never freezes.

---

## Tech Stack

| Component | Library |
|---|---|
| GUI Framework | [PySide6](https://pypi.org/project/PySide6/) (LGPL) |
| Audio Decode & Split | [ffmpeg](https://ffmpeg.org/) (LGPL/GPL) |
| Waveform & Playback | [sounddevice](https://pypi.org/project/sounddevice/) + [soundfile](https://pypi.org/project/soundfile/) + [numpy](https://pypi.org/project/numpy/) |
| Transcription | [faster-whisper](https://pypi.org/project/faster-whisper/) (MIT) |
| Packaging | [PyInstaller](https://pypi.org/project/pyinstaller/) |

---

## Planned

- Agent-usable CLI (`cli.py`) and Python API (`agent_api.py`) — see `CLAUDE.md` for full design
- Intelligent splitting: agent reads transcript and reasons about natural split points rather than equal-duration chunks

---

## License

LM Stick Non-Commercial License — see [LICENSE.md](LICENSE.md) for full terms.

For commercial use inquiries: `shayaan0303@gmail.com`
