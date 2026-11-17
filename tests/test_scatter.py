from __future__ import annotations
from math import sqrt

import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PathCollection
from matplotlib.text import Annotation

from ternary_diagram import TernaryDiagram
from ternary_diagram.utils import check_2d_vector, three2two

ROOT3_OVER_2 = sqrt(3.0) / 2.0
VECTOR = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1], [2, 1, 1]]
Z = [0.0, 1.0, 2.0, 3.0, 4.0]


def _n_axes(td: TernaryDiagram) -> int:
    return len(td.fig.axes)


def test_returns_points_at_converted_positions(td):
    collection = td.scatter(VECTOR)

    assert isinstance(collection, PathCollection)
    np.testing.assert_allclose(
        collection.get_offsets(),
        np.column_stack(three2two(check_2d_vector(VECTOR))),
    )


def test_vector_does_not_need_to_sum_to_one(td):
    raw = td.scatter([[1, 1, 2]])
    normalized = td.scatter([[0.25, 0.25, 0.5]])

    np.testing.assert_allclose(raw.get_offsets(), normalized.get_offsets())


def test_without_z_has_no_colorbar(td):
    td.scatter(VECTOR)

    assert _n_axes(td) == 1


def test_with_z_colors_points_and_adds_colorbar(td):
    collection = td.scatter(VECTOR, z=Z)

    np.testing.assert_allclose(collection.get_array(), Z)
    assert collection.cmap.name == "rainbow"
    assert _n_axes(td) == 2


def test_colorbar_false(td):
    td.scatter(VECTOR, z=Z, colorbar=False)

    assert _n_axes(td) == 1


def test_single_point_with_z(td):
    collection = td.scatter([[1, 1, 1]], z=[1.0])

    np.testing.assert_allclose(collection.get_array(), [1.0])


def test_default_zorder_can_be_overridden(td):
    assert td.scatter(VECTOR).get_zorder() == 3
    assert td.scatter(VECTOR, zorder=10).get_zorder() == 10


def test_cmap_can_be_overridden(td):
    assert td.scatter(VECTOR, z=Z, cmap="viridis").cmap.name == "viridis"


def test_kwargs_are_passed_to_matplotlib(td):
    collection = td.scatter(VECTOR, s=50, label="samples")

    np.testing.assert_allclose(collection.get_sizes(), [50])
    assert collection.get_label() == "samples"


def test_z_min_z_max(td):
    collection = td.scatter(VECTOR, z=Z, z_min=-1.0, z_max=10.0)

    assert collection.norm.vmin == -1.0
    assert collection.norm.vmax == 10.0


def test_vmin_vmax_are_aliases(td):
    collection = td.scatter(VECTOR, z=Z, vmin=-1.0, vmax=10.0)

    assert collection.norm.vmin == -1.0
    assert collection.norm.vmax == 10.0


@pytest.mark.parametrize(
    "kwargs",
    [{"z_min": 0.0, "vmin": 0.0}, {"z_max": 4.0, "vmax": 4.0}],
)
def test_alias_conflict(td, kwargs):
    with pytest.raises(ValueError, match="at the same time"):
        td.scatter(VECTOR, z=Z, **kwargs)


def test_c_with_z(td):
    with pytest.raises(ValueError, match="`c`"):
        td.scatter(VECTOR, z=Z, c="red")


def test_c_without_z(td):
    td.scatter(VECTOR, c="red")


def test_annotations(td):
    td.scatter([[1, 0, 0], [0, 1, 0]], annotations=["Li2O", "A"])

    annotations = [t for t in td.ax.texts if isinstance(t, Annotation)]
    assert [a.get_text() for a in annotations] == ["Li$_{2}$O", "A"]
    assert annotations[0].xy == pytest.approx((0.5, ROOT3_OVER_2))
    assert annotations[0].xyann == pytest.approx((0.52, ROOT3_OVER_2 + 0.02))


def test_annotations_length_mismatch(td):
    with pytest.raises(ValueError, match="annotations"):
        td.scatter([[1, 0, 0], [0, 1, 0]], annotations=["a"])


def test_invalid_vector_shape(td):
    with pytest.raises(ValueError, match="shape"):
        td.scatter([[1, 2]])


def test_example_scatter(df_scatter: pd.DataFrame):
    td = TernaryDiagram(materials=df_scatter.columns[:3], tight_layout=True)

    collection = td.scatter(df_scatter.iloc[:, :3], df_scatter.loc[:, "z"])

    assert len(collection.get_offsets()) == len(df_scatter)


def test_example_mono_scatter(df_mono_scatter: pd.DataFrame):
    td = TernaryDiagram(materials=df_mono_scatter.columns, tight_layout=True)

    collection = td.scatter(df_mono_scatter)

    assert len(collection.get_offsets()) == len(df_mono_scatter)
