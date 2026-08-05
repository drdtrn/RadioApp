from textual.widgets import DataTable, Static, TabbedContent

from radio_tui import config, radio_browser
from radio_tui.app import RadioApp
from radio_tui.models import Station
from radio_tui.radio_browser import StationsResult
from tests.doubles import FailingStartMPVController, FakeMPVController


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
    app = RadioApp(
        cache_path=tmp_path / "stations.json",
        config_path=tmp_path / "config.toml",
        mpv=FakeMPVController(),
    )

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
    app = RadioApp(
        cache_path=tmp_path / "stations.json",
        config_path=tmp_path / "config.toml",
        mpv=FakeMPVController(),
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        search = app.query_one("#search-XK")
        search.value = "nonexistent"
        await pilot.pause()
        xk_table = app.query_one("#table-XK")
        assert xk_table.row_count == 0


def _make_app(tmp_path, monkeypatch, mpv=None):
    monkeypatch.setattr(
        radio_browser,
        "get_stations",
        lambda *a, **k: StationsResult(_fake_stations(), from_cache=False, cache_timestamp=None),
    )
    return RadioApp(
        cache_path=tmp_path / "stations.json",
        config_path=tmp_path / "config.toml",
        mpv=mpv or FakeMPVController(),
    )


async def test_enter_on_row_plays_station_via_mpv(monkeypatch, tmp_path):
    fake_mpv = FakeMPVController()
    app = _make_app(tmp_path, monkeypatch, mpv=fake_mpv)

    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one("#table-XK", DataTable)
        table.focus()
        await pilot.press("enter")
        await pilot.pause()

        assert fake_mpv.played_urls == ["http://x"]
        now_playing = app.query_one("#now-playing", Static)
        assert "Radio Kosova e Lire" in str(now_playing.content)


async def test_space_toggles_pause(monkeypatch, tmp_path):
    fake_mpv = FakeMPVController()
    app = _make_app(tmp_path, monkeypatch, mpv=fake_mpv)

    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one("#table-XK", DataTable)
        table.focus()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()

        assert fake_mpv.paused is True


async def test_plus_and_minus_adjust_volume(monkeypatch, tmp_path):
    fake_mpv = FakeMPVController()
    app = _make_app(tmp_path, monkeypatch, mpv=fake_mpv)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("plus")
        await pilot.pause()

        assert fake_mpv.volume == 75


async def test_last_tab_from_config_is_active_on_mount(monkeypatch, tmp_path):
    # _make_app always points config_path at tmp_path / "config.toml" — write
    # the config there first so RadioApp picks it up on construction/mount.
    config.save_config(tmp_path / "config.toml", config.Config(last_tab="SA"))
    app = _make_app(tmp_path, monkeypatch)

    async with app.run_test() as pilot:
        await pilot.pause()
        tabbed = app.query_one(TabbedContent)
        assert tabbed.active == "tab-SA"


async def test_ctrl_right_and_ctrl_left_switch_tab_and_update_config(monkeypatch, tmp_path):
    app = _make_app(tmp_path, monkeypatch)

    async with app.run_test() as pilot:
        await pilot.pause()
        tabbed = app.query_one(TabbedContent)
        assert tabbed.active == "tab-XK"
        assert app._config.last_tab == "XK"

        await pilot.press("ctrl+right")
        await pilot.pause()

        assert tabbed.active == "tab-SA"
        assert app._config.last_tab == "SA"

        await pilot.press("ctrl+left")
        await pilot.pause()

        assert tabbed.active == "tab-XK"
        assert app._config.last_tab == "XK"


async def test_ctrl_right_switches_tab_when_station_table_is_focused(monkeypatch, tmp_path):
    """Regression test: clicking into a tab's DataTable (the state the README
    tells users to be in for playback shortcuts) and then pressing the
    tab-switch binding must actually switch tabs. Previously, hiding the
    pane containing the focused table made Textual auto-refocus a widget in
    the *other* still-visible pane, which fired TabPane.Focused and made
    TabbedContent._on_tab_pane_focused snap `active` right back — so the
    switch silently no-opped and focus got yanked into an unrelated search
    box."""
    app = _make_app(tmp_path, monkeypatch)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#table-XK")
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == "table-XK"

        tabbed = app.query_one(TabbedContent)
        await pilot.press("ctrl+right")
        await pilot.pause()

        assert tabbed.active == "tab-SA"
        assert app._config.last_tab == "SA"
        # Focus should land on the newly active tab's table, not get
        # silently dropped onto some other widget.
        assert app.focused is not None
        assert app.focused.id == "table-SA"

        await pilot.press("ctrl+left")
        await pilot.pause()

        assert tabbed.active == "tab-XK"
        assert app.focused is not None
        assert app.focused.id == "table-XK"


async def test_tab_switch_keybinding_does_not_affect_volume(monkeypatch, tmp_path):
    fake_mpv = FakeMPVController()
    app = _make_app(tmp_path, monkeypatch, mpv=fake_mpv)

    async with app.run_test() as pilot:
        await pilot.pause()
        starting_volume = fake_mpv.volume

        await pilot.press("ctrl+right")
        await pilot.pause()
        await pilot.press("ctrl+left")
        await pilot.pause()

        assert fake_mpv.volume == starting_volume


async def test_mpv_start_failure_exits_cleanly_instead_of_crashing(monkeypatch, tmp_path):
    app = _make_app(tmp_path, monkeypatch, mpv=FailingStartMPVController())

    async with app.run_test() as pilot:
        await pilot.pause()

    assert app.return_code == 1


async def test_quit_saves_config_and_stops_mpv(monkeypatch, tmp_path):
    fake_mpv = FakeMPVController()
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(
        radio_browser,
        "get_stations",
        lambda *a, **k: StationsResult(_fake_stations(), from_cache=False, cache_timestamp=None),
    )
    app = RadioApp(cache_path=tmp_path / "stations.json", config_path=config_path, mpv=fake_mpv)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()

    assert fake_mpv.quit_called is True
    saved = config.load_config(config_path)
    assert saved.volume == fake_mpv.volume
