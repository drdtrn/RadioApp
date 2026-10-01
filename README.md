# radio-tui

A radio player for Kosovo and Saudi Arabia stations, with two desktop front
ends sharing the same station list, settings and playback engine:

- `radio-gui` — a desktop window, built on [Qt (PySide6)](https://doc.qt.io/qtforpython-6/)
- `radio` — a terminal UI, built on [Textual](https://textual.textualize.io/)

Playback runs through [mpv](https://mpv.io/); station data comes from the
[Radio Browser](https://www.radio-browser.info/) API.

There's also an [Android app](#android-app) in `android/`: the same stations
and features, as a native Kotlin app.

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

## Android app

`android/` holds a native Android version (Kotlin, Jetpack Compose, Media3
ExoPlayer). The Python code can't run there — mpv and its IPC socket, Qt and
Textual don't exist on Android — so the station model, Radio Browser client,
cache and search are ported to Kotlin with the same behaviour. It adds what a
phone needs: playback keeps going with the screen off or the app closed,
with controls in the notification, on the lock screen and on Bluetooth /
headset buttons; it pauses for calls and when headphones are unplugged.

Same as the desktop app: the Kosovo / Saudi Arabia tabs (swipe or tap), search
by name or tag, the song title when a station sends one, ⚠ on streams that
fail, a 24-hour station cache with offline fallback, and the volume, sort
order and last tab are remembered. Pull down (or tap ⟳) to refresh the list.
Resuming after a pause rejoins the live broadcast.

Back and Home leave the radio playing in the background. To stop it and
close the app, tap ⏻ — in the app, in the notification or on the lock
screen — or swipe the app away from the recent apps.

### Install on a phone

Copy the APK (`radio-release.apk`, see below) to the phone and open it. Android asks once to
allow installing apps from that source (Files, Chrome, …). Android 8.0+.

Installing a newer build over an older one only works if both were signed
with the same key (see below); otherwise uninstall the old one first.

### Build the APK

Needs a JDK 17+ and the Android SDK (platform 37, build-tools 36). Android
Studio installs both; with only the
[command-line tools](https://developer.android.com/studio#command-line-tools-only)
unpacked into `~/Android/Sdk/cmdline-tools/latest`:

    export ANDROID_HOME=~/Android/Sdk
    $ANDROID_HOME/cmdline-tools/latest/bin/android --sdk=$ANDROID_HOME \
        sdk install platforms/android-37.0 build-tools/36.0.0 platform-tools
    echo "sdk.dir=$ANDROID_HOME" > android/local.properties

    cd android
    ./gradlew testDebugUnitTest      # unit tests (station model, API client + cache, search, titles)
    ./gradlew assembleRelease        # → app/build/outputs/apk/release/radio-release.apk

Release builds are signed with the key named in `android/keystore.properties`
(not in git):

    storeFile=/home/you/.android/radio-release.jks
    storePassword=…
    keyAlias=radio
    keyPassword=…

Create a key once with `keytool -genkeypair -keystore ~/.android/radio-release.jks
-storetype PKCS12 -alias radio -keyalg RSA -keysize 4096 -validity 36500`, and
back up the `.jks` — every future update must be signed with it. Without
`keystore.properties` the release build falls back to the per-machine debug key.

## Development

    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    pytest

The GUI tests run headless (`QT_QPA_PLATFORM=offscreen`, set in
`tests/conftest.py`), so no display is needed.
