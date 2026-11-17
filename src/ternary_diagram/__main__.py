from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__

__all__ = ("main",)


def main(cli_args: Sequence[str], prog: str | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Draw beautiful ternary diagrams with matplotlib.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        help="show current version",
        version=f"%(prog)s: {__version__}",
    )
    parser.parse_args(cli_args)


def entrypoint() -> None:
    main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:], prog="ternary-diagram")
