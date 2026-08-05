# radio-tui

A terminal radio player for Kosovo and Saudi Arabia stations, built on
[Textual](https://textual.textualize.io/) and [mpv](https://mpv.io/).
Station data comes from the [Radio Browser](https://www.radio-browser.info/)
API.

## Install

    pacman -S mpv
    pipx install .

This puts a `radio` command on your `$PATH`.

## Launcher entry (Walker)

Copy the desktop entry so radio-tui shows up in Omarchy's app launcher:

    mkdir -p ~/.local/share/applications
    cp packaging/radio-tui.desktop ~/.local/share/applications/

The entry launches `alacritty -e radio` by default — edit the `Exec=` line
in `packaging/radio-tui.desktop` if you use a different terminal (foot,
kitty, ghostty, etc.).

## Usage

    radio

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

## Development

    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    pytest
