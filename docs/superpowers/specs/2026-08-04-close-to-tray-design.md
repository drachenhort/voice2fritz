# Close-to-Tray — Design

## Problem

Closing the main window currently quits the app outright, killing SIP
registration and any chance of receiving incoming calls. There's no way
to keep voice2fritz reachable in the background without leaving the
window open.

## Behavior

### Closing the window

Overriding `MainWindow.closeEvent`: show a `QMessageBox` with three
actions:

- **Quit** — accept the close event, app exits normally.
- **Minimize to Tray** — ignore the close event (`event.ignore()`), hide
  the window (`self.hide()`) instead.
- **Cancel** — ignore the close event, window stays open/visible.

No "don't ask again" option — the dialog appears every time the window is
closed.

### System tray icon

A `QSystemTrayIcon` is created at startup (in `MainWindow.__init__`),
reusing the existing app icon (`gui/resources/icon.png`), and shown
immediately — present for the whole app lifetime, not just after the
first minimize.

- **Activation** (click) on the tray icon shows and raises the main
  window (`self.show()`, `self.raise_()`, `self.activateWindow()`).
- **Context menu** (right-click): two actions —
  - "Show voice2fritz" — same as activation.
  - "Quit" — calls `QApplication.quit()` directly, no confirmation
    dialog (already an explicit, unambiguous action from the tray menu).

### Incoming calls while hidden

`IncomingCallPopup` is already a separate top-level widget independent of
`MainWindow`'s visibility, so it continues to show and ring while the main
window is hidden in the tray — no change needed there.

On **Answer**, `MainWindow._on_incoming_call_answered` additionally shows
and raises the main window (same show/raise/activate sequence as tray
activation), so accepting a call while minimized brings the call UI (Call
Details, Hangup/Mute) back into view. Declining does not show the window —
only answering does.

## Out of scope

- No persisted "don't ask again" preference.
- No tray icon badge/notification-count behavior.
- No change to SIP registration/call handling — purely a window
  visibility feature.
