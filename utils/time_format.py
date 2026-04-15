def seconds_to_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS.cs format (cs = centiseconds)."""
    if seconds < 0:
        seconds = 0.0
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{minutes:02d}:{secs:02d}.{cs:02d}"
