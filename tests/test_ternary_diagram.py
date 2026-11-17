from __future__ import annotations
import inspect
from collections import Counter
from itertools import combinations
from math import sqrt
from types import MappingProxyType

import matplotlib.pyplot as plt
import numpy as np
import pytest
from _skeleton_expected import (
    box_aspect,
    expected_border_lines,
    expected_grid_lines,
    expected_tick_label_texts,
    expected_vertex_label_texts,
    expected_view_limits,
    line_key,
    text_key,
)
from matplotlib.colorbar import Colorbar
from matplotlib.colors import to_rgba

from ternary_diagram import TernaryDiagram

ROOT3_OVER_2 = sqrt(3.0) / 2.0
MATERIALS = ("Li2O", "La2O3", "TiO2")
VECTOR = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
Z = [0.0, 1.0, 2.0]


def _texts(td: TernaryDiagram):
    return {t.get_text(): t.get_position() for t in td.ax.texts}


def test_draws_borders_and_grid(td):
    borders = [line for line in td.ax.lines if line.get_linewidth() == 2]
    grids = [line for line in td.ax.lines if line.get_linewidth() == 0.5]

    assert len(borders) == 3
    assert len(grids) == 27  # 9 lines parallel to each of the 3 edges
    assert len(td.ax.lines) == len(borders) + len(grids)
    vertices = {
        (round(x, 6), round(y, 6))
        for line in borders
        for x, y in zip(*line.get_data())
    }
    assert vertices == {(0.0, 0.0), (1.0, 0.0), (0.5, round(ROOT3_OVER_2, 6))}


def test_vertex_labels_are_counterclockwise_from_top(td):
    texts = _texts(td)

    assert texts["Li$_{2}$O"] == pytest.approx((0.5, ROOT3_OVER_2 + 0.02))
    assert texts["La$_{2}$O$_{3}$"] == pytest.approx((0.0, -0.05))
    assert texts["TiO$_{2}$"] == pytest.approx((1.0, -0.05))


def test_auto_latex_notation_disabled(ax):
    td = TernaryDiagram(MATERIALS, ax=ax, auto_latex_notation=False)

    assert set(MATERIALS) <= set(_texts(td))
    assert "Li$_{2}$O" not in _texts(td)


def test_axis_labels(td):
    texts = [t.get_text() for t in td.ax.texts]

    for i in range(1, 10):
        assert texts.count(f"{i}0") == 3


def test_hides_cartesian_axes(td):
    assert not any(spine.get_visible() for spine in td.ax.spines.values())
    assert td.ax.get_aspect() in ("equal", 1.0)


def test_uses_current_axes_by_default():
    _, ax = plt.subplots()

    td = TernaryDiagram(MATERIALS, tight_layout=True)

    assert td.ax is ax
    assert td.fig is ax.figure


def test_ax_and_fig_are_read_only(td, ax):
    with pytest.raises(AttributeError):
        td.ax = ax
    with pytest.raises(AttributeError):
        td.fig = ax.figure


def test_invalid_ax():
    with pytest.raises(TypeError, match="`ax`"):
        TernaryDiagram(MATERIALS, ax="ax")


def test_multiple_diagrams_in_one_figure():
    _, axes = plt.subplots(1, 2)
    left, right = (
        TernaryDiagram(MATERIALS, ax=ax, tight_layout=True) for ax in axes
    )

    left.scatter(VECTOR)

    assert len(left.ax.collections) == 1
    assert len(right.ax.collections) == 0


def test_records_plotted_coordinates(td):
    td.scatter([[1, 0, 0], [0, 1, 0]])
    td.scatter([[0, 0, 1]])
    td.plot([[1, 0, 0], [0, 0, 1]])

    assert len(td.x_["scatter"]) == len(td.y_["scatter"]) == 2
    np.testing.assert_allclose(td.x_["scatter"][0], [0.5, 0.0])
    np.testing.assert_allclose(td.y_["scatter"][0], [ROOT3_OVER_2, 0.0])
    np.testing.assert_allclose(td.x_["plot"][0], [0.5, 1.0])
    assert "contour" not in td.x_


def test_colorbar(td):
    collection = td.scatter(VECTOR, z=Z, colorbar=False)

    cbar = td.colorbar(collection, label="z")

    assert isinstance(cbar, Colorbar)
    assert cbar.ax.get_ylabel() == "z"
    assert len(td.fig.axes) == 2


