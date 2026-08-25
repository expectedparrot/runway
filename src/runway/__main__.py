"""``python -m runway`` -- the same entry point as the ``runway`` script."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
