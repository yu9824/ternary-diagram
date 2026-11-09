from math import sqrt

import matplotlib.text
import numpy as np
import pytest
from matplotlib.colors import to_rgba

from ternary_diagram import TernaryDiagram, _api

MATERIALS = ("Li2O", "La2O3", "TiO2")
ROOT3_OVER_2 = sqrt(3.0) / 2.0
# 上の頂点の座標 (the top vertex)
TOP_XY = (0.5, ROOT3_OVER_2)
CENTER = [1, 1, 1]
CENTER_XY = (0.5, ROOT3_OVER_2 / 3)


@pytest.mark.parametrize(
    "vector",
    [[1, 0, 0], [2, 0, 0], [[1, 0, 0]], np.array([1, 0, 0])],
)
def test_text_is_placed_at_the_composition(td, vector):
    text = td.text("Liquid", vector)

    assert isinstance(text, matplotlib.text.Text)
    assert text in td.ax.texts
    assert text.get_text() == "Liquid"
    assert text.get_position() == pytest.approx(TOP_XY)


def test_text_is_placed_at_a_normalized_composition(td):
    text = td.text("Liquid", [2, 2, 2])

    assert text.get_position() == pytest.approx(CENTER_XY)


def test_text_is_centered_by_default(td):
    text = td.text("Liquid", CENTER)

    assert text.get_horizontalalignment() == "center"
    assert text.get_verticalalignment() == "center"
    # 組成点からずらさない (not shifted from the composition)
    assert text.get_position() == pytest.approx(CENTER_XY)


@pytest.mark.parametrize(
    "kwargs, expected_ha, expected_va",
    [
        ({"ha": "left"}, "left", "center"),
        ({"horizontalalignment": "right"}, "right", "center"),
        ({"va": "top"}, "center", "top"),
        ({"verticalalignment": "bottom"}, "center", "bottom"),
        ({"fontdict": {"ha": "left"}}, "left", "center"),
        ({"fontdict": {"verticalalignment": "top"}}, "center", "top"),
        ({"ha": "right", "va": "baseline"}, "right", "baseline"),
    ],
)
def test_text_alignment_can_be_overridden(
    td, kwargs, expected_ha, expected_va
):
    text = td.text("Liquid", CENTER, **kwargs)

    assert text.get_horizontalalignment() == expected_ha
    assert text.get_verticalalignment() == expected_va


