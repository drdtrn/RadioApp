"""Qt desktop front end (radio-gui): same stations, config and mpv engine as the TUI."""
from __future__ import annotations

import signal
import sys
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSlider,
    QStyle,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from radio_tui import config as config_module
from radio_tui import radio_browser
from radio_tui.config import CACHE_PATH, CONFIG_PATH, COUNTRIES
from radio_tui.models import Station
from radio_tui.mpv_controller import MPV_INSTALL_HINT, MPVController
from radio_tui.radio_browser import StationsResult

APP_ID = "radio-gui"
"""Matches packaging/radio-gui.desktop, so Wayland compositors can pair the
window with its launcher entry (icon, name, dock grouping)."""
POLL_INTERVAL_MS = 2000
VOLUME_STEP = 5
NAME_COLUMN, TAGS_COLUMN, BITRATE_COLUMN = range(3)
IDLE_HINT = "Double-click a station (or select it and press Enter) to start listening"
PLAYBACK_FAILED_TEXT = "This stream failed to play — try another station"


def track_title(station: Station, media_title: str | None) -> str | None:
    """The song/programme title worth showing for `station`, or None.

    mpv's media-title falls back to the last URL segment (e.g. "stream" or
    "tarateel") when a station sends no ICY title — that tells the listener
    nothing, so it's suppressed along with a title that just repeats the
    station name.
    """
    if not media_title:
        return None
    if media_title == station.name or station.url.rstrip("/").endswith(media_title):
        return None
    return media_title


class _StationLoader(QObject):
    """Fetches stations off the UI thread; results arrive via queued signals."""

    loaded = Signal(object)  # StationsResult
    failed = Signal(str)

    def __init__(self, cache_path: Path, force_refresh: bool):
        super().__init__()
        self._cache_path = cache_path
        self._force_refresh = force_refresh

    def run(self) -> None:
        try:
            result = radio_browser.get_stations(
                self._cache_path,
                [code for code, _ in COUNTRIES],
                force_refresh=self._force_refresh,
            )
        except Exception as error:
            # Anything escaping here would kill the thread silently and leave
            # the window stuck on "Loading stations…" — report it instead.
            self.failed.emit(str(error) or type(error).__name__)
            return
        self.loaded.emit(result)


