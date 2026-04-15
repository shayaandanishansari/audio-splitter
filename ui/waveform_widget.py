import numpy as np
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import (
    QColor, QLinearGradient, QPainter, QPen, QBrush, QPolygon, QFont,
)
from PySide6.QtWidgets import QWidget


MARKER_HIT_RADIUS = 10   # px — how close to a marker line counts as a hit
TRIANGLE_H = 14          # height of the marker triangle indicator
TRIANGLE_W = 9           # half-width


class WaveformWidget(QWidget):
    """
    Custom widget that paints:
      • an audio waveform (pink/purple gradient bars, symmetric around center)
      • a red playhead tape
      • draggable black split-marker tapes with numbered triangle indicators

    Signals
    -------
    marker_moved(index, seconds)   — emitted continuously while dragging
    marker_selected(index)         — index == -1 means deselected
    seek_requested(seconds)        — click on empty waveform area
    """

    marker_moved = Signal(int, float)
    marker_selected = Signal(int)
    seek_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._waveform: np.ndarray = np.array([], dtype=np.float32)
        self._duration: float = 0.0
        self._playhead: float = 0.0
        self._markers: list[float] = []        # seconds
        self._selected: int = -1               # index or -1
        self._dragging: bool = False

        self.setMinimumHeight(180)
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load_waveform(self, waveform: np.ndarray, duration: float) -> None:
        self._waveform = waveform
        self._duration = duration
        self._playhead = 0.0
        self._markers = []
        self._selected = -1
        self._dragging = False
        self.update()

    def set_markers(self, positions: list[float]) -> None:
        self._markers = list(positions)
        self.update()

    def get_marker_positions(self) -> list[float]:
        return list(self._markers)

    def set_playhead(self, seconds: float) -> None:
        self._playhead = seconds
        self.update()

    @property
    def selected_marker(self) -> int:
        return self._selected

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _to_x(self, seconds: float) -> int:
        if self._duration <= 0 or self.width() <= 0:
            return 0
        return int(seconds / self._duration * self.width())

    def _to_seconds(self, x: int) -> float:
        if self._duration <= 0 or self.width() <= 0:
            return 0.0
        return float(max(0.0, min(self._duration, x / self.width() * self._duration)))

    def _hit_marker(self, x: int) -> int:
        for i, pos in enumerate(self._markers):
            if abs(x - self._to_x(pos)) <= MARKER_HIT_RADIUS:
                return i
        return -1

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w, h = self.width(), self.height()
        mid = h // 2

        # ── background ──────────────────────────────────────────────
        painter.fillRect(0, 0, w, h, QColor("#1e1616"))

        # ── waveform bars ────────────────────────────────────────────
        if len(self._waveform) > 0:
            n = len(self._waveform)
            bar_w = max(1, w // n)

            for i, amp in enumerate(self._waveform):
                x = int(i * w / n)
                bar_h = max(1, int(amp * (h * 0.46)))

                grad = QLinearGradient(x, mid - bar_h, x, mid + bar_h)
                grad.setColorAt(0.0,  QColor(230, 160, 210, 180))
                grad.setColorAt(0.45, QColor(190, 100, 210, 255))
                grad.setColorAt(0.5,  QColor(210, 120, 220, 255))
                grad.setColorAt(0.55, QColor(190, 100, 210, 255))
                grad.setColorAt(1.0,  QColor(230, 160, 210, 180))

                painter.fillRect(x, mid - bar_h, bar_w, bar_h * 2, grad)

        # ── split markers (black tapes) ───────────────────────────────
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        for i, pos in enumerate(self._markers):
            x = self._to_x(pos)
            selected = (i == self._selected)

            line_color = QColor("#ffffff") if selected else QColor("#111111")
            tri_fill   = QColor("#eeeeee") if selected else QColor("#222222")
            text_color = QColor("#111111") if selected else QColor("#eeeeee")

            # Vertical line
            pen = QPen(line_color, 2)
            painter.setPen(pen)
            painter.drawLine(x, TRIANGLE_H, x, h)

            # Triangle pointing down from top
            painter.setBrush(QBrush(tri_fill))
            painter.setPen(Qt.PenStyle.NoPen)
            tri = QPolygon([
                QPoint(x,              TRIANGLE_H),
                QPoint(x - TRIANGLE_W, 0),
                QPoint(x + TRIANGLE_W, 0),
            ])
            painter.drawPolygon(tri)

            # Number label centred in triangle
            painter.setPen(QPen(text_color))
            f = QFont()
            f.setPointSize(6)
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(x - TRIANGLE_W, 0, TRIANGLE_W * 2, TRIANGLE_H, Qt.AlignmentFlag.AlignCenter, str(i + 1))

        # ── playhead (red tape) ───────────────────────────────────────
        px = self._to_x(self._playhead)
        painter.setPen(QPen(QColor("#e03030"), 2))
        painter.drawLine(px, 0, px, h)

        painter.end()

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        x = int(event.position().x())
        hit = self._hit_marker(x)

        if hit >= 0:
            self._selected = hit
            self._dragging = True
            self.marker_selected.emit(hit)
        else:
            self._selected = -1
            self._dragging = False
            self.marker_selected.emit(-1)
            self.seek_requested.emit(self._to_seconds(x))

        self.update()

    def mouseMoveEvent(self, event):
        x = int(event.position().x())

        if self._dragging and self._selected >= 0:
            seconds = self._to_seconds(x)
            self._markers[self._selected] = seconds
            self.marker_moved.emit(self._selected, seconds)
            self.update()
        else:
            hit = self._hit_marker(x)
            self.setCursor(
                Qt.CursorShape.SizeHorCursor if hit >= 0
                else Qt.CursorShape.ArrowCursor
            )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
