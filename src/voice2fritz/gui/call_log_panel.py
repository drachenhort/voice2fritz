from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import call_log as call_log_module

_DIRECTION_ICONS = {
    "outgoing": ("↗", "#2fa84f"),
    "incoming": ("↙", "#dddddd"),
    "missed": ("↙", "#a83b2f"),
}


def _format_duration(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d}"


def _row_widget(entry: call_log_module.CallLogEntry) -> QWidget:
    icon_char, icon_color = _DIRECTION_ICONS.get(entry.direction, ("?", "#dddddd"))

    icon_label = QLabel(icon_char)
    icon_label.setStyleSheet(f"color: {icon_color}; font-size: 16px;")

    title = entry.name if entry.name else entry.number
    name_label = QLabel(title)
    name_label.setStyleSheet("font-weight: bold;")

    if entry.direction == "missed":
        subtext = entry.number
    else:
        subtext = f"{entry.number} · {_format_duration(entry.duration_seconds)}"
    subtext_label = QLabel(subtext)
    subtext_label.setStyleSheet("color: #8a8f98; font-size: 11px;")

    text_column = QVBoxLayout()
    text_column.setSpacing(0)
    text_column.addWidget(name_label)
    text_column.addWidget(subtext_label)

    time_label = QLabel(entry.timestamp.split("T")[-1][:5] if "T" in entry.timestamp else entry.timestamp)
    time_label.setStyleSheet("color: #8a8f98;")

    row = QHBoxLayout()
    row.addWidget(icon_label)
    row.addLayout(text_column)
    row.addStretch()
    row.addWidget(time_label)

    widget = QWidget()
    widget.setLayout(row)
    return widget


class CallLogPanel(QWidget):
    entryActivated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.entry_list = QListWidget()
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("deleteButton")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.entry_list)
        layout.addWidget(self.clear_button)

        self.entry_list.itemDoubleClicked.connect(self._on_item_activated)
        self.clear_button.clicked.connect(self._on_clear_clicked)

        self._reload_list()

    def _reload_list(self) -> None:
        self.entry_list.clear()
        entries = list(reversed(call_log_module.load_call_log()))
        for entry in entries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setSizeHint(_row_widget(entry).sizeHint())
            self.entry_list.addItem(item)
            self.entry_list.setItemWidget(item, _row_widget(entry))

    def _on_clear_clicked(self) -> None:
        call_log_module.clear_call_log()
        self._reload_list()

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        entry: call_log_module.CallLogEntry = item.data(Qt.ItemDataRole.UserRole)
        self.entryActivated.emit(entry.number)
