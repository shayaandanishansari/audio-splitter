import threading
from pathlib import Path
from typing import Callable, Optional

from faster_whisper import WhisperModel

from utils.time_format import seconds_to_timestamp

DEFAULT_MODEL = "base"

_model: Optional[WhisperModel] = None


def _get_model(model_size: str = DEFAULT_MODEL) -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model


def transcribe(
    file_path: str,
    output_folder: Optional[str] = None,
    model_size: str = DEFAULT_MODEL,
    progress_callback: Optional[Callable[[int], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> str:
    """
    Transcribe an audio file using faster-whisper and save a timestamped
    transcript as <stem>.txt.

    output_folder: where to save the transcript. Defaults to the same
    directory as the audio file if not provided.

    progress_callback is called with an integer 0-100 as each segment
    is processed, derived from segment.end / total_duration.

    stop_event: if set, the segment loop checks it between segments and
    raises InterruptedError when it is set (cancellation).

    Returns the path to the saved transcript file.
    """
    path = Path(file_path)
    out_dir = Path(output_folder) if output_folder else path.parent
    transcript_path = out_dir / path.with_suffix(".txt").name

    model = _get_model(model_size)
    segments, info = model.transcribe(
        file_path, beam_size=5, task="transcribe", language=None
    )
    total_duration = info.duration or 1.0  # avoid division by zero

    lines = []
    for segment in segments:
        if stop_event and stop_event.is_set():
            raise InterruptedError("Transcription cancelled")
        timestamp = seconds_to_timestamp(segment.start)
        lines.append(f"[{timestamp}] {segment.text.strip()}")
        if progress_callback:
            pct = min(100, int(segment.end / total_duration * 100))
            progress_callback(pct)

    transcript_path.write_text("\n".join(lines), encoding="utf-8")
    return str(transcript_path)


if __name__ == "__main__":
    import json
    import os
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python core/transcriber.py <file_path>"}))
        sys.exit(1)

    try:
        result = transcribe(
            file_path=sys.argv[1],
            output_folder=os.environ.get("OUTPUT_FOLDER") or None,
            model_size=os.environ.get("WHISPER_MODEL", DEFAULT_MODEL),
        )
        print(json.dumps({"transcript_path": result}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
