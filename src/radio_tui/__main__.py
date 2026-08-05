"""Entry point for the radio-tui CLI."""
from __future__ import annotations

import sys

from radio_tui import config as config_module
from radio_tui.app import CONFIG_PATH, RadioApp
from radio_tui.mpv_controller import MPVController


def main() -> int:
    """CLI entry point. Returns a process exit code."""
    config = config_module.load_config(CONFIG_PATH)
    if not MPVController.is_installed(config.mpv_binary):
        print(
            f"mpv is not installed (looked for '{config.mpv_binary}'). "
            "Install it with: pacman -S mpv",
            file=sys.stderr,
        )
        return 1

    app = RadioApp()
    app.run()
    return app.return_code or 0


if __name__ == "__main__":
    sys.exit(main())
