import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from radio_tui import config, gui, radio_browser
from radio_tui.models import Station
from radio_tui.radio_browser import NoStationsAvailable, StationsResult
from tests.doubles import FailingStartMPVController, FakeMPVController


def _fake_stations():
    return [
        Station(stationuuid="1", name="Radio Kosova e Lire", url="http://x", countrycode="XK", tags=["news"], bitrate=128),
        Station(stationuuid="2", name="Radio Dukagjini", url="http://z/stream", countrycode="XK", tags=["pop"], bitrate=64),
        Station(stationuuid="3", name="MBC FM", url="http://y", countrycode="SA", tags=["pop"], bitrate=320),
    ]


@pytest.fixture(autouse=True)
def stub_stations(monkeypatch):
    monkeypatch.setattr(
        radio_browser,
        "get_stations",
        lambda *a, **k: StationsResult(_fake_stations(), from_cache=False, cache_timestamp=None),
    )


def _make_window(qtbot, tmp_path, mpv=None):
    window = gui.MainWindow(
        cache_path=tmp_path / "stations.json",
        config_path=tmp_path / "config.toml",
        mpv=mpv or FakeMPVController(),
    )
    qtbot.addWidget(window)
    return window


def _started_window(qtbot, tmp_path, mpv=None):
    window = _make_window(qtbot, tmp_path, mpv)
    window.start()
    qtbot.waitUntil(lambda: window.country_tabs["XK"].station_list.topLevelItemCount() > 0)
    return window


def _item(window, code, name):
    return next(item for item in window.country_tabs[code].items() if item.station.name == name)


def _activate(qtbot, window):
    """Show and activate the window — Qt only fires shortcuts in the active window.

    Waits on QApplication.activeWindow() (what the shortcut map checks), not
    window.isActiveWindow(), which can report True before activation lands.
    """
    window.show()
    window.activateWindow()
    qtbot.waitUntil(lambda: QApplication.activeWindow() is window)


def _play_via_enter(qtbot, window, code, name):
    station_list = window.country_tabs[code].station_list
    station_list.setCurrentItem(_item(window, code, name))
    qtbot.keyClick(station_list, Qt.Key.Key_Return)


def test_stations_load_into_their_country_tabs(qtbot, tmp_path):
    window = _started_window(qtbot, tmp_path)

    assert [s.name for s in window.country_tabs["XK"].visible_stations()] == [
        "Radio Dukagjini",
        "Radio Kosova e Lire",
    ]
    assert [s.name for s in window.country_tabs["SA"].visible_stations()] == ["MBC FM"]
    assert window.refresh_button.isEnabled()
    assert window.statusBar().currentMessage().startswith("3 stations")


def test_start_applies_saved_volume_to_mpv(qtbot, tmp_path):
    config.save_config(tmp_path / "config.toml", config.Config(volume=40))
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)

    assert fake_mpv.started is True
    assert fake_mpv.volume == 40
    assert window.volume_slider.value() == 40


def test_search_hides_non_matching_stations(qtbot, tmp_path):
    window = _started_window(qtbot, tmp_path)
    tab = window.country_tabs["XK"]

    tab.search.setText("dukagjini")
    assert [s.name for s in tab.visible_stations()] == ["Radio Dukagjini"]

    tab.search.setText("NEWS")
    assert [s.name for s in tab.visible_stations()] == ["Radio Kosova e Lire"]

    tab.search.clear()
    assert len(tab.visible_stations()) == 2


def test_enter_in_search_box_selects_first_match(qtbot, tmp_path):
    window = _started_window(qtbot, tmp_path)
    tab = window.country_tabs["XK"]

    tab.search.setText("kosova")
    qtbot.keyClick(tab.search, Qt.Key.Key_Return)

    assert tab.station_list.currentItem().station.name == "Radio Kosova e Lire"


def test_bitrate_column_sorts_numerically(qtbot, tmp_path):
    window = _started_window(qtbot, tmp_path)
    station_list = window.country_tabs["XK"].station_list

    station_list.sortByColumn(gui.BITRATE_COLUMN, Qt.SortOrder.DescendingOrder)

    # Text sorting would put "64 kbps" above "128 kbps".
    assert [s.bitrate for s in window.country_tabs["XK"].visible_stations()] == [128, 64]


