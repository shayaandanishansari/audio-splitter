import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


def load_audio(file_path: str) -> dict:
    """
    Load an audio file and return waveform data.

    MP3 files are decoded to a temporary WAV via ffmpeg, then read with
    soundfile. WAV files are read directly. No pydub / audioop required.

    Returns a dict with:
        samples     — mono float32 numpy array, normalized to [-1, 1]
        sample_rate — int
        duration    — float (seconds)
        format      — 'mp3' or 'wav'
        file_path   — original path string
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in (".mp3", ".wav"):
        raise ValueError(f"Unsupported format: {ext!r}. Only MP3 and WAV are supported.")

    if ext == ".wav":
        samples, sample_rate = sf.read(file_path, always_2d=False, dtype="float32")
        if samples.ndim == 2:
            samples = samples.mean(axis=1)
        duration = len(samples) / sample_rate

    else:  # .mp3 — decode via ffmpeg into a temp WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", file_path,
                    "-ac", "1",          # mix to mono
                    "-ar", "44100",      # resample to 44.1 kHz
                    "-f", "wav",
                    tmp_path,
                ],
                check=True,
                capture_output=True,
            )
            samples, sample_rate = sf.read(tmp_path, always_2d=False, dtype="float32")
            if samples.ndim == 2:
                samples = samples.mean(axis=1)
            duration = len(samples) / sample_rate
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return {
        "samples": samples,
        "sample_rate": sample_rate,
        "duration": duration,
        "format": ext.lstrip("."),
        "file_path": file_path,
    }


def downsample_for_display(samples: np.ndarray, target_width: int) -> np.ndarray:
    """
    Reduce waveform samples to target_width peak values for rendering.
    Returns a float32 array of shape (target_width,) with values in [0, 1].
    """
    n = len(samples)
    if n == 0 or target_width == 0:
        return np.zeros(target_width, dtype=np.float32)

    indices = np.linspace(0, n, target_width + 1, dtype=int)
    result = np.zeros(target_width, dtype=np.float32)
    for i in range(target_width):
        chunk = samples[indices[i]:indices[i + 1]]
        if len(chunk) > 0:
            result[i] = np.max(np.abs(chunk))

    peak = result.max()
    if peak > 0:
        result /= peak

    return result


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python core/audio.py <file_path>"}))
        sys.exit(1)

    try:
        result = load_audio(sys.argv[1])
        print(json.dumps({
            "duration": result["duration"],
            "format": result["format"],
            "sample_rate": result["sample_rate"],
            "file_path": result["file_path"],
        }))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
