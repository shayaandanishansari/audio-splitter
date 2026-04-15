from pathlib import Path

from pydub import AudioSegment


def split_audio(file_path: str, split_points: list[float], output_folder: str) -> list[str]:
    """
    Split an audio file at the given time positions (in seconds).

    Creates a subfolder named after the source file inside output_folder and
    writes each segment there as:  <stem>_001.<ext>, <stem>_002.<ext>, …

    The last segment may be shorter than the others — that is expected.

    Returns the list of written file paths.
    """
    path = Path(file_path)
    ext = path.suffix.lower().lstrip(".")
    stem = path.stem

    if ext == "mp3":
        audio = AudioSegment.from_mp3(file_path)
    elif ext == "wav":
        audio = AudioSegment.from_wav(file_path)
    else:
        raise ValueError(f"Unsupported format: {ext!r}")

    # Output subfolder
    out_dir = Path(output_folder) / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build cut boundaries in milliseconds
    total_ms = len(audio)
    boundaries_ms = (
        [0]
        + [int(t * 1000) for t in sorted(split_points)]
        + [total_ms]
    )

    output_files: list[str] = []
    for idx, (start_ms, end_ms) in enumerate(
        zip(boundaries_ms, boundaries_ms[1:]), start=1
    ):
        segment = audio[start_ms:end_ms]
        filename = f"{stem}_{idx:03d}.{ext}"
        out_path = str(out_dir / filename)
        segment.export(out_path, format=ext)
        output_files.append(out_path)

    return output_files
