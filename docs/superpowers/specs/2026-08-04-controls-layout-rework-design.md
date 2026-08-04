# Controls Layout Rework — Design

## Problem

Non-dialpad controls look unplanned: a vertical column of Hangup/Settings/
Contacts/Log buttons sits beside the dialpad, while Mute lives alone at the
top of the Call Details dock (visually reads as "on top of the Call Log").
Dialpad and Call button already look good and are unchanged by this work.

## Goal

Group the remaining controls by function and give them a consistent,
designed look:

- **Nav group** — Settings, Contacts, Log: app-level actions, not tied to
  an active call.
- **Call-control group** — Hangup, Mute: in-call actions.

## Layout

- **Nav row**: new horizontal row directly under the SIP status LED row,
  spanning the window width, three equal-width buttons (Settings ⚙ /
  Contacts / Log).
- **Call-control row**: new horizontal row directly below the CALL button,
  inside the dialpad column — Hangup ✕ / Mute 🔇 side by side. Both
  disabled when there's no active call (existing enable/disable logic,
  just re-targeted).
- The old `controls_column` (vertical Hangup/Settings/Contacts/Log stack)
  is removed entirely.
- `CallDetailsPanel` becomes a pure display widget (name/state/duration) —
  `mute_button` moves out of it and into `MainWindow`, owned and wired the
  same way it is today (`sip_engine.set_mute` on click).
- Call Details dock and Call Log dock keep their current stacked
  left-side docking; only the leftover top-of-dock button disappears.

## Styling

New QSS class `navButton` in `theme.py`, applied to all six buttons
(Settings, Contacts, Log, Hangup, Mute) — one shared visual family,
distinct from `dialpadButton`: medium-bold text/icon, fixed comfortable
padding, consistent size across the group.

## Out of scope

- Dialpad, T9 letters, CALL button — unchanged, already approved.
- Call Details / Call Log dock behavior (docking, resizing, visibility
  toggle) — unchanged.
- No new functionality — pure layout/styling rework of existing buttons.
