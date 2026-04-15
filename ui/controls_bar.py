from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from utils.time_format import seconds_to_timestamp


class ControlsBar(QWidget):
    """
    Bottom bar:  [Play]  [Pause]  ···  [timer]  ···  [Reset]  [Confirm ✓]
    """

    play_clicked        = Signal()
    pause_clicked       = Signal()
    reset_clicked       = Signal()
    confirm_clicked     = Signal()
    transcribe_clicked  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self.play_btn       = QPushButton("▶")
        self.pause_btn      = QPushButton("⏸")
        self.timer_label    = QLabel("00:00.00")
        self.transcribe_btn = QPushButton("⌨  Transcribe")
        self.reset_btn      = QPushButton("↺  Reset")
        self.confirm_btn    = QPushButton("✓")

        for btn in (self.play_btn, self.pause_btn):
            btn.setFixedSize(40, 40)

        self.confirm_btn.setFixedSize(48, 40)
        self.confirm_btn.setObjectName("confirmBtn")

        # Monospace timer
        font = QFont("Courier New", 13)
        self.timer_label.setFont(font)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setMinimumWidth(110)

        layout.addWidget(self.play_btn)
        layout.addWidget(self.pause_btn)
        layout.addStretch()
        layout.addWidget(self.timer_label)
        layout.addStretch()
        layout.addWidget(self.transcribe_btn)
        layout.addWidget(self.reset_btn)
        layout.addWidget(self.confirm_btn)

        self.play_btn.clicked.connect(self.play_clicked)
        self.pause_btn.clicked.connect(self.pause_clicked)
        self.transcribe_btn.clicked.connect(self.transcribe_clicked)
        self.reset_btn.clicked.connect(self.reset_clicked)
        self.confirm_btn.clicked.connect(self.confirm_clicked)

    def update_timer(self, seconds: float) -> None:
        self.timer_label.setText(seconds_to_timestamp(seconds))
