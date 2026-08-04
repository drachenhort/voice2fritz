# voice2fritz Call Log Dock — Design Spec

Date: 2026-08-04

## Purpose

Turn the Call Log from a separate modal dialog into a `QDockWidget`
attached to the main window, visible by default on startup — so recent
calls are always in view alongside the dialer, matching the dockable
"Recents" feel of the original mockup, rather than requiring a click to
open a popup.

Out of scope: docking Contacts or Settings (stays as regular dialogs —
this is Call Log only, per explicit user scoping). No change to the
underlying `call_log.py` data model or `MainWindow`'s call-logging
bookkeeping (already shipped) — this is a UI-container change only.

## Architecture

`CallLogDialog` (a `QDialog`) is replaced by `CallLogPanel` (a plain
`QWidget`) containing the same list-of-custom-row-widgets + Clear button
UI, minus the modal-specific behavior (`exec()`, `accept()`-on-select).
`MainWindow` wraps `CallLogPanel` in a `QDockWidget` at construction time,
docked to the right side, visible immediately — the log is part of the
main window's chrome from launch, not something opened on demand.

`log_button` changes from "open a dialog" to "toggle the dock's
visibility" — clicking it hides the dock if shown, shows it if hidden.
`callSelected` still exists as a signal (renamed conceptually to
"entry activated", same `Signal(str)` shape) so `MainWindow` can still
fill the dial field on double-click, but the dock itself does not close
or hide as a side effect of that — the prior dialog's "select closes the
window" behavior doesn't make sense for a persistent panel, and removing
it is a **deliberate behavior change**, not an oversight.

## Components

- `src/voice2fritz/gui/call_log_dialog.py` → renamed
  `src/voice2fritz/gui/call_log_panel.py`. `CallLogDialog(QDialog)` →
  `CallLogPanel(QWidget)`:
  - Same `entry_list: QListWidget`, `clear_button: QPushButton`,
    `_reload_list()`, `_on_clear_clicked()`, row-widget rendering
    (`_row_widget`, `_format_duration`, `_DIRECTION_ICONS`) — unchanged
    internals, just no longer a `QDialog` subclass.
  - `_on_item_activated` keeps emitting `entryActivated = Signal(str)`
    (renamed from `callSelected` since it's no longer "select-and-close"
    semantics) but drops the `self.accept()` call — nothing to accept,
    it's not modal.
  - No `resize()` call in `__init__` — the dock widget's own sizing
    (via `QDockWidget`, resizable by the user like any dock) replaces
    the old dialog's fixed initial size.
- `src/voice2fritz/gui/main_window.py` (modified):
  - `self.log_panel = CallLogPanel()` and
    `self.log_dock = QDockWidget("Call Log", self)`,
    `self.log_dock.setWidget(self.log_panel)`,
    `self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.log_dock)`
    — all in `__init__`, dock visible by default (no explicit `hide()`
    call needed; `QDockWidget` is visible once added unless told
    otherwise).
  - `log_panel.entryActivated.connect(self.number_edit.setText)`
    replaces the old `dialog.callSelected.connect(...)` wiring.
  - `_on_log_clicked` becomes:
    ```python
    def _on_log_clicked(self) -> None:
        self.log_dock.setVisible(not self.log_dock.isVisible())
    ```
    (no more `CallLogDialog(self)` construction/`exec()` — the panel
    already exists as part of the window, this just shows/hides it.)
    `log_panel.py`'s `_reload_list()` is called once at construction
    time (already the case, unchanged) and again by `_on_clear_clicked`
    — there's no need to reload on dock show/hide, since
    `_log_completed_call` doesn't currently push updates to an open
    panel. **Known limitation carried forward, not introduced by this
    change:** if a call completes while the dock is visible, the panel
    won't show the new entry until next reload (dock toggled off/on, or
    app restarted) — out of scope for this pass; `main_window.py` would
    need to call `self.log_panel._reload_list()` from
    `_log_completed_call` to fix this, which is a reasonable small
    follow-up but not part of "dock it," which is purely a container
    change.

## Data Flow

Unchanged from the shipped call-log feature — `MainWindow` still logs
completed calls via `call_log.append_call_log_entry` in
`_log_completed_call`. The only change is where the *viewer* for that
log lives: previously a modal dialog constructed fresh (and thus
re-reading the log file) every time Log was clicked; now a
long-lived panel constructed once at startup, shown/hidden by the Log
button, that only re-reads the log file on Clear or app restart (see
the known limitation above).

## Error Handling

No new failure modes — this is a container refactor, not new I/O or
network logic. Existing error handling in `call_log.py` (malformed/
missing file → empty list) is untouched.

## Testing

- `CallLogPanel`: unit-tested the same way `CallLogDialog` was —
  `pytest-qt`, monkeypatching `call_log.load_call_log`/`clear_call_log`.
  Tests updated for the new class name, the dropped
  `exec()`/`accept()`-adjacent assertions, and the renamed
  `entryActivated` signal (was `callSelected`).
- `MainWindow`: updated test for the dock-toggle behavior — clicking
  `log_button` twice should show then hide `log_dock` (assert
  `log_dock.isVisible()` toggles), and `log_panel.entryActivated`
  should still fill `number_edit` — replaces the old
  "opens dialog, dialog's signal fills the field" test.
