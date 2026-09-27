"""Data model for a single radio station."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Station:
    """A single radio station, normalized from the Radio Browser API."""

    stationuuid: str = ""
    name: str = "Unknown station"
    url: str = ""
    countrycode: str = ""
    tags: list[str] = field(default_factory=list)
    language: str = ""
    bitrate: int = 0
    available: bool = True

    def matches(self, query: str) -> bool:
        """True if `query` appears (case-insensitively) in the name or any tag.

        A blank query matches every station.
        """
        query = query.strip().lower()
        if not query:
            return True
        return query in self.name.lower() or any(query in tag.lower() for tag in self.tags)

    @classmethod
    def from_api_dict(cls, data: dict) -> "Station":
        """Build a Station from one entry of the Radio Browser API response."""
        url = data.get("url_resolved") or data.get("url") or ""
        tags_raw = data.get("tags") or ""
        tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]
        return cls(
            stationuuid=data.get("stationuuid", ""),
            name=data.get("name") or "Unknown station",
            url=url,
            countrycode=data.get("countrycode", ""),
            tags=tags,
            language=data.get("language", ""),
            bitrate=int(data.get("bitrate") or 0),
        )

    def to_cache_dict(self) -> dict:
        """Serialize to a plain dict for JSON caching."""
        return {
            "stationuuid": self.stationuuid,
            "name": self.name,
            "url": self.url,
            "countrycode": self.countrycode,
            "tags": self.tags,
            "language": self.language,
            "bitrate": self.bitrate,
        }

    @classmethod
    def from_cache_dict(cls, data: dict) -> "Station":
        """Rebuild a Station from a cached dict (see to_cache_dict)."""
        return cls(
            stationuuid=data["stationuuid"],
            name=data["name"],
            url=data["url"],
            countrycode=data["countrycode"],
            tags=data.get("tags", []),
            language=data.get("language", ""),
            bitrate=data.get("bitrate", 0),
        )
