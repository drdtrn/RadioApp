"""Entry point for the radio-tui CLI."""
from __future__ import annotations

import sys

from radio_tui.app import RadioApp
from radio_tui.mpv_controller import MPVController


def main() -> int:
    """CLI entry point. Returns a process exit code."""
    if not MPVController.is_installed():
        print("mpv is not installed. Install it with: pacman -S mpv", file=sys.stderr)
        return 1

    app = RadioApp()
    app.run()
    return app.return_code or 0


if __name__ == "__main__":
    sys.exit(main())