def test_colorbar_with_cax(td):
    collection = td.scatter(VECTOR, z=Z, colorbar=False)
    cax = td.fig.add_axes((0.85, 0.1, 0.03, 0.8))

    cbar = td.colorbar(collection, cax=cax)

    assert cbar.ax is cax


def test_colorbar_horizontal(td):
    collection = td.scatter(VECTOR, z=Z, colorbar=False)

    cbar = td.colorbar(collection, orientation="horizontal", location="bottom")

    assert cbar.orientation == "horizontal"


def test_colorbar_defaults_to_a_vertical_colorbar_on_the_right(td):
    collection = td.scatter(VECTOR, z=Z, colorbar=False)

    cbar = td.colorbar(collection)

    assert cbar.orientation == "vertical"
    assert cbar.ax.get_position().x0 > td.ax.get_position().x1


@pytest.mark.parametrize(
    ("location", "orientation"),
    [
        ("right", "vertical"),
        ("left", "vertical"),
        ("top", "horizontal"),
        ("bottom", "horizontal"),
    ],
)
def test_colorbar_orientation_follows_location(td, location, orientation):
    collection = td.scatter(VECTOR, z=Z, colorbar=False)

    cbar = td.colorbar(collection, location=location)

    assert cbar.orientation == orientation


def test_colorbar_rejects_orientation_that_disagrees_with_location(td):
    collection = td.scatter(VECTOR, z=Z, colorbar=False)

    with pytest.raises(TypeError):
        td.colorbar(collection, orientation="vertical", location="bottom")


def _post_draw_context(td: TernaryDiagram):
    # The design keeps the per-diagram state in a name-mangled private
    # attribute without a public accessor.
    return td._TernaryDiagram__post_draw_context


def test_tight_layout_is_the_first_keyword_only_parameter():
    parameters = inspect.signature(TernaryDiagram.__init__).parameters
    keyword_only = [
        name
        for name, parameter in parameters.items()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
    ]

    assert keyword_only[0] == "tight_layout"
    assert parameters["tight_layout"].default is None


@pytest.mark.parametrize(
    "tight_layout, expected",
    [(None, None), (True, True), (False, False), (np.bool_(True), True)],
)
def test_tight_layout_is_kept_per_diagram(ax, tight_layout, expected):
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=tight_layout)

    kept = _post_draw_context(td).tight_layout
    assert kept is expected


def test_tight_layout_defaults_to_none(ax):
    td = TernaryDiagram(MATERIALS, ax=ax)

    assert _post_draw_context(td).tight_layout is None


@pytest.mark.parametrize("tight_layout", ["yes", 1, 0])
def test_invalid_tight_layout_leaves_axes_untouched(ax, tight_layout):
    with pytest.raises(
        TypeError, match="`tight_layout` must be None, True or False"
    ):
        TernaryDiagram(MATERIALS, ax=ax, tight_layout=tight_layout)

    assert len(ax.lines) == 0
    assert len(ax.texts) == 0
    assert all(spine.get_visible() for spine in ax.spines.values())


def test_ax_is_checked_before_tight_layout():
    with pytest.raises(TypeError, match="`ax`"):
        TernaryDiagram(MATERIALS, ax="ax", tight_layout="yes")


def test_colorbar_is_registered_to_the_diagram(ax):
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=True)
    collection = td.scatter(VECTOR, z=Z, colorbar=False)
    context = _post_draw_context(td)
    assert not context.has_colorbar()

    cbar = td.colorbar(collection)

    assert context.has_colorbar()
    cbar.remove()
    assert not context.has_colorbar()


def test_each_diagram_has_its_own_post_draw_context():
    _, axes = plt.subplots(1, 2)
    left, right = (
        TernaryDiagram(MATERIALS, ax=ax, tight_layout=True) for ax in axes
    )

    left.colorbar(left.scatter(VECTOR, z=Z, colorbar=False))

    assert _post_draw_context(left) is not _post_draw_context(right)
    assert _post_draw_context(left).has_colorbar()
    assert not _post_draw_context(right).has_colorbar()


# Characterization of the default skeleton drawn by v3. The expected values
# come from `tests/_skeleton_expected.py`, computed from the v3 formulas.
LATEX_MATERIALS = ("Li$_{2}$O", "La$_{2}$O$_{3}$", "TiO$_{2}$")


def test_default_skeleton_lines_match_v3(td):
    expected = expected_grid_lines() + expected_border_lines()

    assert len(td.ax.lines) == 30
    assert Counter(map(line_key, td.ax.lines)) == Counter(expected)


