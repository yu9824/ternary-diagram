import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from ternary_diagram import TernaryDiagram  # noqa: E402

VECTOR = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
    [1, 1, 1],
    [2, 1, 1],
    [1, 2, 1],
    [1, 1, 2],
]


@pytest.mark.parametrize(
    "value",
    # 1.7 and 0.1 make `np.linspace(v, v, 101).std()` a non-zero rounding
    # error, which used to slip through the constant-z check.
    [0.0, 0.1, 0.3, 1.7, 3.0, -2.5],
)
@pytest.mark.parametrize("fill", [True, False])
def test_contour_constant_z(value, fill):
    fig, ax = plt.subplots()
    td = TernaryDiagram(["A", "B", "C"], ax=ax)
    z = np.full(len(VECTOR), value)

    collection = td.contour(VECTOR, z=z, fill=fill)

    levels = np.asarray(collection.levels)
    assert np.all(np.diff(levels) > 0)
    assert levels[0] <= value <= levels[-1]
    plt.close(fig)


def test_contour_nearly_constant_z():
    fig, ax = plt.subplots()
    td = TernaryDiagram(["A", "B", "C"], ax=ax)
    z = np.full(len(VECTOR), 1.7)
    z[0] = np.nextafter(1.7, 2.0)

    collection = td.contour(VECTOR, z=z)

    assert np.all(np.diff(np.asarray(collection.levels)) > 0)
    plt.close(fig)


def test_contour_same_z_min_and_z_max():
    fig, ax = plt.subplots()
    td = TernaryDiagram(["A", "B", "C"], ax=ax)
    z = np.linspace(0.0, 1.0, len(VECTOR))

    collection = td.contour(VECTOR, z=z, z_min=1.7, z_max=1.7)

    assert np.all(np.diff(np.asarray(collection.levels)) > 0)
    plt.close(fig)
