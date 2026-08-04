"""Entry point for the radio-tui CLI."""
from __future__ import annotations

import sys

__version__ = "0.1.0"


def main() -> int:
    """CLI entry point. Returns a process exit code."""
    print(f"radio-tui {__version__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