class _StationItem(QTreeWidgetItem):
    """One station row. Sorts by the station's real values, not display text."""

    def __init__(self, station: Station):
        tags = ", ".join(station.tags)
        bitrate = f"{station.bitrate} kbps" if station.bitrate else "—"
        super().__init__(["", tags, bitrate])
        self.station = station
        self.setToolTip(TAGS_COLUMN, tags)
        self.setTextAlignment(
            BITRATE_COLUMN, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.update_display(playing=False)

    def update_display(self, playing: bool) -> None:
        """Refresh the name cell: ⚠ for a failed stream, bold for the playing one."""
        if self.station.available:
            self.setText(NAME_COLUMN, self.station.name)
            self.setToolTip(NAME_COLUMN, self.station.name)
        else:
            self.setText(NAME_COLUMN, f"⚠ {self.station.name}")
            self.setToolTip(NAME_COLUMN, "This stream failed to play")
        font = self.font(NAME_COLUMN)
        font.setBold(playing)
        self.setFont(NAME_COLUMN, font)

    def __lt__(self, other: QTreeWidgetItem) -> bool:
        column = self.treeWidget().sortColumn()
        if column == BITRATE_COLUMN:
            return self.station.bitrate < other.station.bitrate
        if column == NAME_COLUMN:
            return self.station.name.casefold() < other.station.name.casefold()
        return self.text(column).casefold() < other.text(column).casefold()


class _CountryTab(QWidget):
    """A search box above a sortable station list, for one country."""

    station_activated = Signal(object)  # Station

    def __init__(self, code: str):
        super().__init__()
        self.code = code

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name or tag…")
        self.search.setClearButtonEnabled(True)

        self.station_list = QTreeWidget()
        self.station_list.setHeaderLabels(["Name", "Tags", "Bitrate"])
        self.station_list.setRootIsDecorated(False)
        self.station_list.setUniformRowHeights(True)
        self.station_list.setAlternatingRowColors(True)
        self.station_list.setSortingEnabled(True)
        self.station_list.sortByColumn(NAME_COLUMN, Qt.SortOrder.AscendingOrder)
        header = self.station_list.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(TAGS_COLUMN, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(BITRATE_COLUMN, QHeaderView.ResizeMode.ResizeToContents)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.station_list)

        self.search.textChanged.connect(self._apply_filter)
        self.search.returnPressed.connect(self._focus_first_match)
        self.station_list.itemActivated.connect(
            lambda item, _column: self.station_activated.emit(item.station)
        )

    def items(self) -> list[_StationItem]:
        """All rows, in their current sort order (hidden ones included)."""
        return [
            self.station_list.topLevelItem(index)
            for index in range(self.station_list.topLevelItemCount())
        ]

    def visible_stations(self) -> list[Station]:
        return [item.station for item in self.items() if not item.isHidden()]

    def set_stations(self, stations: list[Station]) -> None:
        self.station_list.clear()
        self.station_list.addTopLevelItems([_StationItem(station) for station in stations])
        self._apply_filter(self.search.text())

    def mark_playing(self, station: Station | None) -> None:
        playing_uuid = station.stationuuid if station is not None else None
        for item in self.items():
            item.update_display(playing=item.station.stationuuid == playing_uuid)

    def _apply_filter(self, query: str) -> None:
        for item in self.items():
            item.setHidden(not item.station.matches(query))

    def _focus_first_match(self) -> None:
        """Enter in the search box jumps to the first visible station."""
        for item in self.items():
            if not item.isHidden():
                self.station_list.setCurrentItem(item)
                self.station_list.setFocus()
                return


class MainWindow(QMainWindow):
    """Station tabs per country above a now-playing bar, driving one mpv process."""

    def __init__(
        self,
        cache_path: Path = CACHE_PATH,
        config_path: Path = CONFIG_PATH,
        mpv=None,
    ):
        super().__init__()
        self._cache_path = cache_path
        self._config_path = config_path
        self._config = config_module.load_config(config_path)
        self.mpv = mpv or MPVController(mpv_binary=self._config.mpv_binary)
        self._mpv_running = False
        self._current_station: Station | None = None
        self._paused = False
        self._loader: _StationLoader | None = None
        self._poll_timer = QTimer(self, interval=POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_now_playing)

        self.setWindowTitle("Radio")
        self.resize(960, 640)
        self._build_tabs()
        self._build_now_playing_bar()
        self._build_shortcuts()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.tabs)
        layout.addWidget(self._now_playing_bar)
        self.setCentralWidget(central)
        self.statusBar()

    def _build_tabs(self) -> None:
        self.tabs = QTabWidget()
        self.country_tabs: dict[str, _CountryTab] = {}
        for code, label in COUNTRIES:
            tab = _CountryTab(code)
            tab.station_activated.connect(self.play)
            self.country_tabs[code] = tab
            self.tabs.addTab(tab, label)

        self.refresh_button = QToolButton()
        self.refresh_button.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_button.setToolTip("Refresh station list (F5)")
        self.refresh_button.setAutoRaise(True)
        self.refresh_button.clicked.connect(self.refresh_stations)
        self.tabs.setCornerWidget(self.refresh_button, Qt.Corner.TopRightCorner)

        codes = list(self.country_tabs)
        if self._config.last_tab in codes:
            self.tabs.setCurrentIndex(codes.index(self._config.last_tab))
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _build_now_playing_bar(self) -> None:
        self.play_pause_button = QToolButton()
        self.play_pause_button.setIconSize(QSize(32, 32))
        self.play_pause_button.setAutoRaise(True)
        self.play_pause_button.setEnabled(False)
        self.play_pause_button.clicked.connect(self.toggle_pause)
        self._update_play_pause_button()

        self.station_label = QLabel("Nothing playing")
        font = self.station_label.font()
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() * 1.15)
        self.station_label.setFont(font)
        self.title_label = QLabel(IDLE_HINT)
        self.title_label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        labels = QVBoxLayout()
        labels.setSpacing(2)
        for label in (self.station_label, self.title_label):
            # Long titles get clipped instead of stretching the whole window.
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            # Arabic titles would otherwise auto-align to the right edge.
            label.setAlignment(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignAbsolute
                | Qt.AlignmentFlag.AlignVCenter
            )
            labels.addWidget(label)

        # Text rather than an icon: icon themes like Yaru ship dark symbolic
        # volume icons that disappear on a dark palette.
        volume_caption = QLabel("Volume")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setPageStep(10)
        self.volume_slider.setFixedWidth(160)
        self.volume_slider.setToolTip("Volume (Ctrl+Up / Ctrl+Down)")
        self.volume_slider.setValue(self._config.volume)
        self.volume_label = QLabel(f"{self._config.volume}%")
        self.volume_label.setMinimumWidth(self.volume_label.fontMetrics().horizontalAdvance("100%"))
        self.volume_slider.valueChanged.connect(self.set_volume)

        self._now_playing_bar = QWidget()
        bar = QHBoxLayout(self._now_playing_bar)
        bar.setContentsMargins(4, 4, 4, 4)
        bar.addWidget(self.play_pause_button)
        bar.addLayout(labels, stretch=1)
        bar.addWidget(volume_caption)
        bar.addWidget(self.volume_slider)
        bar.addWidget(self.volume_label)

    def _build_shortcuts(self) -> None:
        shortcuts = [
            (["Space"], self.toggle_pause),
            (["F5", "Ctrl+R"], self.refresh_stations),
            (["Ctrl+F"], self._focus_search),
            (["Ctrl+Up"], lambda: self._nudge_volume(VOLUME_STEP)),
            (["Ctrl+Down"], lambda: self._nudge_volume(-VOLUME_STEP)),
            (["Ctrl+Q"], self.close),
        ]
        for keys, slot in shortcuts:
            action = QAction(self)
            action.setShortcuts([QKeySequence(key) for key in keys])
            action.triggered.connect(slot)
            self.addAction(action)

    def _standard_icon(self, pixmap: QStyle.StandardPixmap) -> QIcon:
        return self.style().standardIcon(pixmap)

    def start(self) -> None:
        """Launch mpv and begin loading stations. Raises OSError if mpv can't start."""
        self.mpv.start()
        self._mpv_running = True
        self.mpv.set_volume(self._config.volume)
        self._poll_timer.start()
        self._load_stations(force_refresh=False)

    def refresh_stations(self) -> None:
        self._load_stations(force_refresh=True)

    def _load_stations(self, force_refresh: bool) -> None:
        if self._loader is not None:
            return  # a load is already in flight
        self.refresh_button.setEnabled(False)
        self.statusBar().showMessage("Loading stations…")
        loader = _StationLoader(self._cache_path, force_refresh)
        loader.loaded.connect(self._apply_stations)
        loader.failed.connect(self._show_load_error)
        self._loader = loader
        threading.Thread(target=loader.run, name="station-loader", daemon=True).start()

    def _apply_stations(self, result: StationsResult) -> None:
        self._loader = None
        self.refresh_button.setEnabled(True)
        for code, tab in self.country_tabs.items():
            tab.set_stations([station for station in result.stations if station.countrycode == code])
        if self._current_station is not None:
            # The refreshed list holds new Station objects; keep tracking the
            # one that's playing so ⚠/bold markers keep landing on its row.
            playing_uuid = self._current_station.stationuuid
            self._current_station = next(
                (station for station in result.stations if station.stationuuid == playing_uuid),
                self._current_station,
            )
        self._mark_playing()

        message = f"{len(result.stations)} stations"
        if result.cache_timestamp is not None:
            fetched = datetime.fromtimestamp(result.cache_timestamp)
            message += f" · updated {fetched.day} {fetched:%b %H:%M}"
        self.statusBar().showMessage(message)

    def _show_load_error(self, message: str) -> None:
        self._loader = None
        self.refresh_button.setEnabled(True)
        self.statusBar().showMessage(f"Couldn't load stations: {message}  (F5 to retry)")

    def play(self, station: Station) -> None:
        # Errors mpv reported before this point belong to the previous station.
        self.mpv.had_playback_error()
        self._current_station = station
        station.available = True
        self.mpv.play(station.url)
        if self._paused:
            # mpv keeps its pause flag across loadfile, so a station picked
            # while paused would otherwise load silently.
            self._paused = self.mpv.toggle_pause()
        self.play_pause_button.setEnabled(True)
        self._update_play_pause_button()
        self._show_now_playing(title=None)
        self._mark_playing()

    def toggle_pause(self) -> None:
        if self._current_station is None:
            return
        self._paused = self.mpv.toggle_pause()
        self._update_play_pause_button()

    def set_volume(self, volume: int) -> None:
        self._config.volume = volume
        self.volume_label.setText(f"{volume}%")
        if self._mpv_running:
            self.mpv.set_volume(volume)

    def _nudge_volume(self, delta: int) -> None:
        self.volume_slider.setValue(self.volume_slider.value() + delta)

    def _focus_search(self) -> None:
        search = self.tabs.currentWidget().search
        search.setFocus()
        search.selectAll()

    def _on_tab_changed(self, index: int) -> None:
        self._config.last_tab = self.tabs.widget(index).code

    def _poll_now_playing(self) -> None:
        station = self._current_station
        if station is None or not station.available:
            return
        if self.mpv.had_playback_error():
            station.available = False
            self._mark_playing()
            self.title_label.setText(PLAYBACK_FAILED_TEXT)
            return
        self._show_now_playing(track_title(station, self.mpv.get_now_playing()))

    def _show_now_playing(self, title: str | None) -> None:
        station = self._current_station
        self.station_label.setText(station.name)
        self.station_label.setToolTip(station.name)
        self.title_label.setText(title or "")
        self.title_label.setToolTip(title or "")
        self.setWindowTitle(f"{station.name} — Radio")

    def _mark_playing(self) -> None:
        for tab in self.country_tabs.values():
            tab.mark_playing(self._current_station)

    def _update_play_pause_button(self) -> None:
        if self._current_station is None or self._paused:
            icon, tooltip = QStyle.StandardPixmap.SP_MediaPlay, "Resume (Space)"
        else:
            icon, tooltip = QStyle.StandardPixmap.SP_MediaPause, "Pause (Space)"
        self.play_pause_button.setIcon(self._standard_icon(icon))
        self.play_pause_button.setToolTip(tooltip)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._poll_timer.stop()
        config_module.save_config(self._config_path, self._config)
        if self._mpv_running:
            self.mpv.quit()
            self._mpv_running = False
        super().closeEvent(event)


def _close_on_termination_signals(window: MainWindow) -> None:
    """Make Ctrl+C / SIGTERM close the window (saving config and stopping mpv)
    instead of killing the process and leaving mpv orphaned."""
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: window.close())
    # Python only runs signal handlers between bytecodes, which never happens
    # while Qt's C++ event loop sits idle — so wake the interpreter regularly.
    wakeup = QTimer(window, interval=250)
    wakeup.timeout.connect(lambda: None)
    wakeup.start()


def main() -> int:
    """GUI entry point. Returns a process exit code."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Radio")
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(
        QIcon.fromTheme(
            "multimedia-player", app.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)
        )
    )

    config = config_module.load_config(CONFIG_PATH)
    if not MPVController.is_installed(config.mpv_binary):
        QMessageBox.critical(
            None,
            "mpv not found",
            f"mpv is not installed (looked for '{config.mpv_binary}').\n\n{MPV_INSTALL_HINT}",
        )
        return 1

    window = MainWindow()
    try:
        window.start()
    except OSError as error:
        QMessageBox.critical(None, "Could not start mpv", str(error))
        return 1
    _close_on_termination_signals(window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
