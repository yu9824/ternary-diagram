from math import sqrt

import numpy as np
import pytest
from matplotlib.lines import Line2D

ROOT3_OVER_2 = sqrt(3.0) / 2.0


@pytest.mark.parametrize(
    "vector",
    [[[1, 0, 0], [0, 0, 1]], [[2, 0, 0], [0, 0, 4]]],
)
def test_plot_tie_line(td, vector):
    lines = td.plot(vector)

    assert isinstance(lines, list)
    assert len(lines) == 1
    assert isinstance(lines[0], Line2D)
    x, y = lines[0].get_data()
    np.testing.assert_allclose(x, [0.5, 1.0])
    np.testing.assert_allclose(y, [ROOT3_OVER_2, 0.0])


def test_default_zorder_can_be_overridden(td):
    vector = [[1, 0, 0], [0, 0, 1]]

    assert td.plot(vector)[0].get_zorder() == 2
    assert td.plot(vector, zorder=10)[0].get_zorder() == 10


def test_kwargs_are_passed_to_matplotlib(td):
    (line,) = td.plot([[1, 0, 0], [0, 0, 1]], color="black", lw=3, ls="--")

    assert line.get_color() == "black"
    assert line.get_linewidth() == 3
    assert line.get_linestyle() == "--"


def test_invalid_vector_shape(td):
    with pytest.raises(ValueError, match="shape"):
        td.plot([[1, 2], [3, 4]])