def test_default_skeleton_texts_match_v3(td):
    expected = (
        expected_vertex_label_texts(LATEX_MATERIALS)
        + expected_tick_label_texts()
    )

    assert len(td.ax.texts) == 30
    assert Counter(map(text_key, td.ax.texts)) == Counter(expected)


def test_default_skeleton_has_no_axis_titles(td):
    labels = set(LATEX_MATERIALS) | {f"{i}0" for i in range(1, 10)}

    assert {text.get_text() for text in td.ax.texts} == labels
    assert td.ax.get_xlabel() == ""
    assert td.ax.get_ylabel() == ""


def test_default_skeleton_adds_grid_before_border(td):
    # The parts are told apart by geometry only, so that this test checks
    # the order and nothing else.
    grid = {key.segment for key in expected_grid_lines()}
    border = {key.segment for key in expected_border_lines()}
    keys = [line_key(line).segment for line in td.ax.lines]
    assert all(key in grid or key in border for key in keys)

    grid_indices = [i for i, key in enumerate(keys) if key in grid]
    border_indices = [i for i, key in enumerate(keys) if key in border]

    assert len(grid_indices) == 27
    assert len(border_indices) == 3
    assert max(grid_indices) < min(border_indices)


def test_default_skeleton_adds_vertex_labels_before_tick_labels(td):
    def where(key):
        return key.text, key.position

    vertex = set(map(where, expected_vertex_label_texts(LATEX_MATERIALS)))
    tick = set(map(where, expected_tick_label_texts()))
    keys = [where(text_key(text)) for text in td.ax.texts]
    assert all(key in vertex or key in tick for key in keys)

    vertex_indices = [i for i, key in enumerate(keys) if key in vertex]
    tick_indices = [i for i, key in enumerate(keys) if key in tick]

    assert len(vertex_indices) == 3
    assert len(tick_indices) == 27
    assert max(vertex_indices) < min(tick_indices)


def test_default_skeleton_view_limits_after_draw(td):
    expected_xlim, expected_ylim = expected_view_limits(box_aspect(td.ax))

    td.fig.canvas.draw()

    assert td.ax.get_xlim() == pytest.approx(expected_xlim, abs=1e-9)
    assert td.ax.get_ylim() == pytest.approx(expected_ylim, abs=1e-9)


def test_default_skeleton_does_not_advance_color_cycle(td):
    (line,) = td.ax.plot([0.0, 1.0], [0.0, 1.0])

    assert to_rgba(line.get_color()) == to_rgba("C0")


# The construction with the settings of the parts (`*_kw`) and its
# validation. The settings are passed to the skeleton, which draws the parts.
PART_KW_NAMES = (
    "border_kw",
    "grid_kw",
    "tick_kw",
    "axis_label_kw",
    "vertex_label_kw",
)
# Not a mapping of names to values: the pairs of a dict as a list.
NOT_A_MAPPING = [("visible", False)]
LABELS_IN_VERTEX_LABEL_KW = {"labels": ("A", "B", "C")}


def _skeleton(td: TernaryDiagram):
    # The parts are reached through the aggregate kept by the diagram until
    # the public `set_*` methods exist.
    return td._TernaryDiagram__skeleton


def _skeleton_keys(ax):
    return Counter(map(line_key, ax.lines)), Counter(map(text_key, ax.texts))


def _default_skeleton_keys():
    return (
        Counter(expected_grid_lines() + expected_border_lines()),
        Counter(
            expected_vertex_label_texts(LATEX_MATERIALS)
            + expected_tick_label_texts()
        ),
    )


def _assert_untouched(ax):
    assert list(ax.lines) == []
    assert list(ax.texts) == []
    assert all(spine.get_visible() for spine in ax.spines.values())
    assert ax.get_aspect() == "auto"


def test_init_signature_matches_the_roadmap():
    positional = inspect.Parameter.POSITIONAL_OR_KEYWORD
    keyword_only = inspect.Parameter.KEYWORD_ONLY
    empty = inspect.Parameter.empty
    parameters = inspect.signature(TernaryDiagram.__init__).parameters

    assert [
        (name, parameter.kind, parameter.default)
        for name, parameter in parameters.items()
    ] == [
        ("self", positional, empty),
        ("materials", positional, empty),
        ("ax", positional, None),
        ("auto_latex_notation", positional, True),
        ("tight_layout", keyword_only, None),
        ("border_kw", keyword_only, None),
        ("grid_kw", keyword_only, None),
        ("tick_kw", keyword_only, None),
        ("axis_label_kw", keyword_only, None),
        ("vertex_label_kw", keyword_only, None),
    ]