def test_enter_on_station_plays_it(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)

    _play_via_enter(qtbot, window, "XK", "Radio Kosova e Lire")

    assert fake_mpv.played_urls == ["http://x"]
    assert window.station_label.text() == "Radio Kosova e Lire"
    assert window.play_pause_button.isEnabled()
    assert _item(window, "XK", "Radio Kosova e Lire").font(gui.NAME_COLUMN).bold()
    assert not _item(window, "XK", "Radio Dukagjini").font(gui.NAME_COLUMN).bold()


def test_play_pause_button_toggles_pause(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)
    _play_via_enter(qtbot, window, "XK", "Radio Kosova e Lire")

    qtbot.mouseClick(window.play_pause_button, Qt.MouseButton.LeftButton)
    assert fake_mpv.paused is True

    qtbot.mouseClick(window.play_pause_button, Qt.MouseButton.LeftButton)
    assert fake_mpv.paused is False


def test_space_toggles_pause_from_station_list(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)
    _activate(qtbot, window)
    _play_via_enter(qtbot, window, "XK", "Radio Kosova e Lire")

    qtbot.keyClick(window.country_tabs["XK"].station_list, Qt.Key.Key_Space)

    assert fake_mpv.paused is True


def test_space_in_search_box_types_instead_of_pausing(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)
    _activate(qtbot, window)
    _play_via_enter(qtbot, window, "XK", "Radio Kosova e Lire")
    search = window.country_tabs["XK"].search

    qtbot.keyClicks(search, "radio kosova")

    assert search.text() == "radio kosova"
    assert fake_mpv.paused is False


def test_picking_a_station_while_paused_resumes_playback(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)
    _play_via_enter(qtbot, window, "XK", "Radio Kosova e Lire")
    window.toggle_pause()
    assert fake_mpv.paused is True

    _play_via_enter(qtbot, window, "XK", "Radio Dukagjini")

    assert fake_mpv.paused is False
    assert fake_mpv.played_urls == ["http://x", "http://z/stream"]


def test_volume_slider_sets_mpv_volume_and_config(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)

    window.volume_slider.setValue(55)

    assert fake_mpv.volume == 55
    assert window.volume_label.text() == "55%"
    window.close()
    assert config.load_config(tmp_path / "config.toml").volume == 55


