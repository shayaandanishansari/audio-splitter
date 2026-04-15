import threading
from pathlib import Path

from PySide6.QtCore import Qt, QObject, QThread, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
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

WAVEFORM_RESOLUTION = 1200


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class _LoadWorker(QObject):
    finished = Signal(dict)
    failed   = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self._file_path = file_path

    def run(self):
        try:
            data = load_audio(self._file_path)
            self.finished.emit(data)
        except Exception as exc:
            self.failed.emit(str(exc))


class _TranscriptionWorker(QObject):
    finished = Signal(str)
    failed   = Signal(str)
    progress = Signal(int)   # 0-100

    def __init__(self, file_path: str, output_folder: str | None = None):
        super().__init__()
        self._file_path = file_path
        self._output_folder = output_folder
        self._stop_event = threading.Event()

    def cancel(self):
        self._stop_event.set()

    def run(self):
        try:
            path = transcribe(
                self._file_path,
                output_folder=self._output_folder,
                progress_callback=self.progress.emit,
                stop_event=self._stop_event,
            )
            self.finished.emit(path)
        except InterruptedError:
            self.failed.emit("cancelled")
        except Exception as exc:
            self.failed.emit(str(exc))


class _SplitWorker(QObject):
    finished = Signal(list)   # list of output file paths
    failed   = Signal(str)

    def __init__(self, file_path: str, split_points: list, output_folder: str):
        super().__init__()
        self._file_path = file_path
        self._split_points = split_points
        self._output_folder = output_folder

    def run(self):
        try:
            files = split_audio(self._file_path, self._split_points, self._output_folder)
            self.finished.emit(files)
        except Exception as exc:
            self.failed.emit(str(exc))


