from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

_LANGUAGES = [
    ("Auto-detect", None),
    ("Afrikaans", "af"),
    ("Albanian", "sq"),
    ("Amharic", "am"),
    ("Arabic", "ar"),
    ("Armenian", "hy"),
    ("Assamese", "as"),
    ("Azerbaijani", "az"),
    ("Bashkir", "ba"),
    ("Basque", "eu"),
    ("Belarusian", "be"),
    ("Bengali", "bn"),
    ("Bosnian", "bs"),
    ("Breton", "br"),
    ("Bulgarian", "bg"),
    ("Cantonese", "yue"),
    ("Catalan", "ca"),
    ("Chinese", "zh"),
    ("Croatian", "hr"),
    ("Czech", "cs"),
    ("Danish", "da"),
    ("Dutch", "nl"),
    ("English", "en"),
    ("Estonian", "et"),
    ("Faroese", "fo"),
    ("Finnish", "fi"),
    ("French", "fr"),
    ("Galician", "gl"),
    ("Georgian", "ka"),
    ("German", "de"),
    ("Greek", "el"),
    ("Gujarati", "gu"),
    ("Haitian Creole", "ht"),
    ("Hausa", "ha"),
    ("Hawaiian", "haw"),
    ("Hebrew", "he"),
    ("Hindi", "hi"),
    ("Hungarian", "hu"),
    ("Icelandic", "is"),
    ("Indonesian", "id"),
    ("Italian", "it"),
    ("Japanese", "ja"),
    ("Javanese", "jw"),
    ("Kannada", "kn"),
    ("Kazakh", "kk"),
    ("Khmer", "km"),
    ("Korean", "ko"),
    ("Lao", "lo"),
    ("Latin", "la"),
    ("Latvian", "lv"),
    ("Lingala", "ln"),
    ("Lithuanian", "lt"),
    ("Luxembourgish", "lb"),
    ("Macedonian", "mk"),
    ("Malagasy", "mg"),
    ("Malay", "ms"),
    ("Malayalam", "ml"),
    ("Maltese", "mt"),
    ("Maori", "mi"),
    ("Marathi", "mr"),
    ("Mongolian", "mn"),
    ("Myanmar", "my"),
    ("Nepali", "ne"),
    ("Norwegian", "no"),
    ("Nynorsk", "nn"),
    ("Occitan", "oc"),
    ("Pashto", "ps"),
    ("Persian", "fa"),
    ("Polish", "pl"),
    ("Portuguese", "pt"),
    ("Punjabi", "pa"),
    ("Romanian", "ro"),
    ("Russian", "ru"),
    ("Sanskrit", "sa"),
    ("Serbian", "sr"),
    ("Shona", "sn"),
    ("Sindhi", "sd"),
    ("Sinhala", "si"),
    ("Slovak", "sk"),
    ("Slovenian", "sl"),
    ("Somali", "so"),
    ("Spanish", "es"),
    ("Sundanese", "su"),
    ("Swahili", "sw"),
    ("Swedish", "sv"),
    ("Tagalog", "tl"),
    ("Tajik", "tg"),
    ("Tamil", "ta"),
    ("Tatar", "tt"),
    ("Telugu", "te"),
    ("Thai", "th"),
    ("Tibetan", "bo"),
    ("Turkish", "tr"),
    ("Turkmen", "tk"),
    ("Ukrainian", "uk"),
    ("Urdu", "ur"),
    ("Uzbek", "uz"),
    ("Vietnamese", "vi"),
    ("Welsh", "cy"),
    ("Yiddish", "yi"),
    ("Yoruba", "yo"),
]


def _make_spin(spin: QSpinBox, row: QHBoxLayout, suffix: str = "") -> None:
    """Add a spinbox (no built-in arrows) + separate ▲▼ buttons + optional label to a layout."""
    spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    spin.setFixedWidth(40)
    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)

    btn_up = QPushButton("▲")
    btn_dn = QPushButton("▼")
    for btn in (btn_up, btn_dn):
        btn.setFixedSize(22, 18)
        btn.setObjectName("spinArrow")

    btn_up.clicked.connect(spin.stepUp)
    btn_dn.clicked.connect(spin.stepDown)

    arrow_col = QVBoxLayout()
    arrow_col.setSpacing(1)
    arrow_col.setContentsMargins(0, 0, 0, 0)
    arrow_col.addWidget(btn_up)
    arrow_col.addWidget(btn_dn)

    row.addWidget(spin)
    row.addLayout(arrow_col)
    if suffix:
        lbl = QLabel(suffix)
        lbl.setFixedWidth(10)
        row.addWidget(lbl)


