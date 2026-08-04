# Close-to-Tray Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Closing the main window asks Quit / Minimize to Tray / Cancel
instead of silently exiting. A system tray icon lets the user reopen or
quit while minimized. Answering an incoming call while hidden brings the
window back.

**Architecture:** `MainWindow` overrides `closeEvent`, delegating the
three-way decision to a small helper method (`_show_close_dialog`) so
tests can monkeypatch it without driving a real modal dialog. A
`QSystemTrayIcon` is created once in `__init__`, reusing the app's window
icon, with a context menu (Show / Quit) and click-to-show activation.
`_on_incoming_call_answered` gains a show/raise/activate call.

**Tech Stack:** PySide6 (`QSystemTrayIcon`, `QMenu`, `QMessageBox`), pytest + pytest-qt (offscreen platform — tray icon object construction is safe headless; `isSystemTrayAvailable()`/visual display are not exercised by tests).

## Global Constraints

- No persisted "don't ask again" preference — the close dialog appears
  every time.
- Tray menu's Quit action skips the confirmation dialog entirely.
- Declining an incoming call does not show the window; only answering
  does.
- `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip` required for every pytest run.

---

### Task 1: Close confirmation dialog

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Produces: `MainWindow._show_close_dialog(self) -> str`, returning one of
  `"quit"`, `"tray"`, `"cancel"`. `MainWindow.closeEvent(self, event)`
  calls it and acts on the result. Tests monkeypatch
  `_show_close_dialog` directly (via `monkeypatch.setattr(window,
  "_show_close_dialog", lambda: "quit")`) rather than driving the real
  `QMessageBox`, since a modal dialog can't be exercised headlessly.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_main_window.py`, after
`test_log_dock_holds_a_tab_widget_with_log_and_contacts`:

```python
def test_close_event_quit_accepts_the_close(qtbot, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "_show_close_dialog", lambda: "quit")

    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted()


def test_close_event_tray_ignores_close_and_hides_window(qtbot, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.show()
    monkeypatch.setattr(window, "_show_close_dialog", lambda: "tray")

    event = QCloseEvent()
    window.closeEvent(event)

    assert not event.isAccepted()
    assert not window.isVisible()


def test_close_event_cancel_ignores_close_and_keeps_window_visible(qtbot, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.show()
    monkeypatch.setattr(window, "_show_close_dialog", lambda: "cancel")

    event = QCloseEvent()
    window.closeEvent(event)

    assert not event.isAccepted()
    assert window.isVisible()
```