PART_KW_CASES = [
    ("border_kw", "border", {"color": "red", "linewidth": 1}),
    ("border_kw", "border", {"visible": False}),
    ("grid_kw", "grid", {"step": 0.05, "linestyle": "--"}),
    ("grid_kw", "grid", {"visible": False, "color": "blue"}),
    ("grid_kw", "grid", {"zorder": 5}),
    ("tick_kw", "ticks", {"step": 0.2, "fmt": "fraction", "fontsize": 8}),
    ("tick_kw", "ticks", {"endpoints": True}),
    ("axis_label_kw", "axis_labels", {"labels": ("A", None, "C")}),
    ("axis_label_kw", "axis_labels", {"labels": ("A", "B", "C"), "pad": 0.2}),
    (
        "vertex_label_kw",
        "vertex_labels",
        {"offsets": ((0.0, 0.1), (-0.1, 0.0), (0.1, 0.0)), "fontsize": 20},
    ),
    ("vertex_label_kw", "vertex_labels", {"visible": False}),
]


@pytest.mark.parametrize("kw_name, part, settings", PART_KW_CASES)
def test_part_kw_means_the_same_as_updating_the_part_after_creation(
    kw_name, part, settings
):
    _, ax_created = plt.subplots()
    _, ax_updated = plt.subplots()

    created = TernaryDiagram(
        MATERIALS, ax=ax_created, tight_layout=True, **{kw_name: settings}
    )
    updated = TernaryDiagram(MATERIALS, ax=ax_updated, tight_layout=True)
    _skeleton(updated).update(part, **settings)

    assert _skeleton_keys(created.ax) != _default_skeleton_keys()
    assert _skeleton_keys(created.ax) == _skeleton_keys(updated.ax)
    assert len(created.ax.get_children()) == len(updated.ax.get_children())


def test_part_kw_draw_the_parts(ax):
    td = TernaryDiagram(
        MATERIALS,
        ax=ax,
        tight_layout=True,
        border_kw={"color": "red"},
        grid_kw={"visible": False},
        tick_kw={"step": 0.5},
        axis_label_kw={"labels": ("A", "B", "C")},
        vertex_label_kw={"fontsize": 20},
    )

    assert [to_rgba(line.get_color()) for line in td.ax.lines] == [
        to_rgba("red")
    ] * 3
    texts = {text.get_text(): text for text in td.ax.texts}
    assert sorted(texts) == sorted(["50", "A", "B", "C", *LATEX_MATERIALS])
    assert [text.get_text() for text in td.ax.texts].count("50") == 3
    assert all(texts[label].get_fontsize() == 20 for label in LATEX_MATERIALS)


@pytest.mark.parametrize(
    "settings",
    [None, {}, MappingProxyType({})],
    ids=["none", "empty-dict", "empty-mapping-proxy"],
)
def test_empty_part_kw_draw_the_default_skeleton(ax, settings):
    td = TernaryDiagram(
        MATERIALS,
        ax=ax,
        tight_layout=True,
        **dict.fromkeys(PART_KW_NAMES, settings),
    )

    assert _skeleton_keys(td.ax) == _default_skeleton_keys()


def test_part_kw_accept_any_mapping(ax):
    td = TernaryDiagram(
        MATERIALS,
        ax=ax,
        tight_layout=True,
        grid_kw=MappingProxyType({"visible": False}),
    )

    assert len(td.ax.lines) == 3


def test_part_kw_are_not_changed(ax):
    settings = {name: {"zorder": 5, "visible": True} for name in PART_KW_NAMES}
    copies = {name: dict(kw) for name, kw in settings.items()}

    TernaryDiagram(MATERIALS, ax=ax, tight_layout=True, **settings)

    assert settings == copies


@pytest.mark.parametrize("kw_name", PART_KW_NAMES)
@pytest.mark.parametrize(
    "value",
    [NOT_A_MAPPING, "visible", 0, False, {1: True}],
    ids=["list-of-pairs", "str", "zero", "false", "non-str-key"],
)
def test_invalid_part_kw_leave_axes_untouched(ax, kw_name, value):
    with pytest.raises(
        TypeError, match=f"`{kw_name}` must be None or a mapping"
    ):
        TernaryDiagram(MATERIALS, ax=ax, tight_layout=True, **{kw_name: value})

    _assert_untouched(ax)


