from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import call_log as call_log_module
from voice2fritz import contacts as contacts_module
from voice2fritz.i18n import tr

_DIRECTION_ICONS = {
    "outgoing": ("↗", "#2fa84f"),
    "incoming": ("↙", "#dddddd"),
    "missed": ("↙", "#a83b2f"),
}


def _format_duration(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d}"


class _CallLogRow(QWidget):
    """One call log entry; its action bar shows only while the entry is selected."""

    dialClicked = Signal()
    editClicked = Signal()
    saveClicked = Signal()

    def __init__(self, entry: call_log_module.CallLogEntry, is_saved_contact: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("callLogRow")
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

        summary_row = QHBoxLayout()
        summary_row.addWidget(icon_label)
        summary_row.addLayout(text_column)
        summary_row.addStretch()
        summary_row.addWidget(time_label)

        self.dial_button = QPushButton(tr("Redial") if entry.direction == "outgoing" else tr("Call back"))
        self.dial_button.setObjectName("addButton")
        self.edit_button = QPushButton(tr("Edit"))
        self.edit_button.setToolTip(tr("Edit the number on the dialpad before calling"))
        self.save_button = QPushButton(tr("Save"))
        self.save_button.setToolTip(tr("Save to contacts"))
        self.save_button.setVisible(not is_saved_contact)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.addWidget(self.dial_button)
        action_row.addWidget(self.edit_button)
        action_row.addWidget(self.save_button)
        action_row.addStretch()

        self.actions = QWidget()
        self.actions.setObjectName("callLogActions")
        self.actions.setLayout(action_row)
        self.actions.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addLayout(summary_row)
        layout.addWidget(self.actions)

        self.dial_button.clicked.connect(self.dialClicked.emit)
        self.edit_button.clicked.connect(self.editClicked.emit)
        self.save_button.clicked.connect(self.saveClicked.emit)

    def set_actions_visible(self, visible: bool) -> None:
        self.actions.setVisible(visible)


class CallLogPanel(QWidget):
    entryActivated = Signal(str)
    dialRequested = Signal(str)
    editRequested = Signal(str)
    contactSaved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.entry_list = QListWidget()
        self.clear_button = QPushButton(tr("Clear"))
        self.clear_button.setObjectName("deleteButton")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.entry_list)
        layout.addWidget(self.clear_button)

        self.entry_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.entry_list.itemDoubleClicked.connect(self._on_item_activated)
        self.entry_list.currentItemChanged.connect(self._on_current_item_changed)
        self.entry_list.customContextMenuRequested.connect(self._on_context_menu_requested)
        self.clear_button.clicked.connect(self._on_clear_clicked)

        self._reload_list()

    def _reload_list(self) -> None:
        self.entry_list.clear()
        saved_numbers = {contact.number for contact in contacts_module.load_contacts()}
        entries = list(reversed(call_log_module.load_call_log()))
        for entry in entries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry)
            row = _CallLogRow(entry, is_saved_contact=entry.number in saved_numbers)
            row.dialClicked.connect(lambda entry=entry: self.dialRequested.emit(entry.number))
            row.editClicked.connect(lambda entry=entry: self.editRequested.emit(entry.number))
            row.saveClicked.connect(lambda entry=entry: self._save_to_contacts(entry))
            self.entry_list.addItem(item)
            self.entry_list.setItemWidget(item, row)
            # Size after the row is in the list, so it matches the later re-measurements.
            item.setSizeHint(row.sizeHint())

    def row_for(self, item: QListWidgetItem) -> "_CallLogRow":
        return self.entry_list.itemWidget(item)

    def _on_current_item_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        for item, visible in ((previous, False), (current, True)):
            if item is None:
                continue
            row = self.row_for(item)
            row.set_actions_visible(visible)
            item.setSizeHint(row.sizeHint())

    def _on_clear_clicked(self) -> None:
        call_log_module.clear_call_log()
        self._reload_list()

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        entry: call_log_module.CallLogEntry = item.data(Qt.ItemDataRole.UserRole)
        self.entryActivated.emit(entry.number)

    def _build_context_menu(self, item: QListWidgetItem) -> QMenu:
        entry: call_log_module.CallLogEntry = item.data(Qt.ItemDataRole.UserRole)
        label = tr("Redial") if entry.direction == "outgoing" else tr("Call back")
        menu = QMenu(self)
        dial_action = menu.addAction(label)
        dial_action.triggered.connect(lambda: self.dialRequested.emit(entry.number))
        if not any(contact.number == entry.number for contact in contacts_module.load_contacts()):
            save_action = menu.addAction(tr("Save to contacts…"))
            save_action.triggered.connect(lambda: self._save_to_contacts(entry))
        return menu

    def _prompt_contact_name(self, number: str, default_name: str) -> str | None:
        name, accepted = QInputDialog.getText(
            self, tr("Save to contacts"), tr("Name for {number}:", number=number), text=default_name
        )
        return name.strip() if accepted else None

    def _save_to_contacts(self, entry: call_log_module.CallLogEntry) -> None:
        name = self._prompt_contact_name(entry.number, entry.name)
        if not name:
            return
        contacts_module.add_contact(name, entry.number)
        self.contactSaved.emit()
        # The number is a contact now; offer saving no more.
        for row_index in range(self.entry_list.count()):
            item = self.entry_list.item(row_index)
            if item.data(Qt.ItemDataRole.UserRole).number == entry.number:
                row = self.row_for(item)
                row.save_button.setVisible(False)
                item.setSizeHint(row.sizeHint())

    def _on_context_menu_requested(self, pos) -> None:
        item = self.entry_list.itemAt(pos)
        if item is None:
            return
        self._build_context_menu(item).exec(self.entry_list.viewport().mapToGlobal(pos))