- [ ] **Step 2: Run to verify these fail**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_main_window.py -v -k close_event`
Expected: FAIL — `MainWindow` has no `closeEvent` override or
`_show_close_dialog` yet (`AttributeError`).

- [ ] **Step 3: Add the import**

At the top of `main_window.py`, add `QMessageBox` to the existing
`from PySide6.QtWidgets import (...)` block (alphabetical, after
`QMainWindow`).

- [ ] **Step 4: Add `_show_close_dialog` and `closeEvent`**

Add these two methods to `MainWindow`, anywhere among the other
`_on_*`/event-handling methods (e.g. right after `keyPressEvent`):

```python
    def _show_close_dialog(self) -> str:
        box = QMessageBox(self)
        box.setWindowTitle("Close voice2fritz?")
        box.setText("Quit voice2fritz, or keep it running in the tray?")
        quit_button = box.addButton("Quit", QMessageBox.ButtonRole.AcceptRole)
        tray_button = box.addButton("Minimize to Tray", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(tray_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is quit_button:
            return "quit"
        if clicked is tray_button:
            return "tray"
        return "cancel"

    def closeEvent(self, event) -> None:
        choice = self._show_close_dialog()
        if choice == "quit":
            event.accept()
        elif choice == "tray":
            event.ignore()
            self.hide()
        else:
            event.ignore()
```

- [ ] **Step 5: Run to verify pass**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_main_window.py -v -k close_event`
Expected: PASS (3 tests)

- [ ] **Step 6: Run the full test suite**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest`
Expected: PASS, no regressions.

- [ ] **Step 7: Commit**

```bash
git add src/voice2fritz/gui/main_window.py tests/test_main_window.py
git commit -m "feat: confirm Quit/Minimize to Tray/Cancel on window close"
```

---

### Task 2: System tray icon

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: nothing new from Task 1 directly, but relies on the window
  now being hideable (Task 1) for the tray icon to be useful.
- Produces: `MainWindow.tray_icon: QSystemTrayIcon`,
  `MainWindow._show_window_action: QAction`,
  `MainWindow._quit_action: QAction` — tray menu actions, named so tests
  can trigger them directly (`window._show_window_action.trigger()`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_main_window.py`:

```python
def test_tray_icon_created_with_show_and_quit_actions(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    assert window.tray_icon is not None
    menu_actions = window.tray_icon.contextMenu().actions()
    assert window._show_window_action in menu_actions
    assert window._quit_action in menu_actions


def test_tray_show_action_shows_and_raises_window(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.hide()

    window._show_window_action.trigger()

    assert window.isVisible()


def test_tray_activation_shows_window(qtbot):
    from PySide6.QtWidgets import QSystemTrayIcon

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.hide()

    window._on_tray_activated(QSystemTrayIcon.ActivationReason.Trigger)

    assert window.isVisible()


def test_tray_quit_action_quits_without_confirmation(qtbot, monkeypatch):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    called = []
    monkeypatch.setattr(window, "_show_close_dialog", lambda: called.append(True))

    quit_calls = []
    from PySide6.QtWidgets import QApplication
    monkeypatch.setattr(QApplication.instance(), "quit", lambda: quit_calls.append(True))

    window._quit_action.trigger()

    assert quit_calls == [True]
    assert called == []
```

- [ ] **Step 2: Run to verify these fail**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_main_window.py -v -k tray`
Expected: FAIL — `MainWindow` has no `tray_icon` attribute yet.

- [ ] **Step 3: Add imports**

Add `QSystemTrayIcon` and `QMenu` to the `PySide6.QtWidgets` import block
(alphabetical placement), and add a new import line:

```python
from PySide6.QtGui import QAction
```

(placed after the existing `from PySide6.QtCore import Qt` line, since
`main_window.py` currently has no `QtGui` import).

- [ ] **Step 4: Build the tray icon in `__init__`**

Add at the end of `__init__`, after `restore_saved_devices(self.sip_engine)`:

```python
        self._show_window_action = QAction("Show voice2fritz", self)
        self._show_window_action.triggered.connect(self._show_and_raise)
        self._quit_action = QAction("Quit", self)
        self._quit_action.triggered.connect(self._on_tray_quit)

        tray_menu = QMenu(self)
        tray_menu.addAction(self._show_window_action)
        tray_menu.addAction(self._quit_action)

        self.tray_icon = QSystemTrayIcon(self.windowIcon(), self)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
```

- [ ] **Step 5: Add the handler methods**

Add these methods to `MainWindow`, near `_show_close_dialog`:

```python
    def _show_and_raise(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_and_raise()

    def _on_tray_quit(self) -> None:
        QApplication.instance().quit()
```

- [ ] **Step 6: Add the `QApplication` import**

Add `QApplication` to the `PySide6.QtWidgets` import block if not already
present (it isn't, in `main_window.py` today).

- [ ] **Step 7: Run to verify pass**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_main_window.py -v -k tray`
Expected: PASS (4 tests)

- [ ] **Step 8: Run the full test suite**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest`
Expected: PASS, no regressions.

- [ ] **Step 9: Commit**

```bash
git add src/voice2fritz/gui/main_window.py tests/test_main_window.py
git commit -m "feat: system tray icon with show/quit menu"
```

---

### Task 3: Show window on answering a call while hidden

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `MainWindow._show_and_raise` (Task 2).
- Produces: no new public interface — `_on_incoming_call_answered` calls
  `self._show_and_raise()`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_main_window.py`:

```python
def test_answering_incoming_call_shows_window_if_hidden(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.hide()

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    window.incoming_popup.answered.emit()

    assert window.isVisible()


def test_declining_incoming_call_does_not_show_window_if_hidden(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.hide()

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    window.incoming_popup.declined.emit()

    assert not window.isVisible()
```

- [ ] **Step 2: Run to verify the first test fails**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_main_window.py -v -k "answering_incoming_call_shows_window or declining_incoming_call_does_not_show"`
Expected: first test FAILs (window stays hidden), second PASSes already
(declining never touches visibility).

- [ ] **Step 3: Update `_on_incoming_call_answered`**

In `main_window.py`, add `self._show_and_raise()` as the first line of
`_on_incoming_call_answered`:

```python
    def _on_incoming_call_answered(self) -> None:
        self._show_and_raise()
        self._close_incoming_popup()
        self.sip_engine.answer(self._active_call)
        self.hangup_button.setEnabled(True)
        self.mute_button.setEnabled(True)
        self._set_dtmf_mode(True)
        name = self._contact_name_for(self._call_number)
        self.call_details.set_active_call(name, self._call_number or "")
```

- [ ] **Step 4: Run to verify pass**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_main_window.py -v -k "answering_incoming_call_shows_window or declining_incoming_call_does_not_show"`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full test suite**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest`
Expected: PASS, no regressions.

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/gui/main_window.py tests/test_main_window.py
git commit -m "feat: show and raise window when answering a call while hidden"
```

---

## Manual verification (GUI is visible in this session)

- [ ] Close the window (X button / Alt+F4) — confirm the Quit/Minimize to
  Tray/Cancel dialog appears.
- [ ] Choose Cancel — window stays open.
- [ ] Choose Minimize to Tray — window hides, a tray icon appears in the
  system tray.
- [ ] Click the tray icon — window reappears.
- [ ] Right-click the tray icon — confirm "Show voice2fritz" and "Quit"
  are present; Quit exits immediately with no confirmation dialog.
- [ ] Minimize to tray, then trigger an incoming call (or simulate via
  test) and Answer it — confirm the window reappears automatically.
- [ ] Minimize to tray, then Decline an incoming call — confirm the
  window stays hidden.
