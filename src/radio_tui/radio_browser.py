"""Radio Browser API client with a local JSON cache."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from radio_tui.models import Station

API_BASE = "https://all.api.radio-browser.info/json/stations/bycountrycodeexact"
USER_AGENT = "radio-tui/0.1"
CACHE_MAX_AGE_SECONDS = 24 * 60 * 60


class NoStationsAvailable(Exception):
    """Raised when stations can't be fetched and no local cache exists either."""


@dataclass
class StationsResult:
    """Result of get_stations(): the station list plus where it came from."""

    stations: list[Station]
    from_cache: bool
    cache_timestamp: float | None


def fetch_stations(countrycodes: list[str], timeout: float = 10.0) -> list[Station]:
    """Fetch stations for the given country codes from the Radio Browser API."""
    stations: list[Station] = []
    headers = {"User-Agent": USER_AGENT}
    for code in countrycodes:
        response = requests.get(f"{API_BASE}/{code}", headers=headers, timeout=timeout)
        response.raise_for_status()
        stations.extend(Station.from_api_dict(item) for item in response.json())
    return stations


def load_cache(cache_path: Path) -> tuple[list[Station], float] | None:
    """Load cached stations and their fetch timestamp, or None if no cache exists."""
    if not cache_path.exists():
        return None
    payload = json.loads(cache_path.read_text())
    stations = [Station.from_cache_dict(item) for item in payload["stations"]]
    return stations, payload["fetched_at"]


def save_cache(cache_path: Path, stations: list[Station], fetched_at: float) -> None:
    """Write stations and a fetch timestamp to the cache file."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": fetched_at,
        "stations": [station.to_cache_dict() for station in stations],
    }
    cache_path.write_text(json.dumps(payload))


def is_stale(fetched_at: float, now: float, max_age_seconds: int = CACHE_MAX_AGE_SECONDS) -> bool:
    """Return True if a cache fetched at `fetched_at` is older than max_age_seconds."""
    return (now - fetched_at) > max_age_seconds


def get_stations(
    cache_path: Path,
    countrycodes: list[str],
    force_refresh: bool = False,
) -> StationsResult:
    """Get stations, preferring a fresh cache, falling back to the API, then a stale cache."""
    cached = load_cache(cache_path)
    now = time.time()

    if not force_refresh and cached is not None:
        stations, fetched_at = cached
        if not is_stale(fetched_at, now):
            return StationsResult(stations, from_cache=True, cache_timestamp=fetched_at)

    try:
        stations = fetch_stations(countrycodes)
    except requests.RequestException:
        if cached is not None:
            stations, fetched_at = cached
            return StationsResult(stations, from_cache=True, cache_timestamp=fetched_at)
        raise NoStationsAvailable(
            "Could not reach the Radio Browser API and no local cache exists."
        )

    save_cache(cache_path, stations, now)
    return StationsResult(stations, from_cache=False, cache_timestamp=now)
