# Audio Splitter — Project Brief

## Overview

A desktop GUI application that lets users load an audio file, visually set split points on a waveform, and export the audio as separate chunk files. The emphasis is on visual, interactive control over split points rather than blind equal-division splitting.

---

## Core Features

### File Selection
- User selects an input audio file via a **File** button
- Supported formats: **MP3, WAV only**
- Once selected, the button/area updates to show:
  - A small file icon
  - The filename (truncated if needed)
- Output format always matches input format (not configurable)

### Output Folder
- Defaults automatically to **the same directory as the input file**
- Output is written into a **subfolder** within that directory, containing all the split audio chunk files
- User can override the output location via an **Output Folder** button
- Once selected, the button/area updates to show:
  - A small folder icon
  - The folder path (truncated if needed)

---

## Waveform Viewer

- Displays the full audio waveform visually after a file is loaded
- Contains two types of markers:
  - **Red tape (playhead)**: indicates current playback position, moves during playback
  - **Black tapes (split markers)**: vertical lines marking where the audio will be cut

### Split Markers (Black Tapes)
- Variable number of markers, always = `number of chunks - 1`
  - e.g., 4 chunks → 3 black markers dividing the waveform into 4 segments
- **Freely draggable** — user can drag any marker left or right to fine-tune split points
- Initially placed at evenly spaced positions based on chunk count or duration input
- Repositioning a marker does not affect other markers
- Markers are labeled (1, 2, 3... from left to right) with a downward triangle indicator at the top

---

## Playback Controls

Located at the bottom of the waveform viewer:
- **Play** button — starts playback, red tape moves in real time
- **Pause** button — pauses playback at current position

---

## Timer Display

- Displays a timestamp (MM:SS or MM:SS.ms format)
- **If a black marker is selected**: shows the time position of that marker
- **If no marker is selected**: shows the current red playhead time
- Updates in real time during playback

---

## Chunk / Duration Controls

Two linked input controls, each with a **slider** and a **number input box**:

### Chunks
- Sets the number of output chunks (minimum: 2)
- Slider range: 2 to some reasonable max (e.g., 20 or based on audio length)
- Changing this recalculates and updates the Duration field
- Redistributes black markers evenly across the waveform

### Duration (per chunk)
- Sets the target duration of each chunk (in seconds)
- Changing this calculates how many chunks fit (`floor(total_duration / chunk_duration)`) and updates the Chunks field
- The **last chunk may be shorter** than the specified duration — this is expected and acceptable
- Redistributes black markers evenly across the waveform

**Linking behavior:**
- Both fields stay in sync when either is changed via slider or number input
- Dragging a marker manually does NOT update these fields (markers become free-form after manual adjustment)

---

## Reset Button

- Replaces the originally considered yin-yang icon
- Resets all black markers back to their **evenly spaced default positions** based on the current Chunks / Duration values
- Does not reset file or folder selection
- Useful after manually dragging markers and wanting to start over

---

## Confirm / Execute Button

- Green checkmark button
- Triggers the actual audio splitting operation
- Reads current marker positions (in seconds) and slices the audio file at those points
- Exports each segment as a separate file into the output folder
- Files named sequentially (e.g., `original_name_001.mp3`, `original_name_002.mp3`, etc.)

---

## UI Layout (as designed)

```
+-----------------------------------------------+
|              Audio Splitter                   |
|  [File icon + name]       [Output Folder]     |
|                           [Chunks | Duration] |
|  +-------------------------------------+      |
|  |  [waveform with markers]            |      |
|  |  1       2       3       4          |      |
|  |  |       |       |       |          |      |
|  |  ~~~~waveform visualization~~~~~    |      |
|  +-------------------------------------+      |
|  [Play] [Pause]   [Timer]   [Reset] [Confirm] |
+-----------------------------------------------+
```

---

## Technical Constraints & Decisions

- **Supported audio formats**: MP3, WAV (input and output)
- **Output format**: always matches input (no conversion)
- **Last chunk duration**: may be shorter than target — no special handling
- **Marker dragging**: free, no snapping to grid or beats
- **Marker redistribution**: only happens when Chunks or Duration fields change, not during drag
- **Default output location**: same directory as input file, in a subfolder

---

## Transcription

### Behavior
- Transcription fires **automatically in the background** the moment a file is loaded in the GUI — no user action required
- Uses **faster-whisper** (local, free, no API key) with the `base` model by default — fast enough for background use, good quality
- Transcript is saved as `<audio_stem>.txt` **in the same directory as the audio file**
  - e.g., `my_podcast.mp3` → `my_podcast.txt`
