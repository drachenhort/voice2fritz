from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CallDetailsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        self.state_label = QLabel()
        self.duration_label = QLabel()
        self.duration_label.setStyleSheet("color: #8a8f98;")

        self.mute_button = QPushButton("🔇")
        self.mute_button.setToolTip("Mute")
        self.mute_button.setCheckable(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.name_label)
        layout.addWidget(self.state_label)
        layout.addWidget(self.duration_label)
        layout.addWidget(self.mute_button)
        layout.addStretch()

        self._seconds = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self.set_idle()

    def set_active_call(self, name: str, number: str) -> None:
        self.name_label.setText(name if name else number)
        self.state_label.setText("Active")
        self._seconds = 0
        self.duration_label.setText("0:00")
        self.mute_button.setEnabled(True)
        self._timer.start()

    def set_idle(self) -> None:
        self._timer.stop()
        self.name_label.setText("No active call")
        self.state_label.setText("")
        self.duration_label.setText("")
        self.mute_button.setEnabled(False)
        self.mute_button.setChecked(False)

    def set_state_text(self, text: str) -> None:
        self.state_label.setText(text)

    def _tick(self) -> None:
        self._seconds += 1
        minutes, secs = divmod(self._seconds, 60)
        self.duration_label.setText(f"{minutes}:{secs:02d}")
