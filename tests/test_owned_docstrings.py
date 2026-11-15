"""Check the docstring sections and entries owned by user-guide-docs.

The scope is the column "written by this spec" of the docstring ownership
table in the design of user-guide-docs, and nothing else:

- every owned Examples section (``OWNED_EXAMPLES``) has at least one
  ``>>>`` example, and
- every owned Parameters / Attributes entry (``OWNED_ENTRIES``) exists, has
  a sentence that gives its meaning besides the trailing
  ``, by default X``, and does not say ``semi-clockwise``.

Entries and sections owned by upstream specs (``tight_layout``, the
``*_kw`` entries, ``colorbar`` / ``flag_cbar``, the switches added by
annotate-plain-text, the Notes section of the class, and the methods and
functions added upstream) are never read here, so the result of these
tests does not depend on them. The examples are not run here: the shared
doctest runner (``tests/test_doctests.py``) runs them.

Only public names (``ternary_diagram.TernaryDiagram`` and
``ternary_diagram.utils``) are used; no private module is imported.
"""

from __future__ import annotations

import inspect
import re

import pytest

import ternary_diagram
from ternary_diagram import utils

# Examples sections owned by this spec (the ownership table).
OWNED_EXAMPLES: tuple[str, ...] = (
    "TernaryDiagram.__init__",
    "TernaryDiagram.scatter",
    "TernaryDiagram.contour",
    "TernaryDiagram.plot",
    "TernaryDiagram.annotate",
    "TernaryDiagram.colorbar",
    "utils.check_ax",
    "utils.check_2d_vector",
    "utils.check_1d_vector",
    "utils.three2two",
    "utils.get_label",
)

# Parameters / Attributes entries owned by this spec (the ownership table).
# Entries owned by upstream specs are deliberately absent.
OWNED_ENTRIES: dict[str, tuple[str, ...]] = {
    "TernaryDiagram.__init__": (
        "materials",
        "ax",
        "auto_latex_notation",
        "x_",
        "y_",
    ),
    "TernaryDiagram.scatter": (
        "vector",
        "z",
        "z_min",
        "z_max",
        "annotations",
        "**kwargs",
    ),
    "TernaryDiagram.contour": (
        "vector",
        "z",
        "z_min",
        "z_max",
        "fill",
        "**kwargs",
    ),
    "TernaryDiagram.plot": ("vector", "**kwargs"),
    "TernaryDiagram.annotate": ("text", "vector", "**kwargs"),
    "TernaryDiagram.colorbar": (
        "mappable",
        "shrink",
        "format",
        "label",
        "orientation",
        "location",
        "**kwargs",
    ),
    "utils.check_ax": ("ax",),
    "utils.check_2d_vector": ("vector", "scale"),
    "utils.check_1d_vector": ("vector", "scale"),
    "utils.three2two": ("vector",),
    "utils.get_label": ("compound_name",),
}

# Entries written by upstream specs, per docstring. They must never be part
# of OWNED_ENTRIES (checked by test_upstream_entries_are_not_owned).
UPSTREAM_ENTRIES: dict[str, tuple[str, ...]] = {
    "TernaryDiagram.__init__": (
        "tight_layout",  # plot-side-effects
        "border_kw",  # diagram-customization
        "grid_kw",
        "tick_kw",
        "axis_label_kw",
        "vertex_label_kw",
    ),
    "TernaryDiagram.scatter": (
        "colorbar",  # plot-side-effects
        "flag_cbar",
        "auto_latex_notation",  # annotate-plain-text
    ),
    "TernaryDiagram.contour": ("colorbar", "flag_cbar"),
    "TernaryDiagram.annotate": ("auto_latex_notation",),
}

