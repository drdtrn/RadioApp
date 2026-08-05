#!/usr/bin/env python3
"""A stand-in for mpv that never creates its IPC socket.

Used to test MPVController's connect-timeout and cleanup-on-failure paths:
it accepts the same --input-ipc-server flag as real mpv but ignores it and
just hangs, so MPVController._connect_with_retry() times out.
"""
from __future__ import annotations

import time

if __name__ == "__main__":
    time.sleep(10)
