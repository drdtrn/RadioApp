# radio-tui: Terminal radio player for Kosovo & Saudi Arabia stations

**Status:** Approved
**Date:** 2026-08-04

## Summary

A terminal-based (TUI) internet radio player for Omarchy (Hyprland/Arch), scoped
to stations from Kosovo and Saudi Arabia — replicating the core of a Firefox
radio-player extension ("Radio Player by keller") as a native CLI tool. Station
data comes from the Radio Browser API; playback is delegated to `mpv`.

## Goals

- Browse and search radio stations from Kosovo and Saudi Arabia.
- Play a selected station and show live "now playing" (ICY) metadata.
- Feel native to an Omarchy/Hyprland workflow: launchable as a plain CLI command
  and from the Walker app launcher.

## Non-goals (v1)

- Favorites/presets.
- Recently-played history.
- Countries beyond Kosovo and Saudi Arabia.
- A GUI/GTK or Waybar-widget interface.

## Architecture

```
┌─────────────┐     HTTP (JSON)     ┌──────────────────┐
│  radio-tui   │ ──────────────────▶ │ Radio Browser API │
│  (Textual)   │ ◀────────────────── │ (radio-browser.info)│
└──────┬───────┘   station list       └──────────────────┘
       │ JSON IPC over unix socket
       ▼
┌─────────────┐
│     mpv      │──▶ system audio (PipeWire)
│ (subprocess) │
└─────────────┘
```

- **radio-tui** (Python + [Textual](https://textual.textualize.io/)) is the
  whole application: fetches/filters stations, renders the UI, and drives
  playback.
- **mpv** is launched once as a background subprocess
  (`mpv --idle --input-ipc-server=<socket>`) and controlled entirely over its
  JSON IPC socket: load a stream URL, pause/resume, set volume, and poll the
  `media-title` property for the ICY "now playing" text.
- **Radio Browser API** ([radio-browser.info](https://www.radio-browser.info/))
  is a free, open, community-maintained directory of internet radio stations.
  Its `countrycode` filter (`XK` for Kosovo, `SA` for Saudi Arabia) gives
  exactly the scoped station lists, each with a stream URL, name, tags/genre,
  and language.
- The station list is fetched on startup and cached locally so the app still
  opens and plays previously-seen stations if the API is briefly unreachable.

## Features & UX

Single-screen Textual layout:

```
┌ radio-tui ──────────────────────────────────────────────┐
│ [Kosovo] [Saudi Arabia]      Search: ______________     │
├───────────────────────────────────────────────────────────┤
│ ▶ Radio Kosova e Lirë          news/talk        128kbps  │
│   Radio Dukagjini              pop                       │
│   MTV Music                    pop, hits                 │
│   ...                                                     │
├───────────────────────────────────────────────────────────┤
│ ♪ Now playing: Radio Kosova e Lirë                        │
│   "Lajmet e orës" — vol 70%  [space]=pause [+/-]=vol      │
└───────────────────────────────────────────────────────────┘
```

- **Tabs** switch between the two country lists — a client-side filter on the
  already-fetched combined station list, no extra API calls per tab switch.
- **Search box** does live substring filtering on name/tags within the
  current tab.
- **Keybindings:**
  - `Enter` — play the highlighted station
  - `Space` — pause/resume
  - `+`/`-` or `←`/`→` — adjust mpv volume
  - `r` — force a station-list refresh from the API, bypassing the cache
  - `q` — quit (also kills the mpv subprocess)
- **Now-playing bar** shows the station name plus the live ICY title,
  refreshed by polling mpv's IPC every ~2s while a stream is active.

## Storage & config

XDG-standard locations:

- `~/.cache/radio-tui/stations.json` — cached station list (Kosovo + Saudi
  Arabia) with a fetch timestamp; auto-refreshed if older than 24h, or on
  demand via `r`.
- `~/.config/radio-tui/config.toml` — last volume level, last-selected
  tab/country, optional mpv binary path override.

No favorites or history are stored, per the non-goals above.

## Error handling

- **API unreachable on startup** → fall back to the cached `stations.json` if
  present, with a small "using cached list from `<date>`" notice. If no cache
  exists yet, show a clear error message and exit cleanly (no traceback).
- **Station stream fails to play** (dead link, timeout) → mpv reports an
  error over IPC; the UI marks that station "⚠ unavailable" for the session
  and stays on the list rather than crashing.
- **mpv not installed** → detected at startup with a friendly message
  ("install with `pacman -S mpv`") instead of a raw traceback.
- **No now-playing metadata available** (some streams don't send ICY titles)
  → now-playing bar shows just the station name, no title line.

## Testing

- `pytest` unit tests, with mocked HTTP/socket calls, for the two pieces with
  real logic:
  - Radio Browser client: country filtering, caching/staleness logic.
  - mpv IPC wrapper: command formatting, response parsing.
- A couple of smoke tests using Textual's own test/pilot harness (launch,
  switch tab, search filters) — not exhaustive UI coverage.

## Installation & packaging

- Packaged as a small Python project (`pyproject.toml`), installed via
  `pipx install .` (or `uv tool install .`) so `radio` lands on `$PATH`
  without touching system Python.
- A `.desktop` file added to `~/.local/share/applications/` so the app shows
  up in Walker, launching the default terminal with `radio` as the command.
- Runtime dependency: `mpv`, installed via `pacman -S mpv` (documented in the
  README).

## Open questions / follow-ups (not blocking v1)

- Final app/binary name — using `radio-tui` as the project name and `radio`
  as the installed command for now; easy to rename later if it collides with
  something.