# ---------------------------------------------------------------------------
# File / Folder picker button
# ---------------------------------------------------------------------------

class PickerButton(QPushButton):
    """Button that shows a placeholder until a path is selected, then shows
    the icon + truncated name/path."""

    _MAX_LEN = 22

    def __init__(self, placeholder: str, icon: str, parent=None):
        super().__init__(placeholder, parent)
        self._placeholder = placeholder
        self._icon = icon
        self._path: str = ""

    def set_path(self, path: str) -> None:
        self._path = path
        name = Path(path).name or path
        if len(name) > self._MAX_LEN:
            name = name[: self._MAX_LEN - 1] + "…"
        self.setText(f"{self._icon}  {name}")
        self.setToolTip(path)

    def get_path(self) -> str:
        return self._path


# ---------------------------------------------------------------------------
# Linked Chunks / Duration panel
# ---------------------------------------------------------------------------

class ChunkDurationPanel(QWidget):
    """
    Two linked inputs:
      • Chunks  (slider + spinbox)  →  updates Duration
      • Duration (slider + spinbox) →  updates Chunks
    Changing either redistributes markers evenly.
    """

    chunks_changed   = Signal(int)
    duration_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._total: float = 0.0
        self._busy: bool = False   # prevent recursive updates
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # -- Chunks row: label | slider | spinbox --
        chunks_row = QHBoxLayout()
        lbl_c = QLabel("Chunks:")
        lbl_c.setFixedWidth(58)
        self.chunks_slider = QSlider(Qt.Orientation.Horizontal)
        self.chunks_slider.setRange(2, 20)
        self.chunks_slider.setValue(4)
        self.chunks_spin = QSpinBox()
        self.chunks_spin.setRange(2, 20)
        self.chunks_spin.setValue(4)
        chunks_row.addWidget(lbl_c)
        chunks_row.addWidget(self.chunks_slider)
        _make_spin(self.chunks_spin, chunks_row)

        # -- Duration row: label | slider | HH | MM | SS --
        dur_row = QHBoxLayout()
        dur_row.setSpacing(4)
        lbl_d = QLabel("Duration:")
        lbl_d.setFixedWidth(58)
        self.dur_slider = QSlider(Qt.Orientation.Horizontal)
        self.dur_slider.setRange(1, 600)
        self.dur_slider.setValue(30)

        self.dur_h = QSpinBox()
        self.dur_h.setRange(0, 99)
        self.dur_h.setValue(0)

        self.dur_m = QSpinBox()
        self.dur_m.setRange(0, 59)
        self.dur_m.setValue(0)

        self.dur_s = QSpinBox()
        self.dur_s.setRange(0, 59)
        self.dur_s.setValue(30)

        dur_row.addWidget(lbl_d)
        dur_row.addWidget(self.dur_slider)
        _make_spin(self.dur_h, dur_row, "h")
        _make_spin(self.dur_m, dur_row, "m")
        _make_spin(self.dur_s, dur_row, "s")

        layout.addLayout(chunks_row)
        layout.addLayout(dur_row)

        # Wire signals
        self.chunks_slider.valueChanged.connect(self._chunks_slider_changed)
        self.chunks_spin.valueChanged.connect(self._chunks_spin_changed)
        self.dur_slider.valueChanged.connect(self._dur_slider_changed)
        self.dur_h.valueChanged.connect(self._dur_hms_changed)
        self.dur_m.valueChanged.connect(self._dur_hms_changed)
        self.dur_s.valueChanged.connect(self._dur_hms_changed)

    # -- Setters (keep both in sync without recursion) --

    # -- Helpers --

    def _hms_to_seconds(self) -> float:
        return (
            self.dur_h.value() * 3600
            + self.dur_m.value() * 60
            + self.dur_s.value()
        )

    def _seconds_to_hms(self, seconds: float):
        seconds = max(0, int(round(seconds)))
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        self.dur_h.setValue(h)
        self.dur_m.setValue(m)
        self.dur_s.setValue(s)

    # -- Setters (keep everything in sync without recursion) --

    def _apply_chunks(self, chunks: int):
        if self._busy:
            return
        self._busy = True
        try:
            chunks = max(2, chunks)
            self.chunks_slider.setValue(chunks)
            self.chunks_spin.setValue(chunks)
            if self._total > 0:
                dur = self._total / chunks
                self.dur_slider.setValue(max(1, int(dur)))
                self._seconds_to_hms(dur)
        finally:
            self._busy = False
        self.chunks_changed.emit(chunks)

    def _apply_duration(self, duration: float):
        if self._busy:
            return
        self._busy = True
        try:
            duration = max(1.0, duration)
            self.dur_slider.setValue(max(1, int(duration)))
            self._seconds_to_hms(duration)
            if self._total > 0 and duration > 0:
                chunks = max(2, int(self._total / duration))
                self.chunks_slider.setValue(chunks)
                self.chunks_spin.setValue(chunks)
        finally:
            self._busy = False
        self.duration_changed.emit(duration)

    # -- Slots --

    def _chunks_slider_changed(self, val):
        if not self._busy:
            self._apply_chunks(val)

    def _chunks_spin_changed(self, val):
        if not self._busy:
            self._apply_chunks(val)

    def _dur_slider_changed(self, val):
        if not self._busy:
            self._apply_duration(float(val))

    def _dur_hms_changed(self, _val):
        if not self._busy:
            self._apply_duration(self._hms_to_seconds())

    # -- Public --

    def set_total_duration(self, duration: float) -> None:
        self._total = duration
        max_chunks = min(50, max(2, int(duration)))
        self.chunks_slider.setMaximum(max_chunks)
        self.chunks_spin.setMaximum(max_chunks)
        self.dur_slider.setMaximum(max(1, int(duration)))
        self.dur_h.setMaximum(int(duration) // 3600)
        self._apply_chunks(4)

    @property
    def chunks(self) -> int:
        return self.chunks_spin.value()

    @property
    def duration(self) -> float:
        return self._hms_to_seconds()


# ---------------------------------------------------------------------------
# Full input panel
# ---------------------------------------------------------------------------

class InputPanel(QWidget):
    """
    Top bar: [File picker]        [Output Folder picker]
                                  [Chunks / Duration panel]
    """

    file_selected    = Signal(str)
    folder_selected  = Signal(str)
    chunks_changed   = Signal(int)
    duration_changed = Signal(float)
    language_changed = Signal(object)  # str | None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # File button (tall, left side)
        self.file_btn = PickerButton("📄  File?", "📄")
        self.file_btn.setFixedHeight(70)
        self.file_btn.setMinimumWidth(130)

        # Right column: folder button + chunk/duration panel
        right = QVBoxLayout()
        right.setSpacing(6)

        self.folder_btn = PickerButton("📁  Output Folder?", "📁")
        self.folder_btn.setFixedHeight(36)

        # Language selector
        lang_row = QHBoxLayout()
        lang_row.setSpacing(6)
        lang_lbl = QLabel("Language:")
        lang_lbl.setFixedWidth(58)
        self.lang_combo = QComboBox()
        for name, _ in _LANGUAGES:
            self.lang_combo.addItem(name)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(lang_lbl)
        lang_row.addWidget(self.lang_combo)

        self.chunk_panel = ChunkDurationPanel()
        self.chunk_panel.chunks_changed.connect(self.chunks_changed)
        self.chunk_panel.duration_changed.connect(self.duration_changed)

        right.addWidget(self.folder_btn)
        right.addLayout(lang_row)
        right.addWidget(self.chunk_panel)

        layout.addWidget(self.file_btn)
        layout.addStretch()
        layout.addLayout(right)

        self.file_btn.clicked.connect(self._pick_file)
        self.folder_btn.clicked.connect(self._pick_folder)

    def _on_language_changed(self, index: int):
        self.language_changed.emit(_LANGUAGES[index][1])

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "",
            "Audio Files (*.mp3 *.wav)"
        )
        if path:
            self.file_btn.set_path(path)
            default_folder = str(Path(path).parent)
            self.folder_btn.set_path(default_folder)
            self.file_selected.emit(path)

    def _pick_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.folder_btn.set_path(path)
            self.folder_selected.emit(path)

    def set_total_duration(self, duration: float) -> None:
        self.chunk_panel.set_total_duration(duration)

    @property
    def output_folder(self) -> str:
        return self.folder_btn.get_path()

    @property
    def chunks(self) -> int:
        return self.chunk_panel.chunks

    @property
    def language(self):
        return _LANGUAGES[self.lang_combo.currentIndex()][1]
