import warnings
from math import sqrt

import matplotlib.pyplot as plt
import matplotlib.text
import numpy as np
import pytest
from _warning_filters import raise_on_warnings
from matplotlib.colors import to_rgba
from matplotlib.patches import Polygon

from ternary_diagram import TernaryDiagram, _api

MATERIALS = ("Li2O", "La2O3", "TiO2")


def test_default_zorder_constants():
    # 既存の定数は変えない (existing constants are unchanged)
    assert _api.DEFAULT_ZORDER_CONTOUR == 0
    assert _api.DEFAULT_ZORDER_GRIDS == 1
    assert _api.DEFAULT_ZORDER_PLOTS == 2
    assert _api.DEFAULT_ZORDER_SCATTER == 3

    assert _api.DEFAULT_ZORDER_FILL == 0.5
    assert _api.DEFAULT_ZORDER_TEXT == 4
    assert (
        _api.DEFAULT_ZORDER_CONTOUR
        < _api.DEFAULT_ZORDER_FILL
        < _api.DEFAULT_ZORDER_GRIDS
        < _api.DEFAULT_ZORDER_PLOTS
        < _api.DEFAULT_ZORDER_SCATTER
        < _api.DEFAULT_ZORDER_TEXT
    )
    # annotate と土台の文字は matplotlib の既定 (3) のまま
    # (annotations and skeleton labels keep matplotlib's default zorder)
    assert matplotlib.text.Text.zorder == 3
    assert _api.DEFAULT_ZORDER_TEXT > matplotlib.text.Text.zorder


def test_default_zorder_heatmap_is_behind_fill():
    if not hasattr(_api, "DEFAULT_ZORDER_HEATMAP"):
        pytest.skip(
            "DEFAULT_ZORDER_HEATMAP is not defined because heatmaps is not "
            "merged yet; heatmaps checks HEATMAP < FILL when merged later"
        )
    assert _api.DEFAULT_ZORDER_HEATMAP < _api.DEFAULT_ZORDER_FILL


ROOT3_OVER_2 = sqrt(3.0) / 2.0
TRIANGLE = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
# 上・左下・右下の頂点の座標 (top, bottom-left and bottom-right vertices)
TRIANGLE_XY = [[0.5, ROOT3_OVER_2], [0.0, 0.0], [1.0, 0.0]]


@pytest.mark.parametrize(
    "vector",
    [TRIANGLE, [[2, 0, 0], [0, 4, 0], [0, 0, 1]], np.array(TRIANGLE)],
)
def test_fill_draws_closed_polygon(td, vector):
    patches = td.fill(vector)

    assert isinstance(patches, list)
    assert len(patches) == 1
    (polygon,) = patches
    assert isinstance(polygon, Polygon)
    assert polygon in td.ax.patches
    assert polygon.get_closed()
    xy = polygon.get_xy()
    np.testing.assert_allclose(xy[:-1], TRIANGLE_XY)
    # 閉じた多角形の最後の点は最初の点 (closed: the last point is the first)
    np.testing.assert_allclose(xy[-1], xy[0])


def test_fill_keeps_the_order_of_the_vertices(td):
    # 自己交差する順でも並べ替えない (self-intersecting order is kept)
    vector = [[1, 0, 0], [0, 0, 1], [0, 1, 0], [0.5, 0, 0.5]]

    (polygon,) = td.fill(vector)

    np.testing.assert_allclose(
        polygon.get_xy()[:-1],
        [
            [0.5, ROOT3_OVER_2],
            [1.0, 0.0],
            [0.0, 0.0],
            [0.75, ROOT3_OVER_2 / 2],
        ],
    )


def test_fill_label_is_shown_in_legend(td):
    (polygon,) = td.fill(TRIANGLE, label="A")

    handles, labels = td.ax.get_legend_handles_labels()

    assert labels == ["A"]
    assert handles == [polygon]
    legend = td.ax.legend()
    assert [text.get_text() for text in legend.get_texts()] == ["A"]


