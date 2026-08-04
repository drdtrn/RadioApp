"""Manage an mpv subprocess as a background radio playback engine."""
from __future__ import annotations

import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

from radio_tui.mpv_ipc import MPVIPCClient

CONNECT_TIMEOUT_SECONDS = 2.0
CONNECT_RETRY_INTERVAL = 0.05


class MPVController:
    """Starts mpv in idle mode and drives it over its JSON IPC socket."""

    def __init__(self, mpv_binary: str = "mpv"):
        self._mpv_binary = mpv_binary
        self._process: subprocess.Popen | None = None
        self._socket_dir: str | None = None
        self._socket_path: Path | None = None
        self._client: MPVIPCClient | None = None

    @staticmethod
    def is_installed(mpv_binary: str = "mpv") -> bool:
        return shutil.which(mpv_binary) is not None

    def start(self) -> None:
        """Launch mpv in idle mode and connect to its IPC socket."""
        # mkdtemp (not mktemp) creates the directory atomically with 0700
        # permissions, avoiding the predictable-path race of a bare mktemp().
        self._socket_dir = tempfile.mkdtemp(prefix="radio-tui-mpv-")
        self._socket_path = Path(self._socket_dir) / "mpv.sock"
        self._process = subprocess.Popen(
            [
                self._mpv_binary,
                "--no-video",
                "--idle=yes",
                f"--input-ipc-server={self._socket_path}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        sock = self._connect_with_retry()
        self._client = MPVIPCClient(sock)

    def _connect_with_retry(self) -> socket.socket:
        deadline = time.monotonic() + CONNECT_TIMEOUT_SECONDS
        last_error: OSError | None = None
        while time.monotonic() < deadline:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(str(self._socket_path))
                return sock
            except OSError as error:
                last_error = error
                time.sleep(CONNECT_RETRY_INTERVAL)
        raise ConnectionError(f"Could not connect to mpv IPC socket: {last_error}")

    def play(self, url: str) -> None:
        self._client.send_command(["loadfile", url, "replace"])

    def toggle_pause(self) -> bool:
        current = self._client.send_command(["get_property", "pause"])["data"]
        new_state = not current
        self._client.send_command(["set_property", "pause", new_state])
        return new_state

    def set_volume(self, volume: int) -> None:
        volume = max(0, min(100, volume))
        self._client.send_command(["set_property", "volume", volume])

    def get_now_playing(self) -> str | None:
        response = self._client.send_command(["get_property", "media-title"])
        if response.get("error") != "success":
            return None
        return response.get("data")

    def had_playback_error(self) -> bool:
        """Return True and clear the flag if an end-file error occurred since the last check."""
        found = any(
            event.get("event") == "end-file" and event.get("reason") == "error"
            for event in self._client.events
        )
        if found:
            self._client.events.clear()
        return found

    def quit(self) -> None:
        if self._client is not None:
            try:
                self._client.send_command(["quit"])
            except ConnectionError:
                pass
            self._client.close()
        if self._process is not None:
            self._process.terminate()
            self._process.wait(timeout=2)
        if self._socket_dir is not None:
            shutil.rmtree(self._socket_dir, ignore_errors=True)
