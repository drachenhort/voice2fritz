---
planStatus:
  planId: plan-dialpad-button-restyle
  title: Dialpad Button Graphic Restyle
  status: draft
  planType: improvement
  priority: medium
  owner: sigma
  stakeholders: []
  tags: [voice2fritz, ui, qss, dialpad]
  created: "2026-08-05"
  updated: "2026-08-05T10:58:34.000Z"
  progress: 0
---

# Dialpad Button Graphic Restyle

## Objective

Make the dialpad read as a real phone keypad: rounded-square keys with T9 letters rendered *inside* the key, distinct press feedback, keyboard-press highlight, keys that scale with the window, dimmed `*`/`#`, and a CALL button in the same visual language.

## Current State

- Each key is a plain `QPushButton` with `objectName="dialpadButton"`, `setMinimumSize(80, 18)`.
- T9 letters are a **separate** `QLabel` stacked under the button inside a per-cell `QVBoxLayout`/`QWidget`, styled with an **inline** stylesheet (`color: #8a8f98; font-size: 11px;`), fixed height 14.
- Grid uses `setHorizontalSpacing(2)`, `setVerticalSpacing(0)`, zero margins.
- Cells are `QSizePolicy.Fixed/Fixed`, so the keypad never grows with the window.
- Styling in `theme.py` is only: `font-weight: bold; font-size: 22px; padding: 1px;`

Relevant code: `src/voice2fritz/gui/main_window.py:60-95`, `:200-205` (keyPressEvent), `:266-270` (`_set_dtmf_mode`), `src/voice2fritz/gui/theme.py:50-54`.

## Hard Constraints

1. **`button.text()` must stay the bare digit.** `_on_digit_clicked` feeds it into `SipEngine.send_dtmf`. No rich text, no `"2\nABC"`, no HTML in the button text.
2. **`window.digit_buttons[digit]` must stay a clickable `QPushButton`.** Tests call `.click()` on it (`tests/test_main_window.py:136-226`).
3. **`dtmfMode` dynamic property + its QSS border rule must keep working** (`theme.py:46-48`, test at `tests/test_main_window.py:212`).
4. Restyle is **visual only** — no change to dial/DTMF/call behaviour.

## Design

### 1. `DialpadButton(QPushButton)` — new class in `main_window.py`

Replaces the `QLabel` + wrapper-`QWidget` cell entirely; the button *is* the grid cell.

- `__init__(self, digit: str, letters: str)` — `super().__init__(digit)`, stores `self.letters = letters`, sets `objectName("dialpadButton")`.
- `paintEvent`: call `super().paintEvent(event)` (draws the QSS background/border and the centered digit), then paint `self.letters` with a `QPainter` in the bottom strip of the rect (small font, muted `#8a8f98`, horizontally centered).
- The digit is pushed off dead-center by a QSS `padding-bottom` on `#dialpadButton`, leaving the bottom strip free for the letters — no manual bevel drawing needed.
- Expose `letters` as a plain attribute so tests can assert it.

*Fallback if `padding-bottom` doesn't shift the label as expected across Qt styles:* drop `super().paintEvent`, draw the bevel via `QStyleOptionButton` + `style().drawControl(CE_PushButtonBevel, ...)` and paint both digit and letters manually. Try the simple path first.

`digit_letter_labels` is deleted. `tests/test_main_window.py:741` changes from
`window.digit_letter_labels[d].text() == letters` to `window.digit_buttons[d].letters == letters`.

### 2. Responsive sizing

- Drop the fixed-size cell wrapper; add `DialpadButton` straight into `dialpad_grid`.
- `setMinimumSize(64, 54)`, `setSizePolicy(Expanding, Expanding)`.
- `dialpad_grid.setHorizontalSpacing(6)` / `setVerticalSpacing(6)`; set `setColumnStretch(c, 1)` for 0..2 and `setRowStretch(r, 1)` for 0..3 so keys share space evenly.
- Give `dialpad_column` a stretch factor so the grid absorbs vertical growth rather than the number row.

### 3. QSS (`theme.py`)

```
QPushButton#dialpadButton {
    background-color: #262935;
    border: 1px solid #383c48;
    border-radius: 14px;
    font-weight: bold;
    font-size: 24px;
    padding-bottom: 16px;   /* frees bottom strip for T9 letters */
}
QPushButton#dialpadButton:hover   { background-color: #333747; }
QPushButton#dialpadButton:pressed { background-color: #3d4152; }
QPushButton#dialpadButton[symbolKey="true"] { color: #8a8f98; }

/* DTMF: colour the key only while it is being pressed during a call */
QPushButton#dialpadButton[dtmfMode="true"]:pressed {
    background-color: #4a9eff;
    color: #ffffff;
}
```

