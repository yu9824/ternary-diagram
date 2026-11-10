import numpy as np
import pytest
from matplotlib.collections import PolyCollection, TriMesh

from ternary_diagram.utils import get_triangular_lattice, three2two


def _top_component(a, b, c):
    return a


def test_heatmapf_default_returns_poly_collection(td):
    n_collections = len(td.ax.collections)

    mesh = td.heatmapf(_top_component)

    # 既定は flat、scale=50 (default: flat with scale=50 -> 50**2 triangles)
    assert isinstance(mesh, PolyCollection)
    assert len(mesh.get_paths()) == 2500
    assert len(td.ax.collections) == n_collections + 1
    assert td.ax.collections[-1] is mesh


def test_heatmapf_gouraud_returns_tri_mesh(td):
    n_collections = len(td.ax.collections)

    mesh = td.heatmapf(_top_component, shading="gouraud")

    assert isinstance(mesh, TriMesh)
    assert len(td.ax.collections) == n_collections + 1
    assert td.ax.collections[-1] is mesh


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_calls_function_once(td, shading):
    calls = []

    def func(a, b, c):
        calls.append((a, b, c))
        return a

    td.heatmapf(func, scale=4, shading=shading)

    assert len(calls) == 1


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_records_evaluation_points(td, shading):
    scale = 4
    vertices, triangles = get_triangular_lattice(scale)
    # flat は小三角形の重心、gouraud は格子点 (flat: centroids of the small
    # triangles, gouraud: lattice points)
    points = (
        vertices[triangles].mean(axis=1) if shading == "flat" else vertices
    )

    td.heatmapf(_top_component, scale=scale, shading=shading)

    x, y = three2two(points)
    assert len(td.x_["heatmapf"]) == 1
    assert len(td.y_["heatmapf"]) == 1
    np.testing.assert_allclose(td.x_["heatmapf"][0], x)
    np.testing.assert_allclose(td.y_["heatmapf"][0], y)
