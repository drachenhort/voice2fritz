import sys

from PySide6.QtWidgets import QApplication

from voice2fritz import config
from voice2fritz.gui.main_window import MainWindow
from voice2fritz.gui.settings_dialog import SettingsDialog
from voice2fritz.sip_engine import SipEngine


def main() -> None:
    app = QApplication(sys.argv)

    sip_engine = SipEngine()
    sip_engine.start()

    account = config.load_config()
    if account is None:
        dialog = SettingsDialog()
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            sys.exit(0)
        account = config.load_config()

    password = config.get_password(account.username) or ""
    sip_engine.register(account.host, account.username, password)

    window = MainWindow(sip_engine)
    window.show()

    exit_code = app.exec()
    sip_engine.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
