import numpy as np
import pandas as pd
import pytest
from matplotlib.contour import ContourSet

from ternary_diagram import TernaryDiagram

VECTOR = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
    [1, 1, 1],
    [2, 1, 1],
    [1, 2, 1],
    [1, 1, 2],
]
Z = np.linspace(0.0, 6.0, len(VECTOR))


def _n_axes(td: TernaryDiagram) -> int:
    return len(td.fig.axes)


@pytest.mark.parametrize("fill", [True, False])
def test_fill(td, fill):
    collection = td.contour(VECTOR, z=Z, fill=fill)

    assert isinstance(collection, ContourSet)
    assert collection.filled is fill


def test_default_levels_span_z(td):
    levels = np.asarray(td.contour(VECTOR, z=Z).levels)

    assert len(levels) == 101
    assert levels[0] == pytest.approx(Z.min())
    assert levels[-1] == pytest.approx(Z.max())


def test_z_min_z_max_set_level_range(td):
    levels = np.asarray(td.contour(VECTOR, z=Z, z_min=-1.0, z_max=10.0).levels)

    assert levels[0] == pytest.approx(-1.0)
    assert levels[-1] == pytest.approx(10.0)


def test_defaults_can_be_overridden(td):
    default = td.contour(VECTOR, z=Z)
    custom = td.contour(VECTOR, z=Z, cmap="viridis", zorder=5)

    assert default.cmap.name == "rainbow"
    assert default.get_zorder() == 0
    assert custom.cmap.name == "viridis"
    assert custom.get_zorder() == 5


def test_adds_colorbar(td):
    td.contour(VECTOR, z=Z)

    assert _n_axes(td) == 2


def test_flag_cbar_false(td):
    td.contour(VECTOR, z=Z, flag_cbar=False)

    assert _n_axes(td) == 1


@pytest.mark.parametrize(
    "value",
    # 1.7 and 0.1 make `np.linspace(v, v, 101).std()` a non-zero rounding
    # error, which used to slip through the constant-z check.
    [0.0, 0.1, 0.3, 1.7, 3.0, -2.5],
)
@pytest.mark.parametrize("fill", [True, False])
def test_constant_z(td, value, fill):
    collection = td.contour(VECTOR, z=np.full(len(VECTOR), value), fill=fill)

    levels = np.asarray(collection.levels)
    assert np.all(np.diff(levels) > 0)
    assert levels[0] <= value <= levels[-1]


def test_nearly_constant_z(td):
    z = np.full(len(VECTOR), 1.7)
    z[0] = np.nextafter(1.7, 2.0)

    collection = td.contour(VECTOR, z=z)

    assert np.all(np.diff(np.asarray(collection.levels)) > 0)


def test_same_z_min_and_z_max(td):
    collection = td.contour(VECTOR, z=Z, z_min=1.7, z_max=1.7)

    assert np.all(np.diff(np.asarray(collection.levels)) > 0)


@pytest.mark.parametrize("levels", [5, [0.0, 1.0, 2.0, 3.0, 4.0]])
@pytest.mark.parametrize("fill", [True, False])
def test_user_levels(td, levels, fill):
    collection = td.contour(VECTOR, z=Z, levels=levels, fill=fill)

    if isinstance(levels, list):
        np.testing.assert_allclose(collection.levels, levels)
    else:
        assert len(collection.levels) <= levels + 2


@pytest.mark.parametrize("bound", [{"z_min": 0.0}, {"z_max": 4.0}])
def test_user_levels_with_z_bounds(td, bound):
    with pytest.raises(ValueError, match="`levels`"):
        td.contour(VECTOR, z=Z, levels=5, **bound)


def test_without_z(td):
    with pytest.raises(ValueError, match="`z` is required"):
        td.contour(VECTOR)


def test_example_contour(df_contour: pd.DataFrame):
    td = TernaryDiagram(materials=df_contour.columns[:3])
    z = df_contour.loc[:, "z"]

    collection = td.contour(df_contour.iloc[:, :3], z)

    assert collection.levels[0] == pytest.approx(z.min())
    assert collection.levels[-1] == pytest.approx(z.max())
