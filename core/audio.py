from pathlib import Path
import numpy as np
import soundfile as sf
from pydub import AudioSegment


def load_audio(file_path: str) -> dict:
    """
    Load an audio file and return waveform data.

    Returns a dict with:
        samples     — mono float32 numpy array, normalized to [-1, 1]
        sample_rate — int
        duration    — float (seconds)
        format      — 'mp3' or 'wav'
        file_path   — original path string
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".mp3":
        audio = AudioSegment.from_mp3(file_path)
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        if audio.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)
        # 16-bit PCM → normalize to [-1, 1]
        samples /= 32768.0
        sample_rate = audio.frame_rate
        duration = len(audio) / 1000.0
        fmt = "mp3"

    elif ext == ".wav":
        samples, sample_rate = sf.read(file_path, always_2d=False, dtype="float32")
        if samples.ndim == 2:
            samples = samples.mean(axis=1)
        duration = len(samples) / sample_rate
        fmt = "wav"

    else:
        raise ValueError(f"Unsupported format: {ext!r}. Only MP3 and WAV are supported.")

    return {
        "samples": samples,
        "sample_rate": sample_rate,
        "duration": duration,
        "format": fmt,
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

    # Normalize so the loudest peak = 1.0
    peak = result.max()
    if peak > 0:
        result /= peak

    return result
