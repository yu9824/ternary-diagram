from __future__ import annotations
from pathlib import Path

_version_file = Path(__file__).parent / "_version.py"

if _version_file.is_file():
    from ._version import __version__
else:
    __version__ = "unknown"

__license__ = "MIT"
__author__ = "yu9824"
__copyright__ = "Copyright © 2021 yu9824"
__url__ = "http://github.com/yu9824/ternary-diagram/"

from ._api import TernaryDiagram  # noqa: E402

__all__ = ("TernaryDiagram",)