def test_fill_uses_matplotlib_color_cycle(td):
    vector = [[0.5, 0.25, 0.25], [0.25, 0.5, 0.25], [0.25, 0.25, 0.5]]

    (first,) = td.fill(vector)
    (second,) = td.fill(vector)

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    assert first.get_facecolor() == pytest.approx(to_rgba(colors[0]))
    assert second.get_facecolor() == pytest.approx(to_rgba(colors[1]))


def test_fill_default_zorder(td):
    contour = td.contour(
        [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1]],
        z=[0, 1, 2, 3],
        colorbar=False,
    )
    (line,) = td.plot([[1, 0, 0], [0, 0, 1]])
    scatter = td.scatter([[1, 1, 1]])
    annotation = td.annotate("A", [1, 1, 1])

    (polygon,) = td.fill(TRIANGLE)

    zorder = polygon.get_zorder()
    assert zorder == _api.DEFAULT_ZORDER_FILL == 0.5
    assert contour.get_zorder() < zorder
    skeleton_lines = td.border_lines_ + td.grid_lines_
    assert skeleton_lines
    assert all(zorder < line_.get_zorder() for line_ in skeleton_lines)
    assert zorder < line.get_zorder()
    assert zorder < scatter.get_zorder()
    assert zorder < annotation.get_zorder()


def test_fill_default_zorder_after_redrawing_the_grid(td):
    (polygon,) = td.fill(TRIANGLE)

    grid_lines = td.set_grid(step=0.2)

    assert grid_lines
    assert all(polygon.get_zorder() < line.get_zorder() for line in grid_lines)
    assert all(
        polygon.get_zorder() < line.get_zorder() for line in td.border_lines_
    )


def test_fill_default_zorder_can_be_overridden(td):
    assert td.fill(TRIANGLE)[0].get_zorder() == 0.5
    assert td.fill(TRIANGLE, zorder=5)[0].get_zorder() == 5


def test_fill_kwargs_are_passed_to_matplotlib(td):
    (polygon,) = td.fill(
        TRIANGLE,
        facecolor="red",
        edgecolor="blue",
        alpha=0.3,
        hatch="//",
    )

    assert polygon.get_facecolor() == pytest.approx(to_rgba("red", 0.3))
    assert polygon.get_edgecolor() == pytest.approx(to_rgba("blue", 0.3))
    assert polygon.get_alpha() == 0.3
    assert polygon.get_hatch() == "//"


def test_fill_records_coordinates(td):
    td.fill(TRIANGLE)
    td.fill([[2, 0, 0], [0, 4, 0], [0, 0, 1], [1, 1, 0]])

    assert len(td.x_["fill"]) == len(td.y_["fill"]) == 2
    np.testing.assert_allclose(td.x_["fill"][0], [0.5, 0.0, 1.0])
    np.testing.assert_allclose(td.y_["fill"][0], [ROOT3_OVER_2, 0.0, 0.0])
    np.testing.assert_allclose(td.x_["fill"][1], [0.5, 0.0, 1.0, 0.25])
    np.testing.assert_allclose(
        td.y_["fill"][1], [ROOT3_OVER_2, 0.0, 0.0, ROOT3_OVER_2 / 2]
    )


def test_fill_does_not_add_colorbar(td):
    n_axes = len(td.fig.axes)

    td.fill(TRIANGLE)

    assert len(td.fig.axes) == n_axes


@pytest.mark.parametrize(
    "vector, match",
    [
        ([[1, 2], [3, 4]], r"shape must be \(n, 3\), but got \(2, 2\)"),
        ([1, 2, 3], r"shape must be \(n, 3\), but got \(3,\)"),
        (
            [[1, 0, 0], [0, 1, 0]],
            "at least 3 vertices to draw a polygon, but got 2",
        ),
        ([[1, 0, 0]], "at least 3 vertices to draw a polygon, but got 1"),
    ],
)
def test_fill_invalid_vector_draws_nothing(td, vector, match):
    n_patches = len(td.ax.patches)

    with pytest.raises(ValueError, match=match):
        td.fill(vector)

    assert len(td.ax.patches) == n_patches
    assert "fill" not in td.x_
    assert "fill" not in td.y_


