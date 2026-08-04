# Contacts Tab — Design

## Problem

Contacts is only reachable via a modal dialog. The Call Log dock sits
right there in the main window at all times — adding a Contacts tab
alongside it lets the user click over instead of opening a dialog, while
the modal dialog stays available too (Contacts nav button unchanged).

## Components

### `ContactsPanel(QWidget)` — new, `src/voice2fritz/gui/contacts_panel.py`

Extraction of `ContactsDialog`'s current content and logic, unchanged
behavior:

- `contact_table`, sort row, add row, button row (Delete/Select/Sync
  Google) — same widgets, same layout.
- `contactSelected = Signal(str)` — emitted on double-click or Select
  button, same as today.
- **Difference from the dialog:** selecting a contact only emits the
  signal — no `accept()`/close call, since there's no dialog to close.
- `_reload_list`, `_on_sort_changed`, `_on_add_clicked`,
  `_on_delete_clicked`, `_on_sync_clicked` — moved over unchanged.

### `ContactsDialog(QDialog)` — rewritten as a thin wrapper

- Embeds a `ContactsPanel` as its only content.
- Forwards `contactSelected` to its own `contactSelected` signal.
- On `contactSelected`, calls `self.accept()` (preserves today's
  select-and-close behavior for the modal entry point).
- Keeps its `setWindowTitle("Contacts")` / `resize(480, 480)`.

### `MainWindow` changes

- `log_dock`'s widget becomes a `QTabWidget` with two tabs:
  - "Call Log" → existing `self.log_panel` (`CallLogPanel`), unchanged.
  - "Contacts" → new `self.contacts_panel` (`ContactsPanel`).
- `log_dock`'s title is cleared (`QDockWidget("", self)` or
  `setWindowTitle("")`) — the tab labels already identify the content.
- `self.contacts_panel.contactSelected` wired to
  `self.number_edit.setText`, same pattern as
  `self.log_panel.entryActivated`.
- Dock stays fixed-width (260px) / `NoDockWidgetFeatures` — unchanged
  from current pinned-in-place behavior.
- Existing "Contacts" nav button keeps opening `ContactsDialog` modally,
  unchanged.

## Out of scope

- No change to `contacts.py`, `google_contacts.py`, or contact data model.
- No change to the modal dialog's outward behavior/signal contract.
- No removal of the Contacts nav button (kept per explicit decision).
