# radio-tui

A radio player for Kosovo and Saudi Arabia stations, with two front ends
sharing the same station list, settings and playback engine:

- `radio-gui` — a desktop window, built on [Qt (PySide6)](https://doc.qt.io/qtforpython-6/)
- `radio` — a terminal UI, built on [Textual](https://textual.textualize.io/)

Playback runs through [mpv](https://mpv.io/); station data comes from the
[Radio Browser](https://www.radio-browser.info/) API.

## Install (any Linux distro)

Install mpv and [uv](https://docs.astral.sh/uv/):

    sudo pacman -S mpv      # Arch
    sudo apt install mpv    # Ubuntu / Debian
    sudo dnf install mpv    # Fedora
    curl -LsSf https://astral.sh/uv/install.sh | sh

Then install the app straight from GitHub:

    uv tool install git+https://github.com/drdtrn/RadioApp@gui-radio

This puts `radio-gui` and `radio` on your `$PATH` (in `~/.local/bin`). uv
downloads its own Python if the system one is older than 3.11 (e.g. Ubuntu
22.04 ships 3.10). To pick up new commits later:

    uv tool upgrade radio-tui

## Launcher entry

Copy a desktop entry so the app shows up in your launcher (GNOME, KDE,
Walker, …):

    mkdir -p ~/.local/share/applications
    cp packaging/radio-gui.desktop ~/.local/share/applications/

If the launcher can't start it, your desktop session doesn't have
`~/.local/bin` on its `$PATH` yet — log out and back in, or replace
`Exec=radio-gui` with the full path printed by `which radio-gui`.

`packaging/radio-tui.desktop` launches the terminal version instead, via
`ghostty -e radio` — edit its `Exec=` line if you use a different terminal.

## Desktop app (`radio-gui`)

Double-click a station (or select it and press Enter) to play it. The bar
at the bottom shows the station, the current song/programme title when the
station sends one, a play/pause button and a volume slider. Stations whose
stream fails to play are marked ⚠. Column headers sort the list.

| Key                    | Action                         |
|------------------------|---------------------------------|
| Space                  | Pause / resume                  |
| Ctrl+Up / Ctrl+Down    | Volume up / down                |
| Ctrl+F                 | Search the current tab          |
| Enter (in search box)  | Jump to the first match         |
| Ctrl+Tab               | Switch Kosovo / Saudi Arabia    |
| F5 / Ctrl+R            | Force-refresh station list      |
| Ctrl+Q                 | Quit                            |

## Terminal app (`radio`)

| Key                    | Action                       |
|------------------------|-------------------------------|
| Ctrl+Left / Ctrl+Right | Switch Kosovo / Saudi Arabia |
| ↑ / ↓                  | Move station selection        |
| Enter                  | Play highlighted station      |
| Space                  | Pause / resume                |
| + / - or ← / →         | Volume up / down               |
| r                      | Force-refresh station list    |
| q                      | Quit                           |

Plain Tab / Shift+Tab do not switch country tabs — they follow Textual's
normal behavior of cycling keyboard focus between widgets (search box,
station table, tab bar).

Note: playback shortcuts (Space, +/-, arrows) only work when the station table is focused — click or Tab out of the search box first.

Both apps keep volume and the last-used tab in
`~/.config/radio-tui/config.toml`, and cache the station list in
`~/.cache/radio-tui/stations.json` (refreshed once a day).

## Troubleshooting

- **`Could not load the Qt platform plugin "xcb"`** — Qt needs one extra
  system library on X11 sessions: `sudo apt install libxcb-cursor0`
  (Ubuntu / Debian) or `sudo dnf install xcb-util-cursor` (Fedora).

## Development

    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    pytest

The GUI tests run headless (`QT_QPA_PLATFORM=offscreen`, set in
`tests/conftest.py`), so no display is needed.