def _start_worker(worker: QObject, parent: QObject) -> QThread:
    thread = QThread(parent)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)   # type: ignore[attr-defined]
    worker.failed.connect(thread.quit)     # type: ignore[attr-defined]
    thread.start()
    return thread


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
        self._load_thread: QThread | None = None
        self._load_worker: _LoadWorker | None = None
        self._transcription_thread: QThread | None = None
        self._transcription_worker: _TranscriptionWorker | None = None
        self._split_thread: QThread | None = None
        self._split_worker: _SplitWorker | None = None

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

        title = QLabel("Audio Splitter")
        f = QFont()
        f.setPointSize(17)
        title.setFont(f)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_label.setObjectName("statusLabel")
        root.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        root.addWidget(self.progress_bar)

        self.input_panel = InputPanel()
        self.input_panel.file_selected.connect(self._on_file_selected)
        self.input_panel.folder_selected.connect(self._on_folder_selected)
        self.input_panel.chunks_changed.connect(self._on_chunks_changed)
        self.input_panel.duration_changed.connect(self._on_duration_changed)
        root.addWidget(self.input_panel)

        self.waveform = WaveformWidget()
        self.waveform.marker_moved.connect(self._on_marker_moved)
        self.waveform.marker_selected.connect(self._on_marker_selected)
        self.waveform.seek_requested.connect(self._on_seek)
        root.addWidget(self.waveform, stretch=1)

        self.controls = ControlsBar()
        self.controls.play_clicked.connect(self._on_play)
        self.controls.pause_clicked.connect(self._on_pause)
        self.controls.transcribe_clicked.connect(self._on_transcribe)
        self.controls.stop_clicked.connect(self._on_stop_transcription)
        self.controls.reset_clicked.connect(self._on_reset)
        self.controls.confirm_clicked.connect(self._on_confirm)
        root.addWidget(self.controls)

    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.setInterval(40)
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
            QLabel#statusLabel {
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
            QPushButton:focus {
                background-color: #9e8080;
                outline: none;
            }
            QPushButton#confirmBtn {
                background-color: #3aaa55;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#confirmBtn:hover {
                background-color: #4abb66;
            }
            QPushButton#stopBtn {
                background-color: #cc5555;
            }
            QPushButton#stopBtn:hover {
                background-color: #dd6666;
            }
            QPushButton#stopBtn:pressed {
                background-color: #aa3333;
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
            QPushButton#spinArrow {
                background-color: #b09090;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                font-size: 8px;
                padding: 0px;
            }
            QPushButton#spinArrow:hover {
                background-color: #c0a0a0;
            }
            QPushButton#spinArrow:pressed {
                background-color: #906060;
            }
            WaveformWidget {
                border-radius: 10px;
            }
            QProgressBar {
                background-color: #e0c0c0;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #9e8080;
                border-radius: 3px;
            }
        """)

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_file_selected(self, path: str):
        if self._load_thread and self._load_thread.isRunning():
            self._load_thread.quit()
            self._load_thread.wait()

        self.status_label.setText("⏳  Loading audio...")
        self._audio_data = None

        self._load_worker = _LoadWorker(path)
        self._load_worker.finished.connect(self._on_load_done)
        self._load_worker.failed.connect(self._on_load_failed)
        self._load_thread = _start_worker(self._load_worker, self)

    def _on_load_done(self, data: dict):
        self._audio_data = data
        self.status_label.setText("")

        waveform = downsample_for_display(data["samples"], WAVEFORM_RESOLUTION)
        self.waveform.load_waveform(waveform, data["duration"])
        self._player.load(data["samples"], data["sample_rate"], data["duration"])
        self.input_panel.set_total_duration(data["duration"])
        self._distribute_markers(self.input_panel.chunks)

    def _on_load_failed(self, error: str):
        self.status_label.setText("")
        QMessageBox.critical(self, "Load Error", error)

    def _on_folder_selected(self, path: str):
        pass

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

        self.controls.confirm_btn.setEnabled(False)
        self.status_label.setText("⏳  Splitting audio...")

        self._split_worker = _SplitWorker(
            self._audio_data["file_path"], positions, out
        )
        self._split_worker.finished.connect(self._on_split_done)
        self._split_worker.failed.connect(self._on_split_failed)
        self._split_thread = _start_worker(self._split_worker, self)

    def _on_split_done(self, files: list):
        self.controls.confirm_btn.setEnabled(True)
        out = self.input_panel.output_folder
        self.status_label.setText(f"✓  Split into {len(files)} file(s)")
        QMessageBox.information(
            self, "Done",
            f"Split into {len(files)} file(s).\n\nSaved to:\n{out}"
        )

    def _on_split_failed(self, error: str):
        self.controls.confirm_btn.setEnabled(True)
        self.status_label.setText("⚠  Split failed")
        QMessageBox.critical(self, "Split Error", error)

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def _on_transcribe(self):
        if self._audio_data is None:
            QMessageBox.warning(self, "No File", "Please select an audio file first.")
            return
        self.controls.transcribe_btn.hide()
        self.controls.stop_btn.show()
        self._start_transcription(
            self._audio_data["file_path"],
            self.input_panel.output_folder or None,
        )

    def _on_stop_transcription(self):
        if self._transcription_worker:
            self._transcription_worker.cancel()

    def _start_transcription(self, file_path: str, output_folder: str | None = None):
        if self._transcription_thread and self._transcription_thread.isRunning():
            self._transcription_thread.quit()
            self._transcription_thread.wait()

        self.status_label.setText("⏳  Transcribing...")
        self._transcription_worker = _TranscriptionWorker(file_path, output_folder)
        self._transcription_worker.finished.connect(self._on_transcription_done)
        self._transcription_worker.failed.connect(self._on_transcription_failed)
        self._transcription_worker.progress.connect(self._on_transcription_progress)
        self._transcription_thread = _start_worker(self._transcription_worker, self)

    def _on_transcription_progress(self, pct: int):
        self.progress_bar.show()
        self.progress_bar.setValue(pct)
        self.status_label.setText(f"⏳  Transcribing... {pct}%")

    def _on_transcription_done(self, transcript_path: str):
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        self.controls.stop_btn.hide()
        self.controls.transcribe_btn.show()
        self.status_label.setText(
            f"✓  Transcript saved → {Path(transcript_path).name}"
        )

    def _on_transcription_failed(self, error: str):
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        self.controls.stop_btn.hide()
        self.controls.transcribe_btn.show()
        if error == "cancelled":
            self.status_label.setText("Transcription stopped")
        else:
            self.status_label.setText(f"⚠  Transcription failed: {error}")

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
        # Cancel transcription first so the segment loop exits cleanly
        if self._transcription_worker:
            self._transcription_worker.cancel()
        for thread in (self._load_thread, self._transcription_thread, self._split_thread):
            if thread and thread.isRunning():
                thread.quit()
                thread.wait(3000)   # up to 3 s; don't block forever
        super().closeEvent(event)
