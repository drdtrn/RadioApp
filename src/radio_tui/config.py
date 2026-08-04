"""Small TOML-backed config file for persisted user settings."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_VOLUME = 70
DEFAULT_TAB = "XK"
DEFAULT_MPV_BINARY = "mpv"


@dataclass
class Config:
    volume: int = DEFAULT_VOLUME
    last_tab: str = DEFAULT_TAB
    mpv_binary: str = DEFAULT_MPV_BINARY


def load_config(config_path: Path) -> Config:
    """Load config from a TOML file, falling back to defaults for missing keys."""
    if not config_path.exists():
        return Config()
    data = tomllib.loads(config_path.read_text())
    return Config(
        volume=int(data.get("volume", DEFAULT_VOLUME)),
        last_tab=str(data.get("last_tab", DEFAULT_TAB)),
        mpv_binary=str(data.get("mpv_binary", DEFAULT_MPV_BINARY)),
    )


def save_config(config_path: Path, config: Config) -> None:
    """Write config to a TOML file (flat key = value pairs, one per line)."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"volume = {config.volume}",
        f'last_tab = "{config.last_tab}"',
        f'mpv_binary = "{config.mpv_binary}"',
    ]
    config_path.write_text("\n".join(lines) + "\n")