# Docstrings written entirely by upstream specs (no owned section).
UPSTREAM_TARGETS: tuple[str, ...] = (
    "TernaryDiagram",  # the Notes section of the class
    "TernaryDiagram.set_border",
    "TernaryDiagram.set_grid",
    "TernaryDiagram.set_ticks",
    "TernaryDiagram.set_axis_labels",
    "TernaryDiagram.set_vertex_labels",
    "TernaryDiagram.fill",
    "TernaryDiagram.text",
    "TernaryDiagram.tripcolor",
    "TernaryDiagram.heatmapf",
    "utils.check_optional_bool",
    "utils.check_bool",
    "utils.get_tick_values",
    "utils.get_edge_points",
    "utils.get_grid_segments",
    "utils.get_axis_label_position",
    "utils.get_tick_formatter",
    "utils.get_triangular_lattice",
)

ENTRY_SECTIONS: tuple[str, ...] = ("Parameters", "Attributes")
FORBIDDEN_WORD = "semi-clockwise"
DEFAULT_CLAUSE = "by default "

_UNDERLINE = re.compile(r"-{3,}")


def _docstring(target: str) -> str:
    """Return the docstring of a public name under ternary_diagram.

    ``target`` is ``"TernaryDiagram"``, ``"TernaryDiagram.<attribute>"`` or
    ``"utils.<function>"``. The docstring is cleaned with
    :func:`inspect.cleandoc` and is never inherited from a base class.
    """
    head, _, attribute = target.partition(".")
    roots = {"TernaryDiagram": ternary_diagram.TernaryDiagram, "utils": utils}
    if head not in roots:
        raise ValueError(f"unknown target: {target!r}")
    obj = roots[head]
    if attribute:
        obj = inspect.getattr_static(obj, attribute)
        if isinstance(obj, property):
            obj = obj.fget
    doc = getattr(obj, "__doc__", None)
    if not doc:
        pytest.fail(f"{target} has no docstring")
    return inspect.cleandoc(doc)


def _sections(docstring: str) -> dict[str, list[str]]:
    """Split a NumPy-style docstring into its sections.

    A section starts at a header line followed by an underline of dashes,
    and its body runs until the next header. The text before the first
    header is stored under ``""``.
    """
    lines = docstring.splitlines()
    sections: dict[str, list[str]] = {"": []}
    current = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        is_header = (
            i + 1 < len(lines)
            and line.strip() != ""
            and not line.startswith(" ")
            and _UNDERLINE.fullmatch(lines[i + 1].strip()) is not None
        )
        if is_header:
            current = line.strip()
            sections[current] = []
            i += 2
            continue
        sections[current].append(line)
        i += 1
    return sections


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _entry(docstring: str, name: str) -> str:
    """Return one Parameters/Attributes entry.

    The header is a line at the shallowest indentation of the section
    that, stripped, equals ``name`` or starts with ``"<name> :"``, so a
    line in the description of another entry is never taken as a header.
    The entry is the header line and the more-indented lines that follow
    it (blank lines inside the description are kept). The test fails when
    no such entry exists.
    """
    sections = _sections(docstring)
    for section in ENTRY_SECTIONS:
        body = sections.get(section, [])
        header_level = min(
            (_indent(line) for line in body if line.strip()), default=0
        )
        for i, line in enumerate(body):
            stripped = line.strip()
            if _indent(line) != header_level:
                continue
            if stripped != name and not stripped.startswith(f"{name} :"):
                continue
            header_indent = _indent(line)
            entry = [line]
            for following in body[i + 1 :]:
                if following.strip() and _indent(following) <= header_indent:
                    break
                entry.append(following)
            return "\n".join(entry).rstrip()
    pytest.fail(f"entry {name!r} not found in {' / '.join(ENTRY_SECTIONS)}")


def _description(entry: str) -> str:
    """Return the description of an entry as one whitespace-normalized
    string (the header line removed)."""
    _, _, rest = entry.partition("\n")
    return " ".join(rest.split())


def _strip_default_clause(description: str) -> str:
    """Remove a trailing ``, by default X`` clause (or a description that
    is only ``by default X``) and return what is left."""
    head, sep, _ = description.rpartition(DEFAULT_CLAUSE)
    if not sep:
        return description
    head = head.rstrip()
    if head == "" or head.endswith(","):
        return head.rstrip(",").strip()
    # "by default" inside a sentence, not the trailing clause
    return description


