"""Low-level JSON-line protocol for talking to mpv's IPC socket."""
from __future__ import annotations

import json
import socket
from collections import deque


class MPVIPCClient:
    """Wraps a connected unix socket to mpv's --input-ipc-server."""

    def __init__(self, sock: socket.socket, max_events: int = 50):
        self._sock = sock
        self._buffer = b""
        self.events: deque[dict] = deque(maxlen=max_events)

    def send_command(self, command: list) -> dict:
        """Send one command and return mpv's response dict (the non-event line)."""
        self._sock.sendall(json.dumps({"command": command}).encode() + b"\n")
        while True:
            message = self._read_message()
            if "event" in message:
                self.events.append(message)
                continue
            return message

    def _read_message(self) -> dict:
        while b"\n" not in self._buffer:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("mpv IPC socket closed unexpectedly")
            self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\n", 1)
        return json.loads(line)

    def close(self) -> None:
        self._sock.close()
