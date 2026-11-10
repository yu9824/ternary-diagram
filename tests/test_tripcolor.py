import numpy as np
import pytest
from matplotlib.collections import PolyCollection, TriMesh

from ternary_diagram.utils import check_2d_vector, three2two

# 三角形の 3 頂点と内部の 1 点 (the 3 vertices of the triangle and a point
# inside): the automatic triangulation gives 3 triangles
VECTOR = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1]]
Z = [1.0, 2.0, 3.0, 4.0]


@pytest.mark.parametrize(
    "shading, expected_type",
    [("flat", PolyCollection), ("gouraud", TriMesh)],
)
def test_tripcolor_returns_mesh_and_adds_one_collection(
    td, shading, expected_type
):
    n_collections = len(td.ax.collections)

    mesh = td.tripcolor(VECTOR, Z, shading=shading)

    assert isinstance(mesh, expected_type)
    assert len(td.ax.collections) == n_collections + 1
    assert td.ax.collections[-1] is mesh


def test_tripcolor_default_shading_is_flat(td):
    mesh = td.tripcolor(VECTOR, Z)

    assert isinstance(mesh, PolyCollection)
    assert len(mesh.get_paths()) == 3


def test_tripcolor_records_coordinates(td):
    td.tripcolor(VECTOR, Z)

    x, y = three2two(check_2d_vector(VECTOR))
    assert len(td.x_["tripcolor"]) == 1
    assert len(td.y_["tripcolor"]) == 1
    np.testing.assert_allclose(td.x_["tripcolor"][0], x)
    np.testing.assert_allclose(td.y_["tripcolor"][0], y)
