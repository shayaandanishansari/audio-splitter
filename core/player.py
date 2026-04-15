import threading
from typing import Optional

import numpy as np
import sounddevice as sd


class AudioPlayer:
    """
    Thin wrapper around sounddevice for mono float32 playback.
    Position is updated from the audio callback thread and read by the Qt timer
    on the main thread — a plain float assignment is atomic enough on CPython.
    """

    def __init__(self):
        self._samples: Optional[np.ndarray] = None
        self._sample_rate: int = 44100
        self._duration: float = 0.0
        self._current_frame: int = 0
        self._position: float = 0.0
        self._playing: bool = False
        self._stream: Optional[sd.OutputStream] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, samples: np.ndarray, sample_rate: int, duration: float) -> None:
        self.stop()
        with self._lock:
            self._samples = samples.copy()
            self._sample_rate = sample_rate
            self._duration = duration
            self._current_frame = 0
            self._position = 0.0

    def play(self) -> None:
        if self._samples is None or self._playing:
            return
        # If we reached the end, restart from the beginning
        if self._current_frame >= len(self._samples):
            self._current_frame = 0
            self._position = 0.0
        self._playing = True
        self._stream = sd.OutputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="float32",
            callback=self._audio_callback,
            finished_callback=self._on_stream_finished,
        )
        self._stream.start()

    def pause(self) -> None:
        if self._stream and self._playing:
            self._playing = False
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def stop(self) -> None:
        self.pause()
        with self._lock:
            self._current_frame = 0
            self._position = 0.0

    def seek(self, seconds: float) -> None:
        was_playing = self._playing
        if was_playing:
            self.pause()
        with self._lock:
            self._current_frame = int(
                max(0.0, min(seconds, self._duration)) * self._sample_rate
            )
            self._position = seconds
        if was_playing:
            self.play()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def position(self) -> float:
        return self._position

    @property
    def is_playing(self) -> bool:
        return self._playing

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _audio_callback(self, outdata, frames, time_info, status):
        start = self._current_frame
        end = start + frames
        samples = self._samples

        if samples is None or start >= len(samples):
            outdata[:] = 0
            return

        chunk = samples[start:end]
        actual = len(chunk)

        outdata[:actual, 0] = chunk
        if actual < frames:
            outdata[actual:, 0] = 0

        self._current_frame = start + actual
        self._position = self._current_frame / self._sample_rate

    def _on_stream_finished(self):
        self._playing = False
