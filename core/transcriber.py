from pathlib import Path

from faster_whisper import WhisperModel

from utils.time_format import seconds_to_timestamp

# Model used for auto-transcription. "base" is a good balance of speed and
# quality for background use. Swap to "small" or "medium" for better accuracy.
DEFAULT_MODEL = "base"


def transcribe(file_path: str, model_size: str = DEFAULT_MODEL) -> str:
    """
    Transcribe an audio file using faster-whisper and save a timestamped
    transcript as <stem>.txt in the same directory as the audio file.

    Returns the path to the saved transcript file.

    Format of each line:
        [MM:SS.cs] segment text
    """
    path = Path(file_path)
    transcript_path = path.with_suffix(".txt")

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(file_path, beam_size=5)

    lines = []
    for segment in segments:
        timestamp = seconds_to_timestamp(segment.start)
        lines.append(f"[{timestamp}] {segment.text.strip()}")

    transcript_path.write_text("\n".join(lines), encoding="utf-8")
    return str(transcript_path)
