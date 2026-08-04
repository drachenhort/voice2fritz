from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_AVATAR_COLORS = [
    "#e07a5f", "#3d5a80", "#81b29a", "#f2cc8f",
    "#9b5de5", "#00bbf9", "#f15bb5", "#00f5d4",
]
_FALLBACK_AVATAR_COLOR = "#5c6370"


def _initials(name: str) -> str:
    words = name.split()
    return "".join(word[0] for word in words[:2]).upper()


def _avatar_color(name: str) -> str:
    return _AVATAR_COLORS[sum(ord(c) for c in name) % len(_AVATAR_COLORS)]


class IncomingCallPopup(QWidget):
    answered = Signal()
    declined = Signal()

    def __init__(self, name: str, number: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Incoming call")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        avatar_text = _initials(name) if name else "📞"
        avatar_color = _avatar_color(name) if name else _FALLBACK_AVATAR_COLOR
        self.avatar_label = QLabel(avatar_text)
        self.avatar_label.setFixedSize(64, 64)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setStyleSheet(
            f"background-color: {avatar_color}; color: #ffffff; "
            f"border-radius: 32px; font-size: 22px; font-weight: bold;"
        )

        self.name_label = QLabel(name if name else number)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.number_label = QLabel(number)
        self.number_label.setStyleSheet("color: #8a8f98;")
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.answer_button = QPushButton("📞 Answer")
        self.answer_button.setObjectName("callButton")
        self.decline_button = QPushButton("✕ Decline")
        self.decline_button.setObjectName("deleteButton")

        button_row = QHBoxLayout()
        button_row.addWidget(self.decline_button)
        button_row.addWidget(self.answer_button)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)
        layout.addWidget(self.number_label)
        layout.addLayout(button_row)

        self.answer_button.clicked.connect(self.answered.emit)
        self.decline_button.clicked.connect(self.declined.emit)
