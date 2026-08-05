"""Textual TUI application for browsing and playing radio stations."""
from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Footer, Header, Input, TabbedContent, TabPane

from radio_tui import radio_browser
from radio_tui.models import Station
from radio_tui.radio_browser import NoStationsAvailable

CACHE_PATH = Path.home() / ".cache" / "radio-tui" / "stations.json"
COUNTRIES = [("XK", "Kosovo"), ("SA", "Saudi Arabia")]


class RadioApp(App):
    """Browse and play radio stations from Kosovo and Saudi Arabia."""

    BINDINGS = [("r", "refresh_stations", "Refresh")]

    def __init__(self, cache_path: Path = CACHE_PATH):
        super().__init__()
        self._cache_path = cache_path
        self._stations_by_country: dict[str, list[Station]] = {code: [] for code, _ in COUNTRIES}

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            for code, label in COUNTRIES:
                with TabPane(label, id=f"tab-{code}"):
                    with Vertical():
                        yield Input(placeholder="Search…", id=f"search-{code}")
                        yield DataTable(id=f"table-{code}")
        yield Footer()

    def on_mount(self) -> None:
        for code, _ in COUNTRIES:
            table = self.query_one(f"#table-{code}", DataTable)
            table.add_columns("Name", "Tags", "Bitrate")
            table.cursor_type = "row"
        self.load_stations()

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
            tags = ", ".join(station.tags)
            table.add_row(station.name, tags, str(station.bitrate), key=station.stationuuid)

    def on_input_changed(self, event: Input.Changed) -> None:
        code = event.input.id.removeprefix("search-")
        query = event.value.strip().lower()
        stations = self._stations_by_country[code]
        if query:
            stations = [
                station
                for station in stations
                if query in station.name.lower() or any(query in tag.lower() for tag in station.tags)
            ]
        self._render_table(code, stations)

    def action_refresh_stations(self) -> None:
        self.load_stations(force_refresh=True)
