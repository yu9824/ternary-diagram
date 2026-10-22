import inspect
from math import sqrt

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.colorbar import Colorbar

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

    td = TernaryDiagram(MATERIALS)

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
    left, right = (TernaryDiagram(MATERIALS, ax=ax) for ax in axes)

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
    collection = td.scatter(VECTOR, z=Z, flag_cbar=False)

    cbar = td.colorbar(collection, label="z")

    assert isinstance(cbar, Colorbar)
    assert cbar.ax.get_ylabel() == "z"
    assert len(td.fig.axes) == 2


def test_colorbar_with_cax(td):
    collection = td.scatter(VECTOR, z=Z, flag_cbar=False)
    cax = td.fig.add_axes((0.85, 0.1, 0.03, 0.8))

    cbar = td.colorbar(collection, cax=cax)

    assert cbar.ax is cax


def test_colorbar_horizontal(td):
    collection = td.scatter(VECTOR, z=Z, flag_cbar=False)

    cbar = td.colorbar(collection, orientation="horizontal", location="bottom")

    assert cbar.orientation == "horizontal"


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
    collection = td.scatter(VECTOR, z=Z, flag_cbar=False)
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

    left.colorbar(left.scatter(VECTOR, z=Z, flag_cbar=False))

    assert _post_draw_context(left) is not _post_draw_context(right)
    assert _post_draw_context(left).has_colorbar()
    assert not _post_draw_context(right).has_colorbar()