- A subtle status indicator in the UI shows: `⏳ Transcribing...` → `✓ Transcript saved` → `⚠ Transcription failed`
- Transcription runs in a QThread — never blocks the UI

### Transcript format
```
[00:00.00] Hello everyone, welcome back to the podcast.
[00:04.83] Today we're going to be talking about something really interesting.
[00:09.12] Let's get into it.
```

### Why same directory as audio
- Predictable — always findable without coordination
- An agent picking up the same file later can check for an existing transcript before re-running Whisper
- Keeps audio + transcript as a natural pair

### Agent path (separate, future)
- Agent calls `transcribe(file)` explicitly when needed
- Agent manages its own file paths and state
- Can skip transcription entirely if a `.txt` already exists alongside the audio

---

## Tech Stack

- **GUI Framework**: PySide6 (Qt for Python — LGPL, full custom widget control)
- **Audio Processing**: pydub (splitting + export)
- **Waveform + Playback**: sounddevice + numpy (sample extraction, real-time playback)
- **Transcription**: faster-whisper (local Whisper, runs in background QThread)
- **Packaging**: PyInstaller (distributable `.exe`)

---

## File Structure

```
audio_splitter/
│
├── main.py                  # Entry point, launches the app
│
├── core/
│   ├── __init__.py
│   ├── audio.py             # Audio loading, waveform extraction (numpy/soundfile)
│   ├── splitter.py          # Splitting logic using ffmpeg subprocess, file export
│   ├── player.py            # Playback engine (sounddevice), playhead position
│   └── transcriber.py       # faster-whisper transcription, saves <stem>.txt alongside audio
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py       # Root window, layout assembly
│   ├── waveform_widget.py   # Custom QWidget — waveform painting, marker dragging
│   ├── controls_bar.py      # Play/pause, timer, reset, confirm buttons
│   └── input_panel.py       # File picker, output folder, chunks/duration inputs
│
├── assets/
│   └── icons/               # File icon, folder icon, play/pause/reset/confirm SVGs
│
├── utils/
│   ├── __init__.py
│   └── time_format.py       # Timestamp formatting helpers (seconds → MM:SS.ms)
│
├── CLAUDE.md
├── requirements.txt
└── build.spec               # PyInstaller spec file
```

**Key design note:** `core/` is completely UI-agnostic — no PySide6 imports. `waveform_widget.py` will be the most complex file, handling marker dragging, waveform painting, and playhead rendering.

---

## Agent-Usable API (planned, not yet built)

The `core/` layer is already UI-agnostic, making it the natural foundation for an agent-facing API. No GUI changes needed — agents call core functions directly.

### Planned files
- `cli.py` — command-line interface, all output as JSON to stdout
- `agent_api.py` — single clean Python function wrapping the full pipeline

### CLI design

```bash
# Split into N equal chunks
python cli.py audio.mp3 --chunks 4

# Split every N seconds
python cli.py audio.mp3 --duration 30

# Split at explicit timestamps (seconds)
python cli.py audio.mp3 --at 30,75.5,120

# Transcribe only
python cli.py audio.mp3 --transcribe

# Full pipeline: transcribe, let agent reason about splits, then split
python cli.py audio.mp3 --transcribe --chunks 4 --output ./out

# Custom output folder
python cli.py audio.mp3 --chunks 4 --output ./out
```

All commands return JSON to stdout:
```json
{
  "success": true,
  "files": ["out/track_001.mp3", "out/track_002.mp3"],
  "chunks": 4,
  "duration": 183.4,
  "transcript": "out/track.txt"
}
```

### Python API design

```python
from agent_api import split_audio

result = split_audio(
    file="path/to/audio.mp3",
    output=None,              # defaults to same dir as file
    mode="chunks",            # "chunks" | "duration" | "timestamps"
    value=4,                  # int for chunks, float for duration, list[float] for timestamps
    transcribe=True,          # whether to also generate transcript
)
# returns same structure as JSON above
```

### Agent intelligence flow (the real value)

1. `transcribe(file)` → timestamped transcript
2. Agent reads transcript, reasons about natural split points (topic changes, speaker shifts, pauses)
3. Agent calls `split_audio(file, mode="timestamps", value=[t1, t2, ...])` with its chosen points
4. Result: intelligently split files, not just equal-duration chunks

### Key note on transcription
- If a `<stem>.txt` already exists alongside the audio, the agent should check for it before calling transcribe again — avoids redundant Whisper runs
- The GUI auto-generates this file on every file load, so GUI and agent paths naturally share transcripts

---

## Out of Scope (for now)

- Format conversion
- Audio format configuration
- Beat/silence detection for smart splitting
- Waveform zoom
- Undo/redo for marker positions (Reset covers this)
- Metadata preservation
- Batch processing of multiple files
