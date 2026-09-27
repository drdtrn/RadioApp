"""Textual TUI application for browsing and playing radio stations."""
from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Footer, Header, Input, Static, TabbedContent, TabPane

from radio_tui import config as config_module
from radio_tui import radio_browser
from radio_tui.config import CACHE_PATH, CONFIG_PATH, COUNTRIES
from radio_tui.models import Station
from radio_tui.mpv_controller import MPVController
from radio_tui.radio_browser import NoStationsAvailable

VOLUME_STEP = 5


class RadioApp(App):
    """Browse and play radio stations from Kosovo and Saudi Arabia."""

    BINDINGS = [
        ("r", "refresh_stations", "Refresh"),
        ("space", "toggle_pause", "Pause/Resume"),
        ("plus", "volume_up", "Vol+"),
        ("right", "volume_up", "Vol+"),
        ("minus", "volume_down", "Vol-"),
        ("left", "volume_down", "Vol-"),
        ("ctrl+right", "next_tab", "Next tab"),
        ("ctrl+left", "prev_tab", "Prev tab"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        cache_path: Path = CACHE_PATH,
        config_path: Path = CONFIG_PATH,
        mpv=None,
    ):
        super().__init__()
        self._cache_path = cache_path
        self._config_path = config_path
        self._mpv_override = mpv
        self._stations_by_country: dict[str, list[Station]] = {code: [] for code, _ in COUNTRIES}
        self._current_station: Station | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            for code, label in COUNTRIES:
                with TabPane(label, id=f"tab-{code}"):
                    with Vertical():
                        yield Input(placeholder="Search…", id=f"search-{code}")
                        yield DataTable(id=f"table-{code}")
        yield Static("", id="now-playing")
        yield Footer()

    def on_mount(self) -> None:
        self._config = config_module.load_config(self._config_path)
        self.mpv = self._mpv_override or MPVController(mpv_binary=self._config.mpv_binary)
        try:
            self.mpv.start()
        except OSError as error:
            self.exit(return_code=1, message=str(error))
            return

        for code, _ in COUNTRIES:
            table = self.query_one(f"#table-{code}", DataTable)
            table.add_columns("Name", "Tags", "Bitrate")
            table.cursor_type = "row"

        valid_codes = [code for code, _ in COUNTRIES]
        if self._config.last_tab in valid_codes:
            self.query_one(TabbedContent).active = f"tab-{self._config.last_tab}"

        self.load_stations()
        self.set_interval(2.0, self._poll_now_playing)

    @work(exclusive=True, thread=True)
    def load_stations(self, force_refresh: bool = False) -> None:
        try:
            result = radio_browser.get_stations(
                self._cache_path,
                [code for code, _ in COUNTRIES],
                force_refresh=force_refresh,
            )
        except NoStationsAvailable as error:
            self.call_from_thread(self.exit, return_code=1, message=str(error))
            return

        self.call_from_thread(self._apply_stations, result.stations)

    def _apply_stations(self, stations: list[Station]) -> None:
        for code, _ in COUNTRIES:
            self._stations_by_country[code] = [
                station for station in stations if station.countrycode == code
            ]
        self._refresh_tables()

    def _refresh_tables(self) -> None:
        for code, _ in COUNTRIES:
            self._render_table(code, self._stations_by_country[code])

    def _render_table(self, code: str, stations: list[Station]) -> None:
        table = self.query_one(f"#table-{code}", DataTable)
        table.clear()
        for station in stations:
            name = f"⚠ {station.name}" if not station.available else station.name
            tags = ", ".join(station.tags)
            table.add_row(name, tags, str(station.bitrate), key=station.stationuuid)

    def on_input_changed(self, event: Input.Changed) -> None:
        code = event.input.id.removeprefix("search-")
        stations = [
            station for station in self._stations_by_country[code] if station.matches(event.value)
        ]
        self._render_table(code, stations)

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        code = event.pane.id.removeprefix("tab-")
        self._config.last_tab = code

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        code = event.data_table.id.removeprefix("table-")
        station = next(
            (s for s in self._stations_by_country[code] if s.stationuuid == event.row_key.value),
            None,
        )
        if station is not None:
            self._play(station)

    def _play(self, station: Station) -> None:
        self._current_station = station
        self.mpv.play(station.url)
        self._update_now_playing(title=None)

    def _update_now_playing(self, title: str | None) -> None:
        if self._current_station is None:
            self.query_one("#now-playing", Static).update("")
            return
        text = f"♪ Now playing: {self._current_station.name}"
        if title:
            text += f" — {title}"
        text += f"  (vol {self._config.volume}%)"
        self.query_one("#now-playing", Static).update(text)

    def _poll_now_playing(self) -> None:
        if self._current_station is None:
            return
        if self.mpv.had_playback_error():
            self._current_station.available = False
            self._refresh_tables()
            return
        title = self.mpv.get_now_playing()
        self._update_now_playing(title)

    def action_refresh_stations(self) -> None:
        self.load_stations(force_refresh=True)

    def action_toggle_pause(self) -> None:
        self.mpv.toggle_pause()

    def action_volume_up(self) -> None:
        self._config.volume = min(100, self._config.volume + VOLUME_STEP)
        self.mpv.set_volume(self._config.volume)
        self._update_now_playing(title=None)

    def action_volume_down(self) -> None:
        self._config.volume = max(0, self._config.volume - VOLUME_STEP)
        self.mpv.set_volume(self._config.volume)
        self._update_now_playing(title=None)

    def _switch_tab(self) -> None:
        """Toggle the active TabbedContent pane between the two country tabs.

        Setting `TabbedContent.active` alone isn't enough: if a widget inside
        the tab being hidden currently has focus (e.g. the station table —
        the normal place to be when reaching for this binding), Textual's
        focus system reacts to that widget becoming unfocusable by shifting
        focus to the next focusable widget in DOM order. That focus move
        fires `TabPane.Focused`, which `TabbedContent._on_tab_pane_focused`
        handles by snapping `active` right back to whichever tab now holds
        focus — silently undoing the switch. Explicitly focusing the new
        tab's table *after* Textual's own focus machinery has settled (via
        `call_after_refresh`) wins that race instead of fighting it inline.
        """
        codes = [code for code, _ in COUNTRIES]
        tabbed_content = self.query_one(TabbedContent)
        current = tabbed_content.active.removeprefix("tab-")
        next_code = codes[(codes.index(current) + 1) % len(codes)]
        tabbed_content.active = f"tab-{next_code}"
        self.call_after_refresh(self._focus_table, next_code)

    def _focus_table(self, code: str) -> None:
        self.query_one(f"#table-{code}", DataTable).focus()

    def action_next_tab(self) -> None:
        self._switch_tab()

    def action_prev_tab(self) -> None:
        self._switch_tab()

    def action_quit(self) -> None:
        config_module.save_config(self._config_path, self._config)
        self.mpv.quit()
        self.exit()
