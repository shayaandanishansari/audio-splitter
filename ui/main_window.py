from pathlib import Path

from PySide6.QtCore import Qt, QObject, QThread, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.audio import downsample_for_display, load_audio
from core.player import AudioPlayer
from core.splitter import split_audio
from core.transcriber import transcribe
from ui.controls_bar import ControlsBar
from ui.input_panel import InputPanel
from ui.waveform_widget import WaveformWidget

WAVEFORM_RESOLUTION = 1200   # display columns


# ---------------------------------------------------------------------------
# Background transcription worker
# ---------------------------------------------------------------------------

class _TranscriptionWorker(QObject):
    finished = Signal(str)   # transcript file path
    failed   = Signal(str)   # error message

    def __init__(self, file_path: str):
        super().__init__()
        self._file_path = file_path

    def run(self):
        try:
            path = transcribe(self._file_path)
            self.finished.emit(path)
        except Exception as exc:
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Splitter")
        self.setMinimumSize(720, 500)

        self._audio_data: dict | None = None
        self._player = AudioPlayer()
        self._transcription_thread: QThread | None = None
        self._transcription_worker: _TranscriptionWorker | None = None

        self._setup_ui()
        self._apply_styles()
        self._start_timer()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(22, 16, 22, 16)
        root.setSpacing(12)

        # Title row
        title = QLabel("Audio Splitter")
        f = QFont()
        f.setPointSize(17)
        title.setFont(f)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        # Transcription status — subtle, right-aligned
        self.transcript_status = QLabel("")
        self.transcript_status.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.transcript_status.setObjectName("transcriptStatus")
        root.addWidget(self.transcript_status)

        # Input panel
        self.input_panel = InputPanel()
        self.input_panel.file_selected.connect(self._on_file_selected)
        self.input_panel.folder_selected.connect(self._on_folder_selected)
        self.input_panel.chunks_changed.connect(self._on_chunks_changed)
        self.input_panel.duration_changed.connect(self._on_duration_changed)
        root.addWidget(self.input_panel)

        # Waveform
        self.waveform = WaveformWidget()
        self.waveform.marker_moved.connect(self._on_marker_moved)
        self.waveform.marker_selected.connect(self._on_marker_selected)
        self.waveform.seek_requested.connect(self._on_seek)
        root.addWidget(self.waveform, stretch=1)

        # Controls
        self.controls = ControlsBar()
        self.controls.play_clicked.connect(self._on_play)
        self.controls.pause_clicked.connect(self._on_pause)
        self.controls.reset_clicked.connect(self._on_reset)
        self.controls.confirm_clicked.connect(self._on_confirm)
        root.addWidget(self.controls)

    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.setInterval(40)   # ~25 fps
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ------------------------------------------------------------------
    # Stylesheet
    # ------------------------------------------------------------------

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #f2dada;
                color: #2a1818;
            }
            QLabel {
                color: #2a1818;
                background: transparent;
            }
            QLabel#transcriptStatus {
                font-size: 11px;
                color: #7a5555;
            }
            QPushButton {
                background-color: #9e8080;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 7px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #b09090;
            }
            QPushButton:pressed {
                background-color: #806060;
            }
            QPushButton#confirmBtn {
                background-color: #3aaa55;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#confirmBtn:hover {
                background-color: #4abb66;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #c8a8a8;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #6e4848;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #ead0d0;
                border: 1px solid #c0a0a0;
                border-radius: 5px;
                padding: 2px 4px;
            }
            WaveformWidget {
                border-radius: 10px;
            }
        """)

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_file_selected(self, path: str):
        try:
            self._audio_data = load_audio(path)
        except Exception as exc:
            QMessageBox.critical(self, "Load Error", str(exc))
            return

        waveform = downsample_for_display(
            self._audio_data["samples"], WAVEFORM_RESOLUTION
        )
        self.waveform.load_waveform(waveform, self._audio_data["duration"])
        self._player.load(
            self._audio_data["samples"],
            self._audio_data["sample_rate"],
            self._audio_data["duration"],
        )
        self.input_panel.set_total_duration(self._audio_data["duration"])
        self._distribute_markers(self.input_panel.chunks)
        self._start_transcription(path)

    def _on_folder_selected(self, path: str):
        pass   # stored inside input_panel.output_folder

    def _on_chunks_changed(self, chunks: int):
        if self._audio_data:
            self._distribute_markers(chunks)

    def _on_duration_changed(self, duration: float):
        if self._audio_data and duration > 0:
            chunks = max(2, int(self._audio_data["duration"] / duration))
            self._distribute_markers(chunks)

    def _on_marker_moved(self, index: int, seconds: float):
        if self.waveform.selected_marker == index:
            self.controls.update_timer(seconds)

    def _on_marker_selected(self, index: int):
        if index >= 0:
            positions = self.waveform.get_marker_positions()
            if index < len(positions):
                self.controls.update_timer(positions[index])

    def _on_seek(self, seconds: float):
        self._player.seek(seconds)
        self.waveform.set_playhead(seconds)
        if self.waveform.selected_marker < 0:
            self.controls.update_timer(seconds)

    def _on_play(self):
        if self._audio_data is None:
            QMessageBox.warning(self, "No File", "Please select an audio file first.")
            return
        self._player.play()

    def _on_pause(self):
        self._player.pause()

    def _on_reset(self):
        if self._audio_data:
            self._distribute_markers(self.input_panel.chunks)

    def _on_confirm(self):
        if self._audio_data is None:
            QMessageBox.warning(self, "No File", "Please select an audio file first.")
            return
        out = self.input_panel.output_folder
        if not out:
            QMessageBox.warning(self, "No Output", "Please select an output folder.")
            return
        positions = self.waveform.get_marker_positions()
        if not positions:
            QMessageBox.warning(self, "No Markers", "No split markers defined.")
            return
        try:
            files = split_audio(self._audio_data["file_path"], positions, out)
            QMessageBox.information(
                self, "Done",
                f"Split into {len(files)} file(s).\n\nSaved to:\n{out}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Split Error", str(exc))

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def _start_transcription(self, file_path: str):
        # Cancel any in-progress transcription for a previous file
        if self._transcription_thread and self._transcription_thread.isRunning():
            self._transcription_thread.quit()
            self._transcription_thread.wait()

        self.transcript_status.setText("⏳  Transcribing...")

        self._transcription_worker = _TranscriptionWorker(file_path)
        self._transcription_thread = QThread(self)
        self._transcription_worker.moveToThread(self._transcription_thread)

        self._transcription_thread.started.connect(self._transcription_worker.run)
        self._transcription_worker.finished.connect(self._on_transcription_done)
        self._transcription_worker.failed.connect(self._on_transcription_failed)
        self._transcription_worker.finished.connect(self._transcription_thread.quit)
        self._transcription_worker.failed.connect(self._transcription_thread.quit)

        self._transcription_thread.start()

    def _on_transcription_done(self, transcript_path: str):
        self.transcript_status.setText(f"✓  Transcript saved → {Path(transcript_path).name}")

    def _on_transcription_failed(self, error: str):
        self.transcript_status.setText(f"⚠  Transcription failed: {error}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _distribute_markers(self, chunks: int) -> None:
        if not self._audio_data:
            return
        total = self._audio_data["duration"]
        step = total / chunks
        positions = [step * i for i in range(1, chunks)]
        self.waveform.set_markers(positions)

    def _tick(self) -> None:
        if self._player.is_playing:
            pos = self._player.position
            self.waveform.set_playhead(pos)
            if self.waveform.selected_marker < 0:
                self.controls.update_timer(pos)

    def closeEvent(self, event):
        self._player.stop()
        if self._transcription_thread and self._transcription_thread.isRunning():
            self._transcription_thread.quit()
            self._transcription_thread.wait()
        super().closeEvent(event)
