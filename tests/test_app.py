from radio_tui import radio_browser
from radio_tui.app import RadioApp
from radio_tui.models import Station
from radio_tui.radio_browser import StationsResult


def _fake_stations():
    return [
        Station(stationuuid="1", name="Radio Kosova e Lire", url="http://x", countrycode="XK", tags=["news"]),
        Station(stationuuid="2", name="MBC FM", url="http://y", countrycode="SA", tags=["pop"]),
    ]


async def test_stations_load_into_correct_country_tables(monkeypatch, tmp_path):
    monkeypatch.setattr(
        radio_browser,
        "get_stations",
        lambda *a, **k: StationsResult(_fake_stations(), from_cache=False, cache_timestamp=None),
    )
    app = RadioApp(cache_path=tmp_path / "stations.json")

    async with app.run_test() as pilot:
        await pilot.pause()
        xk_table = app.query_one("#table-XK")
        sa_table = app.query_one("#table-SA")
        assert xk_table.row_count == 1
        assert sa_table.row_count == 1


async def test_search_filters_table_rows(monkeypatch, tmp_path):
    monkeypatch.setattr(
        radio_browser,
        "get_stations",
        lambda *a, **k: StationsResult(_fake_stations(), from_cache=False, cache_timestamp=None),
    )
    app = RadioApp(cache_path=tmp_path / "stations.json")

    async with app.run_test() as pilot:
        await pilot.pause()
        search = app.query_one("#search-XK")
        search.value = "nonexistent"
        await pilot.pause()
        xk_table = app.query_one("#table-XK")
        assert xk_table.row_count == 0
