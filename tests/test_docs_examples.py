"""The quick start shared by the README and the top page of the docs.

Neither Sphinx nor the doctest runner executes these two code blocks, so
this test checks that they are the same and that they run without errors
or FutureWarning. Docstring examples are run by ``test_doctests.py`` and
the user guide pages are executed by MyST-NB when the docs are built.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
TOP_PAGE = ROOT / "docs_src" / "index.md"

_PYTHON_BLOCK = re.compile(r"^```python\n(.*?)^```", re.DOTALL | re.MULTILINE)


def _first_python_block(markdown_path: Path) -> str:
    """Return the first ```python fenced code block of a Markdown file."""
    match = _PYTHON_BLOCK.search(markdown_path.read_text(encoding="utf-8"))
    if match is None:
        pytest.fail(f"{markdown_path.name} has no ```python code block")
    return match.group(1)


def test_first_python_block_reads_the_first_fence_only(tmp_path):
    page = tmp_path / "page.md"
    page.write_text(
        "```bash\npip install x\n```\n\n```python\nfirst = 1\n```\n\n"
        "```python\nsecond = 2\n```\n",
        encoding="utf-8",
    )

    assert _first_python_block(page) == "first = 1\n"


def test_quick_start_examples_match_and_run(tmp_path, monkeypatch):
    """README.md and docs_src/index.md share the same quick start, which
    runs."""
    readme_code = _first_python_block(README)
    top_page_code = _first_python_block(TOP_PAGE)
    assert readme_code == top_page_code

    # The example saves a figure; keep it out of the repository.
    monkeypatch.chdir(tmp_path)
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        exec(compile(readme_code, str(README), "exec"), {})

    assert (tmp_path / "figure.png").is_file()
