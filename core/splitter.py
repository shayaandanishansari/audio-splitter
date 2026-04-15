import json
import subprocess
from pathlib import Path


def _get_duration(file_path: str) -> float:
    """Use ffprobe to get the exact duration of an audio file in seconds."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            file_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def split_audio(file_path: str, split_points: list[float], output_folder: str) -> list[str]:
    """
    Split an audio file at the given time positions (in seconds) using ffmpeg.

    Uses stream copy (-c copy) so there is no re-encoding — splits are
    instant and the output is bit-perfect.

    Creates a subfolder named after the source file inside output_folder and
    writes each segment as:  <stem>_001.<ext>, <stem>_002.<ext>, …

    The last segment may be shorter than the others — that is expected.

    Returns the list of written file paths.
    """
    path = Path(file_path)
    ext = path.suffix.lower().lstrip(".")
    stem = path.stem

    if ext not in ("mp3", "wav"):
        raise ValueError(f"Unsupported format: {ext!r}")

    out_dir = Path(output_folder) / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    total = _get_duration(file_path)
    boundaries = [0.0] + sorted(split_points) + [total]

    output_files: list[str] = []
    for idx, (start, end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
        out_path = str(out_dir / f"{stem}_{idx:03d}.{ext}")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", file_path,
                "-ss", str(start),
                "-to", str(end),
                "-c", "copy",
                out_path,
            ],
            check=True,
            capture_output=True,
        )
        output_files.append(out_path)

    return output_files