`*` and `#` get `setProperty("symbolKey", True)` at construction.

### 3a. DTMF feedback — press-time only

The old rule `QPushButton[dtmfMode="true"] { border: 2px solid #4a9eff; }` is **removed**.
It put a 2px accent border on all twelve keys for the whole call, which at the new key size
reads as a wall of blue and competes with the status LED and the Mute button (visible in the
full-window mockup).

Instead the accent appears **only on the key being pressed, and only while a call is active**:

- idle press → `#3d4152`, a subtle step up from the `#333747` hover
- DTMF press → accent `#4a9eff` with white text

Blue therefore means "tone sent" rather than "mode is on", which is information the user
actually needs at the moment they need it. `_set_dtmf_mode` and the `dtmfMode` property stay
exactly as they are — the property now selects the flash colour instead of a static border,
so `tests/test_main_window.py:212` keeps passing unchanged.

**Known trade-off:** nothing on the keypad now signals that keys send tones instead of
appending to the number field. The Call Details dock already shows "Active" during a call,
which is the closest existing cue. If that proves too subtle in real use, add a one-line
hint to `CallDetailsPanel` rather than putting the border back — deliberately deferred, not
overlooked.

### 4. Keyboard press highlight

In `keyPressEvent`, when the typed char maps to a key, reuse the `:pressed` state instead of
inventing a second highlight mechanism:

```python
button = self.digit_buttons[text]
button.setDown(True)
QTimer.singleShot(120, lambda b=button: b.setDown(False))
```

Guard against a repeat-fire leaving a key stuck down (re-arming the timer is fine; the final
timer always clears it).

### 5. CALL button

Match the key language: `border-radius: 14px`, `min-height: 48px`, `font-size: 16px`, keep
green `#2fa84f` with the existing hover. It stays full-width under the grid.

## Tasks

1. Add `DialpadButton` class with `paintEvent` letter rendering.
2. Rewrite the grid construction loop in `MainWindow.__init__` — drop cell wrapper + `QLabel`, add stretches, set `symbolKey` on `*`/`#`.
3. Update `theme.py` QSS (dialpad key, hover, pressed, symbolKey, CALL button).
4. Delete the static `QPushButton[dtmfMode="true"]` border rule; add the
   `[dtmfMode="true"]:pressed` accent rule in its place (§3a).
5. Add keyboard-press flash in `keyPressEvent` (import `QTimer`).
6. Update `tests/test_main_window.py:741` to assert `digit_buttons[d].letters`.
7. Add a test that `*`/`#` carry `symbolKey is True` and digits don't.
8. Add a test that `keyPressEvent` with `"5"` leaves `digit_buttons["5"].isDown()` True immediately after (timer not yet fired).
9. Run full suite (151 tests currently pass) — confirm no regression, especially DTMF and `dtmfMode`.
10. Launch the app and eyeball the keypad against the mockup — including pressing a key
    mid-call to confirm the accent flash actually fires on the DTMF path.

## Risks

- **`padding-bottom` behaviour is style-engine dependent.** If the digit doesn't move up, fall back to full manual painting (see §1).
- **`:pressed` QSS vs `setDown(True)`** — confirm `setDown` actually triggers the `:pressed` selector (it should; `:pressed` maps to the sunken state). If not, use a `pressedFlash` dynamic property + unpolish/polish, like `_set_dtmf_mode` already does.
- Letters at small window sizes could collide with the digit; the 54px min-height plus a
  minimum letter font size guards this.
- **Attribute-plus-pseudo-state selectors** (`[dtmfMode="true"]:pressed`) are supported by Qt
  Style Sheets, but the property must already be set when the state changes — it is, since
  `_set_dtmf_mode` runs on call start and re-polishes. Verify on hardware (task 10); if the
  combined selector misbehaves, set the colour imperatively in `_on_digit_clicked` instead.

## Mockups

[Dialpad keys and states](../mockups/dialpad-restyle.mockup.html "width=520 height=720")

[Full window, idle and active call](../mockups/full-window-restyle.mockup.html "width=700 height=1180")

## Out of Scope

- Round/circular keys (considered, rejected — T9 letters have nowhere to go).
- Tab-bar navigation, Hold/Transfer, any non-dialpad panel restyle.
- Light theme.
