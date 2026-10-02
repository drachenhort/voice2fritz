import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from voice2fritz import config, i18n
from voice2fritz.gui import theme
from voice2fritz.gui.main_window import RESTART_EXIT_CODE, MainWindow
from voice2fritz.gui.settings_dialog import SettingsDialog
from voice2fritz.sip_engine import SipEngine

ICON_PATH = Path(__file__).parent / "gui" / "resources" / "icon.png"


def main() -> None:
    app = QApplication(sys.argv)
    app.setDesktopFileName("voice2fritz")

    i18n.set_language(config.load_language())
    if i18n.current_language() != "en":
        # Qt's own texts: standard dialog buttons, text field context menus.
        qt_translator = QTranslator(app)
        translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if qt_translator.load(QLocale(i18n.current_language()), "qtbase", "_", translations):
            app.installTranslator(qt_translator)

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

    window.register_account(account)

    exit_code = app.exec()
    sip_engine.stop()
    if exit_code == RESTART_EXIT_CODE:
        _relaunch()
    sys.exit(exit_code)


def _relaunch() -> None:
    if getattr(sys, "frozen", False):
        # Packaged build (PyInstaller): the executable is the app itself.
        command = [sys.executable, *sys.argv[1:]]
    else:
        command = [sys.executable, "-m", "voice2fritz.main", *sys.argv[1:]]
    if sys.platform == "win32":
        # os.execv on Windows starts a detached copy and returns oddly; spawn and exit instead.
        subprocess.Popen(command)
        sys.exit(0)
    os.execv(command[0], command)


if __name__ == "__main__":
    main()
