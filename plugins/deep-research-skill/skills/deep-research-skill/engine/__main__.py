"""Module entry point: `python -m engine ...` (run from the skill directory)."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