def test_ctrl_up_and_down_nudge_volume(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)
    _activate(qtbot, window)
    station_list = window.country_tabs["XK"].station_list

    qtbot.keyClick(station_list, Qt.Key.Key_Up, Qt.KeyboardModifier.ControlModifier)
    assert fake_mpv.volume == 75

    qtbot.keyClick(station_list, Qt.Key.Key_Down, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClick(station_list, Qt.Key.Key_Down, Qt.KeyboardModifier.ControlModifier)
    assert fake_mpv.volume == 65


def test_ctrl_tab_switches_country_from_list_and_search_box(qtbot, tmp_path):
    window = _started_window(qtbot, tmp_path)
    _activate(qtbot, window)

    qtbot.keyClick(window.country_tabs["XK"].station_list, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
    assert window.tabs.currentWidget().code == "SA"

    qtbot.keyClick(window.country_tabs["SA"].search, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
    assert window.tabs.currentWidget().code == "XK"


def test_last_tab_is_restored_and_tab_changes_are_saved(qtbot, tmp_path):
    config.save_config(tmp_path / "config.toml", config.Config(last_tab="SA"))
    window = _started_window(qtbot, tmp_path)
    assert window.tabs.currentWidget().code == "SA"

    window.tabs.setCurrentIndex(0)
    window.close()

    assert config.load_config(tmp_path / "config.toml").last_tab == "XK"


def test_now_playing_shows_track_title_from_mpv(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)
    _play_via_enter(qtbot, window, "XK", "Radio Kosova e Lire")

    fake_mpv.now_playing = "Artist — Song"
    window._poll_now_playing()

    assert window.title_label.text() == "Artist — Song"
    assert window.windowTitle() == "Radio Kosova e Lire — Radio"


def test_playback_error_marks_station_unavailable(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)
    _play_via_enter(qtbot, window, "XK", "Radio Kosova e Lire")

    fake_mpv.error_flag = True
    window._poll_now_playing()

    assert _item(window, "XK", "Radio Kosova e Lire").text(gui.NAME_COLUMN).startswith("⚠")
    assert window.title_label.text() == gui.PLAYBACK_FAILED_TEXT
    # Later polls must not wipe the failure message.
    window._poll_now_playing()
    assert window.title_label.text() == gui.PLAYBACK_FAILED_TEXT


def test_retrying_a_failed_station_clears_its_warning(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)
    _play_via_enter(qtbot, window, "XK", "Radio Kosova e Lire")
    fake_mpv.error_flag = True
    window._poll_now_playing()

    _play_via_enter(qtbot, window, "XK", "Radio Kosova e Lire")

    assert not _item(window, "XK", "Radio Kosova e Lire").text(gui.NAME_COLUMN).startswith("⚠")


def test_refresh_keeps_tracking_the_playing_station(qtbot, tmp_path):
    window = _started_window(qtbot, tmp_path)
    _play_via_enter(qtbot, window, "XK", "Radio Kosova e Lire")

    window.refresh_stations()
    qtbot.waitUntil(lambda: window.refresh_button.isEnabled())

    assert _item(window, "XK", "Radio Kosova e Lire").font(gui.NAME_COLUMN).bold()


def test_load_failure_is_reported_and_refresh_stays_available(qtbot, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise NoStationsAvailable("Could not reach the Radio Browser API.")

    monkeypatch.setattr(radio_browser, "get_stations", fail)
    window = _make_window(qtbot, tmp_path)
    window.start()

    qtbot.waitUntil(lambda: window.refresh_button.isEnabled())
    assert "Could not reach the Radio Browser API." in window.statusBar().currentMessage()


def test_unexpected_load_error_does_not_leave_window_stuck_loading(qtbot, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("corrupt cache")

    monkeypatch.setattr(radio_browser, "get_stations", fail)
    window = _make_window(qtbot, tmp_path)
    window.start()

    qtbot.waitUntil(lambda: window.refresh_button.isEnabled())
    assert "corrupt cache" in window.statusBar().currentMessage()


def test_mpv_start_failure_raises_and_close_skips_mpv_quit(qtbot, tmp_path):
    fake_mpv = FailingStartMPVController()
    window = _make_window(qtbot, tmp_path, mpv=fake_mpv)

    with pytest.raises(OSError):
        window.start()
    window.close()

    assert fake_mpv.quit_called is False


def test_close_saves_config_and_stops_mpv(qtbot, tmp_path):
    fake_mpv = FakeMPVController()
    window = _started_window(qtbot, tmp_path, mpv=fake_mpv)

    window.close()

    assert fake_mpv.quit_called is True
    assert (tmp_path / "config.toml").exists()


def test_track_title_hides_url_fallback_and_station_name():
    station = Station(name="Mp3Quran Tarateel", url="https://qurango.net/radio/tarateel")

    assert gui.track_title(station, "tarateel") is None
    assert gui.track_title(station, "Mp3Quran Tarateel") is None
    assert gui.track_title(station, None) is None
    assert gui.track_title(station, "Surah Al-Fatiha") == "Surah Al-Fatiha"


def test_main_reports_missing_mpv_and_returns_one(qtbot, monkeypatch):
    monkeypatch.setattr(gui.config_module, "load_config", lambda path: config.Config(mpv_binary="/opt/custom/mpv"))
    monkeypatch.setattr(gui.MPVController, "is_installed", staticmethod(lambda mpv_binary="mpv": False))
    shown = []
    monkeypatch.setattr(gui.QMessageBox, "critical", lambda parent, title, text: shown.append(text))

    assert gui.main() == 1
    assert "/opt/custom/mpv" in shown[0]


def test_main_reports_mpv_start_failure_and_returns_one(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(gui.config_module, "load_config", lambda path: config.Config())
    monkeypatch.setattr(gui.MPVController, "is_installed", staticmethod(lambda mpv_binary="mpv": True))
    monkeypatch.setattr(gui.MPVController, "start", FailingStartMPVController.start)
    shown = []
    monkeypatch.setattr(gui.QMessageBox, "critical", lambda parent, title, text: shown.append(text))

    assert gui.main() == 1
    assert "mpv binary not found" in shown[0]