# 結合テスト: 既存の描画と並べたときの重なり順
# (integration tests: stacking order next to the existing plots)
# 奥から手前への層 (layers from back to front)
STACKING_ORDER = (
    "contour",
    "fill",
    "skeleton lines",
    "tie line",
    "scatter and annotation",
    "text",
)
CENTER = [1, 1, 1]
LAYER_DRAWERS = {
    "contour": lambda td: [
        td.contour(
            [[1, 0, 0], [0, 1, 0], [0, 0, 1], CENTER],
            z=[0, 1, 2, 3],
            colorbar=False,
        )
    ],
    "fill": lambda td: td.fill(TRIANGLE),
    "tie line": lambda td: td.plot([[1, 0, 0], [0, 0, 1]]),
    "scatter and annotation": lambda td: [
        td.scatter([CENTER]),
        td.annotate("A", CENTER),
    ],
    "text": lambda td: [td.text("Liquid", CENTER)],
}


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


@pytest.mark.parametrize(
    "drawing_order",
    [
        pytest.param(list(LAYER_DRAWERS), id="back-to-front"),
        pytest.param(list(LAYER_DRAWERS)[::-1], id="front-to-back"),
    ],
)
def test_stacking_order_does_not_depend_on_the_drawing_order(
    td, drawing_order
):
    artists = {name: LAYER_DRAWERS[name](td) for name in drawing_order}
    artists["skeleton lines"] = td.border_lines_ + td.grid_lines_

    _assert_layers_are_stacked(
        [(name, artists[name]) for name in STACKING_ORDER]
    )


# 結合テスト: 描画後処理 (integration tests: processing after drawing)
SUBPLOT_PARAMS = ("left", "bottom", "right", "top", "wspace", "hspace")
# 警告文の要点 (essentials of the layout warning, checked with `match=`)
LAYOUT_WARNING_MATCH = r"(?s)(?=.*4\.0\.0)(?=.*`tight_layout=True`)"


def _subplotpars(fig) -> dict:
    return {name: getattr(fig.subplotpars, name) for name in SUBPLOT_PARAMS}


def _is_layout_future_warning(warning) -> bool:
    return issubclass(warning.category, FutureWarning) and (
        "tight_layout" in str(warning.message)
    )


def _messages(record) -> list:
    return [f"{w.category.__name__}: {w.message}" for w in record]


@pytest.mark.parametrize("tight_layout", [False, True])
def test_fill_follows_layout_setting_without_colorbar(tight_layout):
    fig, ax = plt.subplots()
    default = _subplotpars(fig)
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=tight_layout)
    n_axes = len(fig.axes)

    with raise_on_warnings():
        td.fill(TRIANGLE)

    # カラーバーが増えない (no colorbar is added)
    assert len(fig.axes) == n_axes
    # 余白は三角図の設定に従う (the margins follow the diagram setting)
    assert (_subplotpars(fig) != default) is tight_layout


def test_fill_then_text_warn_about_layout_once_in_total():
    fig, ax = plt.subplots()
    default = _subplotpars(fig)
    # `tight_layout` は既定値を確かめるため省略する
    # (`tight_layout` is omitted on purpose: this checks the default)
    td = TernaryDiagram(MATERIALS, ax=ax)
    n_axes = len(fig.axes)

    with pytest.warns(FutureWarning, match=LAYOUT_WARNING_MATCH) as record:
        td.fill(TRIANGLE)

    assert len(record) == 1, _messages(record)
    assert _is_layout_future_warning(record[0])
    assert record[0].filename == __file__
    assert _subplotpars(fig) != default

    # 同じ三角図の text は警告を繰り返さない
    # (text on the same diagram does not repeat the warning)
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        td.text("Liquid", CENTER)

    assert record == [], _messages(record)
    assert len(fig.axes) == n_axes
