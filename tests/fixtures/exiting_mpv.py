#!/usr/bin/env python3
"""A stand-in for mpv that exits immediately without creating its IPC socket.

Used to test MPVController's cleanup-on-failure path when the mpv process
dies right after spawn instead of hanging: MPVController._connect_with_retry()
should still time out with a ConnectionError (never a crash from a dead
process), and start() should still clean up the subprocess and temp dir.
"""
from __future__ import annotations

if __name__ == "__main__":
    pass