def test_text_default_zorder(td):
    (polygon,) = td.fill([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    (line,) = td.plot([[1, 0, 0], [0, 0, 1]])
    scatter = td.scatter([CENTER])

    text = td.text("Liquid", CENTER)

    zorder = text.get_zorder()
    assert zorder == _api.DEFAULT_ZORDER_TEXT == 4
    assert polygon.get_zorder() < zorder
    skeleton_lines = td.border_lines_ + td.grid_lines_
    assert skeleton_lines
    assert all(line_.get_zorder() < zorder for line_ in skeleton_lines)
    assert line.get_zorder() < zorder
    assert scatter.get_zorder() < zorder


def test_text_default_zorder_does_not_depend_on_the_call_order(td):
    text = td.text("Liquid", CENTER)

    (polygon,) = td.fill([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    scatter = td.scatter([CENTER])

    assert polygon.get_zorder() < text.get_zorder()
    assert scatter.get_zorder() < text.get_zorder()


def test_text_default_zorder_can_be_overridden(td):
    assert td.text("Liquid", CENTER).get_zorder() == 4
    assert td.text("Liquid", CENTER, zorder=1).get_zorder() == 1


def test_text_kwargs_are_passed_to_matplotlib(td):
    text = td.text("Liquid", CENTER, fontsize=14, color="red", rotation=30)

    assert text.get_fontsize() == 14
    assert to_rgba(text.get_color()) == pytest.approx(to_rgba("red"))
    assert text.get_rotation() == pytest.approx(30)


def test_text_does_not_set_fontsize(td):
    default = matplotlib.text.Text().get_fontsize()

    text = td.text("Liquid", CENTER)

    assert text.get_fontsize() == default


def test_text_records_coordinates(td):
    td.text("Liquid", [1, 0, 0])
    td.text("Solid", [2, 2, 2])

    assert len(td.x_["text"]) == len(td.y_["text"]) == 2
    np.testing.assert_allclose(td.x_["text"][0], [0.5])
    np.testing.assert_allclose(td.y_["text"][0], [ROOT3_OVER_2])
    np.testing.assert_allclose(td.x_["text"][1], [CENTER_XY[0]])
    np.testing.assert_allclose(td.y_["text"][1], [CENTER_XY[1]])


def test_text_does_not_add_colorbar(td):
    n_axes = len(td.fig.axes)

    td.text("Liquid", CENTER)

    assert len(td.fig.axes) == n_axes


@pytest.mark.parametrize(
    "vector",
    [[1, 2], [1, 2, 3, 4], [[1, 0, 0], [0, 1, 0]]],
)
def test_text_invalid_vector_draws_nothing(td, vector):
    n_texts = len(td.ax.texts)

    with pytest.raises(ValueError, match="length must be 3"):
        td.text("Liquid", vector)

    assert len(td.ax.texts) == n_texts
    assert "text" not in td.x_
    assert "text" not in td.y_


# --- auto_latex_notation (化学式の整形 / formatting chemical formulas) ---


@pytest.fixture
def td_plain(ax):
    """A diagram that does not format chemical formulas by default."""
    return TernaryDiagram(
        MATERIALS, ax=ax, auto_latex_notation=False, tight_layout=True
    )


def test_text_formats_chemical_formula_by_default(td):
    assert td.text("Li2O", CENTER).get_text() == "Li$_{2}$O"


def test_text_auto_latex_notation_false_applies_to_the_call_only(td):
    assert (
        td.text("Li2O", CENTER, auto_latex_notation=False).get_text() == "Li2O"
    )
    # 三角図単位の設定は書き換わらない (the diagram setting is unchanged)
    assert td.text("Li2O", CENTER).get_text() == "Li$_{2}$O"


def test_text_explicit_true_formats_on_default_diagram(td):
    assert (
        td.text("Li2O", CENTER, auto_latex_notation=True).get_text()
        == "Li$_{2}$O"
    )


@pytest.mark.parametrize("kwargs", [{}, {"auto_latex_notation": None}])
def test_text_inherits_diagram_setting_without_formatting(td_plain, kwargs):
    assert td_plain.text("Li2O", CENTER, **kwargs).get_text() == "Li2O"


def test_text_auto_latex_notation_true_overrides_diagram_setting(td_plain):
    assert (
        td_plain.text("Li2O", CENTER, auto_latex_notation=True).get_text()
        == "Li$_{2}$O"
    )
    # 三角図単位の設定は書き換わらない (the diagram setting is unchanged)
    assert td_plain.text("Li2O", CENTER).get_text() == "Li2O"


@pytest.mark.parametrize(
    "value, expected",
    [(np.bool_(False), "Li2O"), (np.bool_(True), "Li$_{2}$O")],
)
def test_text_accepts_numpy_bool(td, value, expected):
    assert (
        td.text("Li2O", CENTER, auto_latex_notation=value).get_text()
        == expected
    )


def test_text_does_not_warn_without_auto_latex_notation(td, recwarn):
    td.text("Sample 1", CENTER)

    assert not [w for w in recwarn if issubclass(w.category, FutureWarning)]


@pytest.mark.parametrize(
    "string", ["Li2O", "Sample 1", "LiF + Li2O", "L + α", "Liquid"]
)
def test_text_formats_like_annotate(td, string):
    text = td.text(string, CENTER)
    annotation = td.annotate(string, CENTER, auto_latex_notation=True)

    assert text.get_text() == annotation.get_text()


@pytest.mark.parametrize("auto_latex_notation", [None, True, False])
def test_text_does_not_format_non_str(td, auto_latex_notation):
    text = td.text(1.5, CENTER, auto_latex_notation=auto_latex_notation)

    assert text.get_text() == "1.5"


@pytest.mark.parametrize("value", [1, 0, "yes"])
def test_text_invalid_auto_latex_notation_draws_nothing(td, value):
    n_texts = len(td.ax.texts)

    with pytest.raises(TypeError, match="auto_latex_notation"):
        td.text("Li2O", CENTER, auto_latex_notation=value)

    assert len(td.ax.texts) == n_texts
    assert "text" not in td.x_
    assert "text" not in td.y_


# 結合テスト: 土台を描き直した後の重なり順
# (integration tests: stacking order after redrawing the skeleton)
def _assert_layers_are_stacked(layers):
    for (back_name, back), (front_name, front) in zip(layers, layers[1:]):
        assert back, back_name
        assert front, front_name
        back_zorder = max(artist.get_zorder() for artist in back)
        front_zorder = min(artist.get_zorder() for artist in front)
        assert back_zorder < front_zorder, (
            f"{back_name} (zorder {back_zorder}) must be behind "
            f"{front_name} (zorder {front_zorder})"
        )


def _redraw_skeleton(td):
    td.set_grid(step=0.2, linewidth=0.8)
    td.set_border(linewidth=2.0)


@pytest.mark.parametrize(
    "redraw_first", [False, True], ids=["redraw-last", "redraw-first"]
)
def test_stacking_order_after_redrawing_the_skeleton(td, redraw_first):
    if redraw_first:
        _redraw_skeleton(td)

    contour = td.contour(
        [[1, 0, 0], [0, 1, 0], [0, 0, 1], CENTER],
        z=[0, 1, 2, 3],
        colorbar=False,
    )
    polygons = td.fill([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    tie_lines = td.plot([[1, 0, 0], [0, 0, 1]])
    scatter = td.scatter([CENTER])
    annotation = td.annotate("A", CENTER)
    text = td.text("Liquid", CENTER)

    if not redraw_first:
        _redraw_skeleton(td)

    # 描き直した線が使われている (the redrawn lines are in use)
    skeleton_lines = td.border_lines_ + td.grid_lines_
    assert len(td.grid_lines_) == 3 * 4
    assert all(line.get_linewidth() == 2.0 for line in td.border_lines_)
    assert all(line in td.ax.lines for line in skeleton_lines)

    _assert_layers_are_stacked(
        [
            ("contour", [contour]),
            ("fill", polygons),
            ("skeleton lines", skeleton_lines),
            ("tie line", tie_lines),
            ("scatter and annotation", [scatter, annotation]),
            ("text", [text]),
        ]
    )
