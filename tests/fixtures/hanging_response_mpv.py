#!/usr/bin/env python3
"""A stand-in for mpv that accepts the IPC connection but never responds.

Unlike hanging_mpv.py (which never even creates the socket, so
MPVController._connect_with_retry() times out), this fixture creates the
--input-ipc-server socket and accepts a connection normally, so
MPVController.start() succeeds. It then reads (and discards) anything sent
to it without ever writing a reply, simulating a real mpv process that has
wedged after the IPC handshake. Used to verify that MPVController surfaces
this as a timeout (via the socket timeout set in _connect_with_retry)
instead of blocking a caller's recv() forever.
"""
from __future__ import annotations

import socket
import sys
import time


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
    # Keep the connection open and never reply, simulating a wedged mpv.
    # (Deliberately do NOT `del conn` / let it go out of scope here — that
    # would close the fd immediately, making the client see a prompt
    # ConnectionResetError instead of a genuine multi-second recv() timeout.)
    time.sleep(30)


if __name__ == "__main__":
    main()
