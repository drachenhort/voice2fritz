# voice2fritz DTMF Support — Design Spec

Date: 2026-08-04

## Purpose

Let the user send DTMF tones during an active call (needed for IVR menus,
voicemail systems, automated phone trees), by reusing the existing
dialpad buttons instead of adding a separate keypad.

Deferred from v1 per the design spec's stated v2 candidate list; this is
that feature.

## Behavior Change

`MainWindow`'s existing dialpad buttons (`1`-`9`, `*`, `0`, `#`) become
context-sensitive:

- **No active call:** clicking a digit appends it to `number_edit` — the
  existing v1 behavior, unchanged.
- **Active call:** clicking a digit sends that digit as a DTMF tone over
  the call instead, and does NOT modify `number_edit`.

The mode is determined by whether `MainWindow._active_call` is set (the
same flag that already gates hangup/mute availability).

## Components

- `SipEngine.send_dtmf(call, digit: str) -> None` (new method in
  `sip_engine.py`) — wraps pjsua2's `Call.dialDtmf(digit)`, which sends
  RFC 2833 out-of-band DTMF by default (PJSIP's standard approach, no
  extra configuration needed).
- `MainWindow._on_digit_clicked(digit)` (modified) — branches on
  `self._active_call is None`: append to `number_edit` if `None`,
  otherwise call `self.sip_engine.send_dtmf(self._active_call, digit)`.

## Visual Feedback

Dialpad buttons (`self.digit_buttons`) get a dynamic Qt property,
`dtmfMode`, toggled to `True` when a call becomes active (alongside the
existing `hangup_button`/`mute_button` `setEnabled(True)` calls in
`_on_call_clicked` and `_on_incoming_call`'s accept path) and back to
`False` when the call ends (alongside `_on_call_ended`'s existing
resets). A new QSS rule in `theme.py` gives buttons with
`dtmfMode="true"` a subtle blue border, distinguishing DTMF mode from
normal dialing without restructuring the layout.

Setting a dynamic property requires calling
`style().unpolish(button)`/`style().polish(button)` (or re-injecting the
stylesheet) on each affected button after `setProperty()` for Qt to
re-evaluate the QSS selector — this is a known Qt/QSS requirement, not
optional boilerplate.

## Data Flow

No change to the existing call-state signal flow
(`registrationStateChanged`, `callStateChanged`, `callEnded`,
`incomingCall`). DTMF sending is a one-way, fire-and-forget action
triggered directly by a button click — pjsua2 does not emit a
success/failure callback for `dialDtmf()` that needs handling.

## Error Handling

If `dialDtmf()` is called with no active call or media, pjsua2 raises a
`pjsua2.Error`. Since the button click is already gated by
`self._active_call is not None`, this should not occur in practice; no
additional guard is added beyond that existing check (consistent with
the rest of `sip_engine.py`'s style of trusting its preconditions).

## Testing

- `sip_engine.send_dtmf`: no automated test possible (pjsua2 unavailable
  in CI/dev sandboxes without a real build) — verified via `py_compile`
  and a manual real-call test sending DTMF to an IVR/voicemail system,
  consistent with how the rest of `sip_engine.py` is verified.
- `MainWindow`: new unit test using the existing `FakeSipEngine` pattern
  — with `_active_call` set (simulate via `make_call` or
  `incomingCall`+accept), clicking a digit button calls
  `engine.send_dtmf(active_call, digit)` and does NOT change
  `number_edit.text()`. Existing dialpad tests (no active call) remain
  unchanged and continue to verify the append behavior.
- No test asserts on the `dtmfMode` QSS visual styling (consistent with
  the rest of the app's approach to appearance — not unit-testable,
  verified manually).