@pytest.mark.parametrize(
    "labels", [("A", "B", "C"), None], ids=["labels", "none"]
)
def test_vertex_label_kw_cannot_contain_labels(ax, labels):
    with pytest.raises(
        ValueError, match="`vertex_label_kw` cannot contain `labels`"
    ) as excinfo:
        TernaryDiagram(
            MATERIALS,
            ax=ax,
            tight_layout=True,
            vertex_label_kw={"labels": labels, "fontsize": 20},
        )

    assert "`materials`" in str(excinfo.value)
    _assert_untouched(ax)


@pytest.mark.parametrize(
    "materials, count",
    [
        ((), 0),
        (["Li2O"], 1),
        (("Li2O", "La2O3"), 2),
        ("AB", 2),
        (np.array(["Li2O", "La2O3"]), 2),
        (iter(["Li2O", "La2O3"]), 2),
    ],
    ids=["empty", "list-of-1", "tuple-of-2", "str-of-2", "array", "iterator"],
)
def test_materials_with_fewer_than_3_items(ax, materials, count):
    with pytest.raises(
        ValueError, match=f"`materials` needs 3 materials.*but got {count}"
    ):
        TernaryDiagram(materials, ax=ax, tight_layout=True)

    _assert_untouched(ax)


@pytest.mark.parametrize("materials", [None, 3], ids=["none", "int"])
def test_materials_that_are_not_iterable(ax, materials):
    with pytest.raises(TypeError, match="`materials` must be a sequence"):
        TernaryDiagram(materials, ax=ax, tight_layout=True)

    _assert_untouched(ax)


def test_materials_with_more_than_3_items_use_the_first_3(ax):
    td = TernaryDiagram([*MATERIALS, "SiO2"], ax=ax, tight_layout=True)

    assert _skeleton_keys(td.ax) == _default_skeleton_keys()


def test_items_after_the_3rd_material_are_not_validated(ax):
    td = TernaryDiagram([*MATERIALS, 1], ax=ax, tight_layout=True)

    assert _skeleton_keys(td.ax) == _default_skeleton_keys()


@pytest.mark.parametrize("auto_latex_notation", [True, False])
@pytest.mark.parametrize("materials", ["ABC", "ABCD"])
def test_str_materials_label_one_vertex_per_character(
    ax, materials, auto_latex_notation
):
    # ternary-diagram v3 takes a str as a sequence of 1-letter materials.
    td = TernaryDiagram(
        materials,
        ax=ax,
        auto_latex_notation=auto_latex_notation,
        tight_layout=True,
    )

    assert Counter(map(text_key, td.ax.texts)) == Counter(
        expected_vertex_label_texts(("A", "B", "C"))
        + expected_tick_label_texts()
    )


def test_str_materials_with_vertex_label_kw(ax):
    td = TernaryDiagram(
        "ABC", ax=ax, tight_layout=True, vertex_label_kw={"fontsize": 20}
    )

    vertex_labels = _skeleton(td).artists("vertex_labels")
    assert [text.get_text() for text in vertex_labels] == ["A", "B", "C"]
    assert [text.get_fontsize() for text in vertex_labels] == [20] * 3


def test_non_str_material_with_auto_latex_notation(ax):
    # The error of ternary-diagram v3, raised by `get_label`.
    with pytest.raises(ValueError, match="must be string"):
        TernaryDiagram((1, "La2O3", "TiO2"), ax=ax, tight_layout=True)

    assert list(ax.lines) == []
    assert list(ax.texts) == []


def test_non_str_material_without_auto_latex_notation(ax):
    td = TernaryDiagram(
        (1, "La2O3", "TiO2"),
        ax=ax,
        auto_latex_notation=False,
        tight_layout=True,
    )

    vertex_labels = _skeleton(td).artists("vertex_labels")
    assert [text.get_text() for text in vertex_labels] == [
        "1",
        "La2O3",
        "TiO2",
    ]


@pytest.mark.parametrize(
    "kw",
    [
        {"grid_kw": {"step": 0}},
        {"tick_kw": {"fmt": 1}},
        {"axis_label_kw": {"labels": ("A",)}},
        {"axis_label_kw": {"unknown_property": 1}},
    ],
    ids=["grid-step", "tick-fmt", "axis-labels", "unknown-property"],
)
def test_invalid_part_settings_leave_no_skeleton_artist(ax, kw):
    with pytest.raises((TypeError, ValueError, AttributeError)):
        TernaryDiagram(MATERIALS, ax=ax, tight_layout=True, **kw)

    assert list(ax.lines) == []
    assert list(ax.texts) == []


