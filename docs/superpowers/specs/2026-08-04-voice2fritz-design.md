# voice2fritz — Design Spec

Date: 2026-08-04

## Purpose

A Linux desktop SIP softphone that registers with a FRITZ!Box as a VoIP
client. Lets the user make and receive calls over a headset, with easy
selection of which audio device to speak into and which to hear through.

Out of scope for v1: contacts list, call history, DTMF dialpad, multiple
SIP accounts/lines, voicemail integration, non-Linux platforms.

## Architecture

- **GUI**: PySide6 desktop app, single main window.
- **SIP/RTP engine**: pjsua2 (PJSIP's Python bindings) — handles SIP
  registration, call signaling, RTP media, and codec negotiation.
- **Config**: account settings (FRITZ!Box host, SIP username) stored in
  `~/.config/voice2fritz/config.json`. SIP password stored in the system
  keyring (via `python-keyring`, Secret Service API) — never written to
  the plaintext config file.
- Single SIP account/line for v1.

## Components

1. `sip_engine.py` — Wraps pjsua2's `Endpoint`/`Account`/`Call` objects.
   Exposes registration-state, incoming-call, and call-state-change
   callbacks to the rest of the app.
2. `audio.py` — Enumerates and selects audio input/output devices via
   pjsua2's `AudioDevManager`.
3. `config.py` — Loads/saves account config JSON; reads/writes the SIP
   password via `python-keyring`.
4. `gui/main_window.py` — Main window: number entry field, call/hangup/mute
   buttons, audio input/output device dropdowns, registration status
   indicator.
5. `gui/settings_dialog.py` — Lets the user enter FRITZ!Box host and SIP
   username/password; password is written to the keyring, never to the
   config file.
6. `main.py` — App entrypoint. Wires pjsua2 callbacks to Qt signals.

## Data Flow

1. App launch → `config.py` loads account config.
2. If an account is configured, `sip_engine.py` registers with the
   FRITZ!Box via pjsua2. GUI reflects registration status.
3. User enters a number and clicks Call → `sip_engine.make_call()` creates
   a pjsua2 `Call`. State callbacks (proceeding / confirmed / disconnected)
   are marshaled from the pjsua2 worker thread to the Qt main thread via
   Qt signals, and the GUI updates accordingly.
4. Incoming call → pjsua2 callback fires on its worker thread → marshaled
   to Qt via signal → GUI shows an incoming-call prompt (accept/reject).

**Threading constraint**: pjsua2 runs its own worker thread. All pjsua2
callbacks must cross into the Qt thread via signal/slot — never touch Qt
widgets directly from the pjsua2 thread.

## Error Handling

- **Registration failure** (bad credentials, network unreachable): status
  bar shows the error; user can retry manually. App does not crash.
- **Call failure** (busy, no answer, network drop mid-call): GUI shows a
  status message and resets call state cleanly.
- **Audio device unavailable at launch** (e.g. headset unplugged): falls
  back to the system default device, logs a warning, does not block app
  startup.

## Testing

pjsua2 requires a real SIP server and audio hardware to exercise call
flow, so there is no meaningful way to unit-test registration/call/audio
behavior in isolation.

- Unit tests: `config.py` and the keyring integration layer, with the
  keyring mocked.
- Integration testing: manual, against a real FRITZ!Box SIP account —
  covering register, dial, answer, hangup, mute, and device switching.
- No automated SIP call tests for v1.
