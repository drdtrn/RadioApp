#!/usr/bin/env python3
"""A minimal stand-in for mpv, used only in tests.

Accepts the same --input-ipc-server flag as real mpv, opens a unix socket
server, and replies to loadfile/get_property/set_property/quit commands with
canned JSON responses so MPVController can be tested without a real mpv
binary or network stream.
"""
from __future__ import annotations

import json
import socket
import sys


def _arg_value(flag_prefix: str) -> str:
    for arg in sys.argv[1:]:
        if arg.startswith(flag_prefix):
            return arg[len(flag_prefix):]
    raise SystemExit(f"missing required flag {flag_prefix}")


def main() -> None:
    socket_path = _arg_value("--input-ipc-server=")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(socket_path)
    server.listen(1)
    conn, _ = server.accept()

    paused = False
    buffer = b""
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            return
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            request = json.loads(line)
            command = request["command"]
            name = command[0]

            if name == "quit":
                conn.sendall(json.dumps({"error": "success"}).encode() + b"\n")
                return
            if name == "get_property" and command[1] == "pause":
                data = paused
            elif name == "get_property" and command[1] == "media-title":
                data = "Fake Song Title"
            elif name == "set_property" and command[1] == "pause":
                paused = command[2]
                data = None
            else:
                data = None

            conn.sendall(json.dumps({"error": "success", "data": data}).encode() + b"\n")


if __name__ == "__main__":
    main()
