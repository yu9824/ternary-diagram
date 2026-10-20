import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from ternary_diagram import TernaryDiagram  # noqa: E402

VECTOR = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1], [2, 1, 1]]
Z = [0.0, 1.0, 2.0, 3.0, 4.0]


@pytest.fixture
def td():
    fig, ax = plt.subplots()
    yield TernaryDiagram(["A", "B", "C"], ax=ax)
    plt.close(fig)


@pytest.mark.parametrize("levels", [5, [0.0, 1.0, 2.0, 3.0, 4.0]])
@pytest.mark.parametrize("fill", [True, False])
def test_contour_user_levels(td, levels, fill):
    collection = td.contour(VECTOR, z=Z, levels=levels, fill=fill)

    if isinstance(levels, list):
        np.testing.assert_allclose(collection.levels, levels)
    else:
        assert len(collection.levels) <= levels + 2


@pytest.mark.parametrize("bound", [{"z_min": 0.0}, {"z_max": 4.0}])
def test_contour_levels_with_z_bounds(td, bound):
    with pytest.raises(ValueError, match="`levels`"):
        td.contour(VECTOR, z=Z, levels=5, **bound)


def test_scatter_vmin_vmax_alias(td):
    collection = td.scatter(VECTOR, z=Z, vmin=-1.0, vmax=10.0)

    assert collection.norm.vmin == -1.0
    assert collection.norm.vmax == 10.0


def test_scatter_z_min_z_max(td):
    collection = td.scatter(VECTOR, z=Z, z_min=-1.0, z_max=10.0)

    assert collection.norm.vmin == -1.0
    assert collection.norm.vmax == 10.0


@pytest.mark.parametrize(
    "kwargs",
    [{"z_min": 0.0, "vmin": 0.0}, {"z_max": 4.0, "vmax": 4.0}],
)
def test_scatter_alias_conflict(td, kwargs):
    with pytest.raises(ValueError, match="at the same time"):
        td.scatter(VECTOR, z=Z, **kwargs)


def test_scatter_c_with_z(td):
    with pytest.raises(ValueError, match="`c`"):
        td.scatter(VECTOR, z=Z, c="red")


def test_scatter_c_without_z(td):
    td.scatter(VECTOR, c="red")