# The order of the validation: ax -> materials -> tight_layout -> *_kw
# (border_kw -> grid_kw -> tick_kw -> axis_label_kw -> vertex_label_kw).
# When several arguments are invalid, the first one in this order raises.
def test_ax_is_checked_first():
    with pytest.raises(TypeError, match="`ax`"):
        TernaryDiagram(
            ("Li2O", "La2O3"),
            ax="ax",
            tight_layout="yes",
            border_kw=NOT_A_MAPPING,
            vertex_label_kw=LABELS_IN_VERTEX_LABEL_KW,
        )


@pytest.mark.parametrize(
    "materials, error, match",
    [
        (("Li2O", "La2O3"), ValueError, "`materials` needs 3 materials"),
        (None, TypeError, "`materials` must be a sequence"),
    ],
    ids=["too-few", "not-iterable"],
)
def test_materials_are_checked_before_tight_layout_and_part_kw(
    ax, materials, error, match
):
    with pytest.raises(error, match=match):
        TernaryDiagram(
            materials,
            ax=ax,
            tight_layout="yes",
            grid_kw=NOT_A_MAPPING,
            vertex_label_kw=LABELS_IN_VERTEX_LABEL_KW,
        )

    _assert_untouched(ax)


def test_materials_are_checked_before_part_kw(ax):
    with pytest.raises(ValueError, match="`materials` needs 3 materials"):
        TernaryDiagram(
            ("Li2O", "La2O3"), ax=ax, tight_layout=True, grid_kw=NOT_A_MAPPING
        )

    _assert_untouched(ax)


@pytest.mark.parametrize(
    "kw",
    [
        {"grid_kw": NOT_A_MAPPING},
        {"vertex_label_kw": LABELS_IN_VERTEX_LABEL_KW},
    ],
    ids=["not-a-mapping", "labels"],
)
def test_tight_layout_is_checked_before_part_kw(ax, kw):
    with pytest.raises(
        TypeError, match="`tight_layout` must be None, True or False"
    ):
        TernaryDiagram(MATERIALS, ax=ax, tight_layout="yes", **kw)

    _assert_untouched(ax)


@pytest.mark.parametrize("first, second", list(combinations(PART_KW_NAMES, 2)))
def test_part_kw_are_checked_in_order(ax, first, second):
    with pytest.raises(TypeError, match=f"`{first}` must be None"):
        TernaryDiagram(
            MATERIALS,
            ax=ax,
            tight_layout=True,
            **{first: NOT_A_MAPPING, second: NOT_A_MAPPING},
        )

    _assert_untouched(ax)


@pytest.mark.parametrize("kw_name", PART_KW_NAMES[:-1])
def test_part_kw_types_are_checked_before_the_vertex_labels(ax, kw_name):
    with pytest.raises(TypeError, match=f"`{kw_name}` must be None"):
        TernaryDiagram(
            MATERIALS,
            ax=ax,
            tight_layout=True,
            vertex_label_kw=LABELS_IN_VERTEX_LABEL_KW,
            **{kw_name: NOT_A_MAPPING},
        )

    _assert_untouched(ax)


def test_part_kw_are_checked_before_drawing_any_part(ax):
    # An invalid setting of a part is found by the part when it is drawn,
    # but an invalid `vertex_label_kw` is found before drawing anything.
    with pytest.raises(ValueError, match="`vertex_label_kw`"):
        TernaryDiagram(
            MATERIALS,
            ax=ax,
            tight_layout=True,
            grid_kw={"step": 0},
            vertex_label_kw=LABELS_IN_VERTEX_LABEL_KW,
        )

    _assert_untouched(ax)


# --- aspect of the Axes ---------------------------------------------------
# ternary-diagram 3.x keeps the aspect by widening the data limits. 4.0.0
# will shrink the Axes box instead; users can try it now by changing the
# setting after construction, which the diagram must not undo.


def test_aspect_is_equal_with_adjustable_datalim(td):
    assert td.ax.get_aspect() in ("equal", 1.0)
    assert td.ax.get_adjustable() == "datalim"


def test_aspect_changed_by_the_user_is_kept(td):
    td.ax.set_aspect("equal", adjustable="box")

    td.scatter(VECTOR, z=Z, colorbar=False)
    td.contour(VECTOR, z=Z, colorbar=False)
    td.set_grid(step=0.2)
    td.set_ticks(step=0.2)

    assert td.ax.get_aspect() in ("equal", 1.0)
    assert td.ax.get_adjustable() == "box"
