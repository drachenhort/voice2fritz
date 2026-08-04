import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from voice2fritz import config
from voice2fritz.gui import theme
from voice2fritz.gui.main_window import MainWindow
from voice2fritz.gui.settings_dialog import SettingsDialog
from voice2fritz.sip_engine import SipEngine

ICON_PATH = Path(__file__).parent / "gui" / "resources" / "icon.png"


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.DARK_STYLESHEET)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    app.setQuitOnLastWindowClosed(False)

    sip_engine = SipEngine()
    sip_engine.start()

    account = config.load_config()
    if account is None:
        dialog = SettingsDialog(sip_engine)
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            sip_engine.stop()
            sys.exit(0)
        account = config.load_config()

    window = MainWindow(sip_engine)
    window.show()

    password = config.get_password(account.username) or ""
    sip_engine.register(account.host, account.username, password)

    exit_code = app.exec()
    sip_engine.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
