"""Test doubles shared across app tests."""
from __future__ import annotations


class FakeMPVController:
    """In-process stand-in for MPVController — no subprocess, no sockets."""

    def __init__(self):
        self.started = False
        self.played_urls: list[str] = []
        self.paused = False
        self.volume = 70
        self.now_playing = "Fake Title"
        self.error_flag = False
        self.quit_called = False

    def start(self) -> None:
        self.started = True

    def play(self, url: str) -> None:
        self.played_urls.append(url)

    def toggle_pause(self) -> bool:
        self.paused = not self.paused
        return self.paused

    def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, volume))

    def get_now_playing(self) -> str | None:
        return self.now_playing

    def had_playback_error(self) -> bool:
        flag, self.error_flag = self.error_flag, False
        return flag

    def quit(self) -> None:
        self.quit_called = True


class FailingStartMPVController(FakeMPVController):
    """FakeMPVController whose start() fails like a missing/broken mpv binary would."""

    def start(self) -> None:
        raise FileNotFoundError("mpv binary not found")
