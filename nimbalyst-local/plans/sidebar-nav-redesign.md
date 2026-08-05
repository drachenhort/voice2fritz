---
planStatus:
  planId: plan-sidebar-nav-redesign
  title: Sidebar Navigation Redesign
  status: in-development
  planType: feature
  priority: medium
  owner: sigma
  stakeholders: []
  tags: [voice2fritz, ui, redesign]
  created: "2026-08-05"
  updated: "2026-08-05T14:43:56.000Z"
  progress: 0
---

# Sidebar Navigation Redesign

## Objective

Implement [sidebar-nav-redesign.mockup.html](../mockups/sidebar-nav-redesign.mockup.html)
against the real app: a persistent left icon rail (Dialpad / Contacts / Call Log / Settings)
replacing the current dock-and-dialog layout.

## Correction to the mockup's premise

The mockup's stated problem — "Contacts and Settings are both trapped behind modal dialogs" —
is only half true. Re-reading `main_window.py` before implementing: `ContactsPanel` already
lives docked in a `QTabWidget` next to `CallLogPanel`, always visible on the left
(`log_dock`/`log_tabs`). The `Contacts` nav button opens a *second*, redundant `ContactsDialog`
just for picking a number into the dialer. Only **Settings** is genuinely dialog-only.

User chose to rebuild to match the mockup exactly anyway, aware this removes the
already-working docked layout (169 tests currently cover it) in favor of rail-switched pages.
This plan proceeds on that basis.

## Gaps the mockup didn't specify, resolved here

1. **Hangup/Mute controls.** The mockup's status-strip "call chip" is static text (name,
   duration, "Muted"). With Contacts/Call Log/Settings now full pages instead of docks, Hangup
   and Mute need a home reachable from every page. Call Details (name/state/duration) moves
   out of its dock into the same bar, and Hangup/Mute move there too as real buttons — the
   whole `CallDetailsPanel` becomes a horizontal bar under the status strip, visible only
   during a call, rather than the mockup's plain-text chip.
2. **Recents beside the dialpad vs. Call Log as a rail page.** The mockup shows both. Building
   both would mean two independently-updating views over the same call log — implementing
   Call Log only as a rail page, not duplicated as a mini-list next to the dialpad. Flagged as
   a deliberate deviation, not an oversight.
3. **`ContactsDialog` becomes dead code** once Contacts is a rail page hosting `ContactsPanel`
   directly — deleted, along with `tests/test_contacts_dialog.py`.

## Design

### `SettingsPanel(QWidget)` — new, extracted from `SettingsDialog`

Move the form (`host_edit`, `username_edit`, `password_edit`, `capture_combo`,
`speaker_combo`, `google_priority_checkbox`, `save_button`) and all of `_on_save`/
`_on_capture_changed`/`_on_playback_changed`/`_save_device_selection` into a `QWidget`.
`SettingsDialog` becomes a thin wrapper (`ContactsDialog`'s old pattern) so its 11 existing
tests keep passing unchanged. `MainWindow`'s Settings page embeds `SettingsPanel` directly.

### `NavRail(QWidget)` — new

Vertical column of four checkable `QPushButton`s (`objectName="railButton"`), icons only
(reuse existing emoji: 📞 👤 🕐 ⚙), exclusive selection via a `QButtonGroup`. Emits
`pageSelected(int)`.

### `MainWindow` restructuring

- Remove `call_details_dock`, `log_dock`, `log_tabs`.
- Central widget becomes `QHBoxLayout(nav_rail, QVBoxLayout(status_bar, call_bar, QStackedWidget))`.
- `QStackedWidget` pages, in rail order: Dialpad (existing number row + keypad + call button,
  minus the old inline Hangup/Mute row), Contacts (`ContactsPanel` instance), Call Log
  (`CallLogPanel` instance), Settings (`SettingsPanel` instance).
- `status_bar`: LED + account label (unchanged content, no dock).
- `call_bar`: `CallDetailsPanel`, restyled horizontal, with Hangup/Mute buttons appended;
  hidden via `setVisible(False)` when idle, shown on `_on_call_clicked`/`_on_incoming_call_answered`,
  hidden again in `_on_call_ended`.
- `contacts_panel.contactSelected` and `log_panel.entryActivated` still connect to
  `number_edit.setText` — unchanged, just different parent.

## Tasks

1. Extract `SettingsPanel`; re-point `SettingsDialog` to wrap it. Run `test_settings_dialog.py`
   unchanged — must still pass.
2. Add `NavRail`.
3. Restructure `MainWindow.__init__`: remove docks, build rail + stacked pages + call bar.
4. Move Hangup/Mute wiring from the old `call_control_row` onto the call bar's buttons.
5. Delete `contacts_dialog.py` and `tests/test_contacts_dialog.py`.
6. Update `tests/test_main_window.py`:
   - Delete the 6 dock-structure tests (`test_log_dock_*`, `test_call_details_dock*`,
     `test_docks_have_fixed_width...`).
   - Delete `test_contacts_button_opens_dialog_and_fills_number_on_selection`; replace with a
     test that clicking the Contacts rail button shows the Contacts page.
   - Add: rail switches `QStackedWidget.currentIndex`; call bar hidden when idle, visible
     with an active call, hidden again after hangup.
7. QSS for `railButton` (rounded, muted icon, accent when checked) and `callBar` background,
   matching the mockup's rail/status-chip colors.
8. Run full suite; fix fallout.
9. Launch the real app (`run.sh`) and screenshot idle + active-call states against the mockup.

## Known fidelity gaps (real Qt vs. the HTML mockup)

- Font rendering and exact icon glyphs will differ — mockup uses emoji placeholders, not real
  `QIcon`s.
- Call bar is a restyled `CallDetailsPanel`, not the mockup's plain-text chip — it needs to
  stay interactive (Hangup/Mute), which the mockup didn't draw.
- No FRITZ!Box device-status/DECT panel, no Hold/Transfer/Video — out of scope, same as the
  mockup's own "Future" strip.
