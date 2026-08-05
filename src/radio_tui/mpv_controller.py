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
IPC_TIMEOUT_SECONDS = 2.0
"""Timeout for individual IPC round trips once connected.

Without this, a hung/unresponsive mpv process would block a socket.recv()
indefinitely (see MPVIPCClient._read_message), and since get_now_playing()/
had_playback_error() are polled every 2s from the main UI thread
(RadioApp._poll_now_playing), a hang here freezes the entire TUI forever.
"""


class MPVController:
    """Starts mpv in idle mode and drives it over its JSON IPC socket."""

    def __init__(self, mpv_binary: str = "mpv"):
        self._mpv_binary = mpv_binary
        self._process: subprocess.Popen | None = None
        self._socket_dir: str | None = None
        self._socket_path: Path | None = None
        self._client: MPVIPCClient | None = None
        self._ipc_unresponsive = False

    @staticmethod
    def is_installed(mpv_binary: str = "mpv") -> bool:
        return shutil.which(mpv_binary) is not None

    def start(self) -> None:
        """Launch mpv in idle mode and connect to its IPC socket."""
        # mkdtemp (not mktemp) creates the directory atomically with 0700
        # permissions, avoiding the predictable-path race of a bare mktemp().
        self._socket_dir = tempfile.mkdtemp(prefix="radio-tui-mpv-")
        self._socket_path = Path(self._socket_dir) / "mpv.sock"
        try:
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
        except Exception:
            if self._process is not None:
                self._process.terminate()
                self._process.wait(timeout=2)
            shutil.rmtree(self._socket_dir, ignore_errors=True)
            raise
        self._client = MPVIPCClient(sock)

    def _connect_with_retry(self) -> socket.socket:
        deadline = time.monotonic() + CONNECT_TIMEOUT_SECONDS
        last_error: OSError | None = None
        while time.monotonic() < deadline:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(str(self._socket_path))
                sock.settimeout(IPC_TIMEOUT_SECONDS)
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
        try:
            response = self._client.send_command(["get_property", "media-title"])
        except OSError:
            # Includes socket.timeout: mpv accepted the connection but stopped
            # responding. Surface it the same way as any other IPC failure
            # (None) instead of letting the poller block forever, and record
            # it so had_playback_error() can flag the station as unavailable.
            self._ipc_unresponsive = True
            return None
        if response.get("error") != "success":
            return None
        return response.get("data")

    def had_playback_error(self) -> bool:
        """Return True and clear the flag if an end-file error occurred since the
        last check, or if mpv's IPC connection has gone unresponsive (timed out)."""
        if self._ipc_unresponsive:
            self._ipc_unresponsive = False
            return True
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
            except OSError:
                # Includes ConnectionError (mpv already gone) and
                # socket.timeout (mpv wedged and never replied). Either way,
                # don't let a graceful "quit" IPC command block or crash
                # shutdown — fall through to terminating the process directly.
                pass
            self._client.close()
        if self._process is not None:
            self._process.terminate()
            self._process.wait(timeout=2)
        if self._socket_dir is not None:
            shutil.rmtree(self._socket_dir, ignore_errors=True)
