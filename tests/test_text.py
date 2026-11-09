from math import sqrt

import matplotlib.text
import numpy as np
import pytest
from matplotlib.colors import to_rgba

from ternary_diagram import _api

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
