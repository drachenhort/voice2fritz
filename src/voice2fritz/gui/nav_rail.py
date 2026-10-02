from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget

from voice2fritz.i18n import tr

_PAGES = [
    ("dialpad", "\N{BLACK TELEPHONE}", "Dialpad"),
    ("contacts", "\N{BUST IN SILHOUETTE}", "Contacts"),
    ("call_log", "\N{ALARM CLOCK}", "Call Log"),
    ("settings", "\N{GEAR}", "Settings"),
]


class NavRail(QWidget):
    pageSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("navRail")

        self.buttons: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(6)

        for index, (name, glyph, title) in enumerate(_PAGES):
            button = QPushButton(glyph)
            button.setObjectName("railButton")
            button.setCheckable(True)
            button.setToolTip(tr(title))
            button.clicked.connect(lambda checked=False, i=index: self.pageSelected.emit(i))
            group.addButton(button)
            layout.addWidget(button)
            self.buttons[name] = button

        layout.addStretch()
        self.buttons["dialpad"].setChecked(True)

    def set_current_index(self, index: int) -> None:
        """Check the matching rail button without re-emitting pageSelected."""
        for i, (name, _, _) in enumerate(_PAGES):
            if i == index:
                self.buttons[name].setChecked(True)
                break
