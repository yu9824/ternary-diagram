from math import sqrt

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from ternary_diagram.utils import (
    check_1d_vector,
    check_2d_vector,
    check_ax,
    get_label,
    three2two,
)

ROOT3_OVER_2 = sqrt(3.0) / 2.0


@pytest.mark.parametrize(
    "compound_name, expected",
    [
        ("Li2O", "Li$_{2}$O"),
        ("La2O3", "La$_{2}$O$_{3}$"),
        ("(LiLa)0.5TiO3", "(LiLa)$_{0.5}$TiO$_{3}$"),
        ("Li0.33La0.55TiO3", "Li$_{0.33}$La$_{0.55}$TiO$_{3}$"),
        ("Ca10", "Ca$_{10}$"),
        ("Li", "Li"),
        ("", ""),
    ],
)
def test_get_label(compound_name, expected):
    assert get_label(compound_name) == expected


@pytest.mark.parametrize("compound_name", [1, None, ["Li2O"]])
def test_get_label_not_str(compound_name):
    with pytest.raises(ValueError, match="must be string"):
        get_label(compound_name)


@pytest.mark.parametrize(
    "vector, expected",
    [
        ([1, 0, 0], (0.5, ROOT3_OVER_2)),  # top
        ([0, 1, 0], (0.0, 0.0)),  # bottom left
        ([0, 0, 1], (1.0, 0.0)),  # bottom right
        ([0, 0.5, 0.5], (0.5, 0.0)),  # middle of the bottom edge
        ([1 / 3, 1 / 3, 1 / 3], (0.5, ROOT3_OVER_2 / 3)),  # centroid
    ],
)
def test_three2two(vector, expected):
    x, y = three2two(np.array([vector]))

    assert (x[0], y[0]) == pytest.approx(expected)


def test_three2two_shape():
    x, y = three2two(np.full((5, 3), 1 / 3))

    assert x.shape == y.shape == (5,)


def test_check_2d_vector_normalizes_each_row():
    arr = check_2d_vector([[1, 1, 2], [0, 0, 5]])

    np.testing.assert_allclose(arr, [[0.25, 0.25, 0.5], [0.0, 0.0, 1.0]])


def test_check_2d_vector_without_scale():
    arr = check_2d_vector([[1, 1, 2]], scale=False)

    assert isinstance(arr, np.ndarray)
    np.testing.assert_array_equal(arr, [[1, 1, 2]])


def test_check_2d_vector_accepts_dataframe():
    df = pd.DataFrame({"A": [1, 0], "B": [1, 0], "C": [2, 1]})

    np.testing.assert_allclose(
        check_2d_vector(df), [[0.25, 0.25, 0.5], [0.0, 0.0, 1.0]]
    )


@pytest.mark.parametrize(
    "vector",
    [[1, 2, 3], [[1, 2]], [[1, 2, 3, 4]], [[[1, 2, 3]] * 3]],
)
def test_check_2d_vector_invalid_shape(vector):
    with pytest.raises(ValueError, match=r"shape must be \(n, 3\)"):
        check_2d_vector(vector)


@pytest.mark.parametrize(
    "vector, scale, expected",
    [
        ([1, 2, 3], False, [[1, 2, 3]]),
        ([2, 2, 4], True, [[0.25, 0.25, 0.5]]),
        ([[1, 2, 3]], False, [[1, 2, 3]]),
    ],
)
def test_check_1d_vector(vector, scale, expected):
    np.testing.assert_allclose(check_1d_vector(vector, scale=scale), expected)


@pytest.mark.parametrize("vector", [[1, 2], [1, 2, 3, 4]])
def test_check_1d_vector_invalid_length(vector):
    with pytest.raises(ValueError, match="length must be 3"):
        check_1d_vector(vector)


def test_check_ax_none_returns_current_axes(ax):
    assert check_ax(None) is ax
    assert plt.gca() is ax


def test_check_ax_returns_given_axes(ax):
    _, other = plt.subplots()

    assert check_ax(ax) is ax
    assert check_ax(other) is other


@pytest.mark.parametrize("invalid", ["ax", 1, plt.figure])
def test_check_ax_invalid(invalid):
    with pytest.raises(TypeError, match="`ax`"):
        check_ax(invalid)
