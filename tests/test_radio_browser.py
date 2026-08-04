import time

import pytest
import requests

from radio_tui import radio_browser
from radio_tui.models import Station


def _station_payload(name="Radio Test", countrycode="XK"):
    return {
        "stationuuid": "uuid-1",
        "name": name,
        "url": "http://example/stream",
        "url_resolved": "http://example/stream",
        "countrycode": countrycode,
        "tags": "pop",
        "language": "albanian",
        "bitrate": "128",
    }


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_stations_hits_one_url_per_country(monkeypatch):
    requested_urls = []

    def fake_get(url, headers, timeout):
        requested_urls.append(url)
        return _FakeResponse([_station_payload()])

    monkeypatch.setattr(requests, "get", fake_get)

    stations = radio_browser.fetch_stations(["XK", "SA"])

    assert requested_urls == [
        f"{radio_browser.API_BASE}/XK",
        f"{radio_browser.API_BASE}/SA",
    ]
    assert len(stations) == 2
    assert all(isinstance(s, Station) for s in stations)


def test_save_and_load_cache_round_trip(tmp_path):
    cache_path = tmp_path / "stations.json"
    station = Station.from_api_dict(_station_payload())

    radio_browser.save_cache(cache_path, [station], fetched_at=1000.0)
    loaded_stations, fetched_at = radio_browser.load_cache(cache_path)

    assert loaded_stations == [station]
    assert fetched_at == 1000.0


def test_load_cache_returns_none_when_missing(tmp_path):
    assert radio_browser.load_cache(tmp_path / "missing.json") is None


def test_is_stale():
    now = 10_000.0
    assert radio_browser.is_stale(fetched_at=now - 25 * 3600, now=now) is True
    assert radio_browser.is_stale(fetched_at=now - 1 * 3600, now=now) is False


def test_get_stations_uses_fresh_cache_without_hitting_api(tmp_path, monkeypatch):
    cache_path = tmp_path / "stations.json"
    station = Station.from_api_dict(_station_payload())
    radio_browser.save_cache(cache_path, [station], fetched_at=time.time())

    def fail_fetch(*args, **kwargs):
        raise AssertionError("should not call the API when cache is fresh")

    monkeypatch.setattr(radio_browser, "fetch_stations", fail_fetch)

    result = radio_browser.get_stations(cache_path, ["XK"])

    assert result.from_cache is True
    assert result.stations == [station]


def test_get_stations_falls_back_to_stale_cache_on_api_failure(tmp_path, monkeypatch):
    cache_path = tmp_path / "stations.json"
    station = Station.from_api_dict(_station_payload())
    stale_timestamp = time.time() - 48 * 3600
    radio_browser.save_cache(cache_path, [station], fetched_at=stale_timestamp)

    def fail_fetch(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(radio_browser, "fetch_stations", fail_fetch)

    result = radio_browser.get_stations(cache_path, ["XK"])

    assert result.from_cache is True
    assert result.cache_timestamp == stale_timestamp


def test_get_stations_raises_when_api_fails_and_no_cache(tmp_path, monkeypatch):
    def fail_fetch(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(radio_browser, "fetch_stations", fail_fetch)

    with pytest.raises(radio_browser.NoStationsAvailable):
        radio_browser.get_stations(tmp_path / "missing.json", ["XK"])
