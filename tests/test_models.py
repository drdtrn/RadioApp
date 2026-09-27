from radio_tui.models import Station


def test_from_api_dict_prefers_resolved_url_and_splits_tags():
    api_data = {
        "stationuuid": "abc-123",
        "name": "Radio Kosova e Lire",
        "url": "http://raw.example/stream",
        "url_resolved": "http://resolved.example/stream",
        "countrycode": "XK",
        "tags": "news, talk , ",
        "language": "albanian",
        "bitrate": "128",
    }

    station = Station.from_api_dict(api_data)

    assert station.url == "http://resolved.example/stream"
    assert station.tags == ["news", "talk"]
    assert station.bitrate == 128
    assert station.available is True


def test_from_api_dict_falls_back_to_raw_url_and_defaults():
    station = Station.from_api_dict({"name": "No Extras FM"})

    assert station.url == ""
    assert station.tags == []
    assert station.bitrate == 0
    assert station.countrycode == ""


def test_cache_round_trip_preserves_fields():
    station = Station(
        stationuuid="abc-123",
        name="Radio Kosova e Lire",
        url="http://resolved.example/stream",
        countrycode="XK",
        tags=["news", "talk"],
        language="albanian",
        bitrate=128,
    )

    rebuilt = Station.from_cache_dict(station.to_cache_dict())

    assert rebuilt == station


def test_matches_searches_name_and_tags_case_insensitively():
    station = Station(name="Radio Kosova e Lire", tags=["News", "talk"])

    assert station.matches("kosova")
    assert station.matches("  NEWS ")
    assert station.matches("")
    assert not station.matches("jazz")
