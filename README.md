# Audio Splitter

A desktop GUI application for visually splitting audio files at user-defined points. Load an audio file, see the waveform, drag split markers to fine-tune cut positions, and export the result as separate chunk files.

Built with **PySide6** for a native, cross-platform desktop experience.

---

## Features

- **Visual waveform display** — see the full audio waveform with a gradient-powered visualization
- **Draggable split markers** — freely position black markers to define exact cut points; no snapping, full manual control
- **Live playhead** — a red playhead moves in real-time during playback so you can preview before cutting
- **Linked chunk/duration controls** — set the number of output chunks or target duration per chunk; both stay in sync and redistribute markers evenly
- **Auto-transcription** — when a file is loaded, a transcript is automatically generated in the background using a local Whisper model (no API key needed)
- **Reset to defaults** — one click restores evenly-spaced markers after manual adjustments
- **Format preservation** — output format always matches the input (MP3 stays MP3, WAV stays WAV)

---

## Screenshot

*(Add a screenshot or GIF here once available)*

---

## Installation

### Prerequisites

- Python **3.10+**
- `ffmpeg` must be installed on your system (required by `pydub` for MP3 support)

### Setup

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

---

## Usage

```bash
python main.py
```

1. Click **📄 File** to select an audio file (MP3 or WAV).
2. The waveform appears. Split markers are placed evenly based on the default chunk count.
3. **Drag markers** left or right to fine-tune split points.
4. Use **Play ▶ / Pause ⏸** to preview audio and check marker positions.
5. Adjust **Chunks** or **Duration** to redistribute markers automatically.
6. Click **✓** to split and export chunks to the output folder.
7. Use **↺ Reset** to restore markers to their evenly-spaced defaults.

### Output

Files are saved into a subfolder inside the output directory, named after the source file:

```
<output_folder>/<audio_stem>/<stem>_001.mp3
<output_folder>/<audio_stem>/<stem>_002.mp3
...
```

---

### Transcription

When an audio file is loaded, a transcript is **automatically generated in the background** using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — no API key, runs entirely locally.

The transcript is saved alongside the audio file as `<stem>.txt`:

```
[00:00.00] Hello everyone, welcome back to the podcast.
[00:04.83] Today we're going to be talking about something really interesting.
[00:09.12] Let's get into it.
```

A status indicator in the UI shows the transcription progress: `⏳ Transcribing...` → `✓ Transcript saved` → `⚠ Transcription failed`. The model runs on a background thread so the UI never freezes.

---

## Building a Standalone Executable

```bash
pip install pyinstaller
pyinstaller build.spec
```

The resulting `.exe` will be in the `dist/` folder. No Python installation is required to run it.

---

## Architecture

```
audio_splitter/
├── main.py                  # Entry point
├── core/
│   ├── audio.py             # Audio loading, waveform extraction (numpy/soundfile)
│   ├── player.py            # Playback engine (sounddevice)
│   ├── splitter.py          # Splitting logic (pydub)
│   └── transcriber.py       # faster-whisper transcription, saves <stem>.txt alongside audio
├── ui/
│   ├── main_window.py       # Root window, layout, signal wiring
│   ├── waveform_widget.py   # Custom widget — waveform painting, marker dragging
│   ├── controls_bar.py      # Play/pause, timer, reset, confirm
│   └── input_panel.py       # File/folder pickers, chunks/duration controls
├── utils/
│   └── time_format.py       # Timestamp formatting
└── build.spec               # PyInstaller spec
```

**Design principle:** `core/` is completely UI-agnostic — no PySide6 imports. All communication between layers happens through Qt signals.

---

## Tech Stack

| Component | Library |
|---|---|
| GUI Framework | [PySide6](https://pypi.org/project/PySide6/) |
| Audio Processing | [pydub](https://pypi.org/project/pydub/) |
| Playback | [sounddevice](https://pypi.org/project/sounddevice/) |
| WAV Loading | [soundfile](https://pypi.org/project/soundfile/) |
| Transcription | [faster-whisper](https://pypi.org/project/faster-whisper/) |
| Numerical Ops | [numpy](https://pypi.org/project/numpy/) |
| Packaging | [PyInstaller](https://pypi.org/project/pyinstaller/) |

---

## License

This project uses PySide6 under the **LGPL** license.

---

## Contributing

Pull requests and issues are welcome. Please keep `core/` UI-agnostic and use Qt signals for cross-layer communication.