# --- scope of the checks ---------------------------------------------------


def test_owned_examples_and_entries_cover_the_same_docstrings() -> None:
    assert len(OWNED_EXAMPLES) == 11
    assert len(set(OWNED_EXAMPLES)) == len(OWNED_EXAMPLES)
    assert set(OWNED_ENTRIES) == set(OWNED_EXAMPLES)


@pytest.mark.parametrize("target", sorted(UPSTREAM_ENTRIES))
def test_upstream_entries_are_not_owned(target: str) -> None:
    """The checks never read the entries written by upstream specs."""
    owned = set(OWNED_ENTRIES.get(target, ()))
    assert owned.isdisjoint(UPSTREAM_ENTRIES[target])


def test_upstream_docstrings_are_not_owned() -> None:
    """The checks never read the docstrings written by upstream specs."""
    assert set(UPSTREAM_TARGETS).isdisjoint(OWNED_EXAMPLES)
    assert set(UPSTREAM_TARGETS).isdisjoint(OWNED_ENTRIES)


# --- the parser itself -----------------------------------------------------

_SAMPLE = inspect.cleandoc(
    """
    Summary.

    Parameters
    ----------
    a : int
        Meaning of a, by default 1
    b : int, optional
        by default 2
    **kwargs
        Passed on.

        Second paragraph.

    Returns
    -------
    int
        Something.

    Examples
    --------
    >>> 1 + 1
    2
    """
)


def test_entry_parser_reads_header_and_description() -> None:
    assert _description(_entry(_SAMPLE, "a")) == "Meaning of a, by default 1"
    assert _description(_entry(_SAMPLE, "**kwargs")) == (
        "Passed on. Second paragraph."
    )
    assert "Returns" not in _entry(_SAMPLE, "**kwargs")


def test_entry_parser_fails_on_missing_entry() -> None:
    with pytest.raises(pytest.fail.Exception, match="'c' not found"):
        _entry(_SAMPLE, "c")
    # an entry outside Parameters / Attributes is not an entry
    with pytest.raises(pytest.fail.Exception, match="'int' not found"):
        _entry(_SAMPLE, "int")


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Meaning of a, by default 1", "Meaning of a"),
        ("by default 2", ""),
        (", by default 2", ""),
        ("Used by default when given.", "Used by default when given."),
        ("No default here.", "No default here."),
    ],
)
def test_strip_default_clause(description: str, expected: str) -> None:
    assert _strip_default_clause(description) == expected


def test_sections_parser_finds_examples() -> None:
    assert any(
        line.lstrip().startswith(">>>")
        for line in _sections(_SAMPLE)["Examples"]
    )


# --- the owned docstrings --------------------------------------------------


@pytest.mark.parametrize("target", OWNED_EXAMPLES)
def test_owned_docstrings_have_examples(target: str) -> None:
    """Each owned Examples section has at least one ``>>>`` example."""
    sections = _sections(_docstring(target))
    assert "Examples" in sections, f"{target} has no Examples section"
    assert any(
        line.lstrip().startswith(">>>") for line in sections["Examples"]
    ), f"the Examples section of {target} has no '>>>' example"


@pytest.mark.parametrize(
    ("target", "name"),
    [
        (target, name)
        for target, names in OWNED_ENTRIES.items()
        for name in names
    ],
)
def test_owned_entries_have_descriptions(target: str, name: str) -> None:
    """Each owned entry exists, has a sentence besides ', by default X',
    and does not contain 'semi-clockwise'."""
    entry = _entry(_docstring(target), name)
    meaning = _strip_default_clause(_description(entry))
    assert meaning, (
        f"{target}: entry {name!r} has no sentence besides "
        f"', by default X':\n{entry}"
    )
    assert FORBIDDEN_WORD not in entry.lower(), (
        f"{target}: entry {name!r} says {FORBIDDEN_WORD!r}:\n{entry}"
    )
