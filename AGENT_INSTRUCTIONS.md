# Agent Instructions — Audio Splitter

## Overview

Each `core/` module is directly runnable as a script. Agents use these the same way the GUI does — same functions, driven by CLI args and environment variables instead of UI controls. All scripts output JSON to stdout.

Run all commands from the **project root**.

## Prerequisites

- Python 3.13+
- `ffmpeg` on PATH (`winget install ffmpeg` on Windows)
- Dependencies installed: `pip install -r requirements.txt`

---

## Environment Variables

Set these in the session to configure behaviour across all scripts:

| Variable        | Default                      | Description                                            |
| --------------- | ---------------------------- | ------------------------------------------------------ |
| `OUTPUT_FOLDER` | Same directory as input file | Where split chunks are written                         |
| `WHISPER_MODEL` | `base`                       | Whisper model size (`tiny`, `base`, `small`, `medium`) |

```powershell
# PowerShell
$env:OUTPUT_FOLDER = "./output"
$env:WHISPER_MODEL = "small"
```

```bash
# bash
export OUTPUT_FOLDER="./output"
export WHISPER_MODEL="small"
```

---

## Scripts

### `core/audio.py` — Inspect audio file

Get duration, format, and sample rate before deciding how to split.

```bash
python core/audio.py podcast.mp3
```

```json
{"duration": 183.4, "format": "mp3", "sample_rate": 44100, "file_path": "podcast.mp3"}
```

---

### `core/splitter.py` — Split audio

Three mutually exclusive modes:

```bash
# Split into N equal chunks
python core/splitter.py podcast.mp3 --chunks 4

# Split every N seconds
python core/splitter.py podcast.mp3 --duration 60

# Split at exact timestamps (seconds, comma-separated)
python core/splitter.py podcast.mp3 --at 30,75.5,120
```

```json
{"files": ["output/podcast/podcast_001.mp3", "output/podcast/podcast_002.mp3"], "chunks": 2}
```

Output folder respects `$OUTPUT_FOLDER`. Files are named `<stem>_001.<ext>`, `<stem>_002.<ext>`, … inside a subfolder named after the source file.

---

### `core/transcriber.py` — Transcribe audio

**Only use this when the user asks for content-aware / intelligent splitting.** Not needed for simple chunk or duration splits.

```bash
python core/transcriber.py podcast.mp3
python core/transcriber.py podcast.mp3 --language ur
```

```json
{"transcript_path": "podcast.txt"}
```

`--language` accepts any Whisper language code (e.g. `ur`, `en`, `fr`). Omit it to auto-detect. See the full list at the bottom of this file.

Transcript is saved as `<stem>.txt` alongside the audio file (or in `$OUTPUT_FOLDER` if set). Before transcribing, check if `<stem>.txt` already exists — if it does, skip this step.

Transcript format:

```
[00:00.00] Hello everyone, welcome back to the podcast.
[00:04.83] Today we're going to be talking about something really interesting.
```

Model size is controlled by `$WHISPER_MODEL`. Larger models are slower but more accurate.

---

## Workflows

### Simple split (no transcription)

```bash
python core/audio.py podcast.mp3          # check duration/format
python core/splitter.py podcast.mp3 --chunks 4
```

### Intelligent split (agent reasons over transcript)

Only when the user explicitly asks for content-aware splits:

```bash
python core/audio.py podcast.mp3          # get duration
python core/transcriber.py podcast.mp3    # generate transcript (skip if .txt exists)
# read the transcript, reason about natural split points
# (topic shifts, speaker changes, long pauses, sentence boundaries)
python core/splitter.py podcast.mp3 --at 45.0,130.5,210.0
```

---

## Error Handling

All scripts return `{"error": "<message>"}` and exit with code 1 on failure. Common causes:

- `ffmpeg` not on PATH
- Input file not found or unsupported format (only MP3 and WAV are supported)
- `$WHISPER_MODEL` set to an invalid size

---

## Whisper Language Codes

Pass any of these to `--language`. Omit for auto-detect.

| Code | Language | Code | Language | Code | Language |
|------|----------|------|----------|------|----------|
| `af` | Afrikaans | `gl` | Galician | `pt` | Portuguese |
| `am` | Amharic | `gu` | Gujarati | `ro` | Romanian |
| `ar` | Arabic | `ha` | Hausa | `ru` | Russian |
| `as` | Assamese | `haw` | Hawaiian | `sa` | Sanskrit |
| `az` | Azerbaijani | `he` | Hebrew | `sd` | Sindhi |
| `ba` | Bashkir | `hi` | Hindi | `si` | Sinhala |
| `be` | Belarusian | `hr` | Croatian | `sk` | Slovak |
| `bg` | Bulgarian | `ht` | Haitian Creole | `sl` | Slovenian |
| `bn` | Bengali | `hu` | Hungarian | `sn` | Shona |
| `bo` | Tibetan | `hy` | Armenian | `so` | Somali |
| `br` | Breton | `id` | Indonesian | `sq` | Albanian |
| `bs` | Bosnian | `is` | Icelandic | `sr` | Serbian |
| `ca` | Catalan | `it` | Italian | `su` | Sundanese |
| `cs` | Czech | `ja` | Japanese | `sv` | Swedish |
| `cy` | Welsh | `jw` | Javanese | `sw` | Swahili |
| `da` | Danish | `ka` | Georgian | `ta` | Tamil |
| `de` | German | `kk` | Kazakh | `te` | Telugu |
| `el` | Greek | `km` | Khmer | `tg` | Tajik |
| `en` | English | `kn` | Kannada | `th` | Thai |
| `es` | Spanish | `ko` | Korean | `tk` | Turkmen |
| `et` | Estonian | `la` | Latin | `tl` | Tagalog |
| `eu` | Basque | `lb` | Luxembourgish | `tr` | Turkish |
| `fa` | Persian | `ln` | Lingala | `tt` | Tatar |
| `fi` | Finnish | `lo` | Lao | `uk` | Ukrainian |
| `fo` | Faroese | `lt` | Lithuanian | `ur` | Urdu |
| `fr` | French | `lv` | Latvian | `uz` | Uzbek |
| `fry` | Frisian | `mg` | Malagasy | `vi` | Vietnamese |
| `ga` | Irish | `mi` | Maori | `yi` | Yiddish |
| | | `mk` | Macedonian | `yo` | Yoruba |
| | | `ml` | Malayalam | `yue` | Cantonese |
| | | `mn` | Mongolian | `zh` | Chinese |
| | | `mr` | Marathi | | |
| | | `ms` | Malay | | |
| | | `mt` | Maltese | | |
| | | `my` | Myanmar | | |
| | | `ne` | Nepali | | |
| | | `nl` | Dutch | | |
| | | `nn` | Nynorsk | | |
| | | `no` | Norwegian | | |
| | | `oc` | Occitan | | |
| | | `pa` | Punjabi | | |
| | | `pl` | Polish | | |
| | | `ps` | Pashto | | |
