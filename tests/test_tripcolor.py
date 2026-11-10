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


# 三角形の 3 頂点と内部の 4 点 (the 3 vertices and 4 inner points, no
# symmetry so that the automatic triangulation is unique)
POINTS = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
    [3, 2, 1],
    [1, 3, 2],
    [2, 1, 4],
    [1, 1, 1],
]
POINTS_Z = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]


def _xy(vector):
    return three2two(check_2d_vector(vector))


def _point_indices(vertices, x, y):
    """Map each 2D vertex to the index of the composition at that place."""
    distances = np.hypot(
        vertices[:, [0]] - np.asarray(x)[np.newaxis, :],
        vertices[:, [1]] - np.asarray(y)[np.newaxis, :],
    )
    indices = distances.argmin(axis=1)
    np.testing.assert_allclose(distances.min(axis=1), 0.0, atol=1e-12)
    return indices


def _painted_triangles(mesh, x, y):
    """Indices of the 3 compositions of each painted triangle, in order.

    Both a PolyCollection (flat) and a TriMesh (gouraud) return one path per
    painted triangle from ``get_paths()``; masked triangles have no path.
    """
    return [
        tuple(_point_indices(path.vertices[:3], x, y))
        for path in mesh.get_paths()
    ]


def _area(x, y, triangles):
    """Sum of the areas of the triangles (shoelace formula)."""
    tri = np.asarray(triangles)
    x0, x1, x2 = (np.asarray(x)[tri[:, i]] for i in range(3))
    y0, y1, y2 = (np.asarray(y)[tri[:, i]] for i in range(3))
    return float(
        np.sum(np.abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2)
    )


def _as_set(triangles):
    return {frozenset(t) for t in triangles}


def test_tripcolor_flat_colors_are_mean_of_vertex_values(td):
    x, y = _xy(POINTS)
    z = np.asarray(POINTS_Z)

    mesh = td.tripcolor(POINTS, z)

    triangles = _painted_triangles(mesh, x, y)
    assert len(triangles) > 1
    expected = z[np.asarray(triangles)].mean(axis=1)
    np.testing.assert_allclose(mesh.get_array(), expected)
    # 平均であって頂点の値そのものではない (the mean, not a vertex value)
    assert not np.isin(mesh.get_array(), z).all()


def test_tripcolor_gouraud_colors_are_z(td):
    mesh = td.tripcolor(POINTS, POINTS_Z, shading="gouraud")

    np.testing.assert_allclose(mesh.get_array(), POINTS_Z)
    # 全点が三角形に使われている (every point is a vertex of a triangle)
    x, y = _xy(POINTS)
    used = set(np.ravel(_painted_triangles(mesh, x, y)).tolist())
    assert used == set(range(len(POINTS)))


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_tripcolor_paints_whole_diagram_from_its_vertices(td, shading):
    x, y = _xy(POINTS)

    mesh = td.tripcolor(POINTS, POINTS_Z, shading=shading)

    corner_x, corner_y = _xy([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    whole = _area(corner_x, corner_y, [[0, 1, 2]])
    assert whole == pytest.approx(np.sqrt(3) / 4)
    assert _area(x, y, _painted_triangles(mesh, x, y)) == pytest.approx(whole)


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_tripcolor_paints_only_convex_hull(td, shading):
    # 内側の小さな三角形の頂点と内部の点 (the vertices of a smaller inner
    # triangle and points inside it)
    vector = [
        [6, 2, 2],
        [2, 6, 2],
        [2, 2, 6],
        [4, 3, 3],
        [3, 4, 3],
        [3, 3, 4],
        [5, 3, 2],
    ]
    x, y = _xy(vector)

    mesh = td.tripcolor(vector, np.arange(len(vector)), shading=shading)

    inner = _area(x, y, [[0, 1, 2]])
    painted = _area(x, y, _painted_triangles(mesh, x, y))
    corner_x, corner_y = _xy([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    assert inner < _area(corner_x, corner_y, [[0, 1, 2]])
    assert painted == pytest.approx(inner)


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_tripcolor_uses_given_triangles(td, shading):
    x, y = _xy(VECTOR)

    mesh = td.tripcolor(VECTOR, Z, shading=shading, triangles=[[0, 1, 2]])

    assert _painted_triangles(mesh, x, y) == [(0, 1, 2)]


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_tripcolor_mask_reduces_painted_triangles(td, shading):
    x, y = _xy(VECTOR)
    all_triangles = _as_set(
        _painted_triangles(td.tripcolor(VECTOR, Z, shading=shading), x, y)
    )

    mesh = td.tripcolor(
        VECTOR,
        Z,
        shading=shading,
        mask=[True, False, False],
        colorbar=False,
    )

    painted = _as_set(_painted_triangles(mesh, x, y))
    assert len(all_triangles) == 3
    assert len(painted) == 2
    assert painted < all_triangles


@pytest.mark.parametrize(
    "vector, z, match",
    [
        (VECTOR, None, "`z` is required"),
        (VECTOR, Z[:-1], r"one value per composition \(4\), but got 3"),
        ([[1, 0, 0], [0, 1, 0]], [1.0, 2.0], "Cannot triangulate"),
        # 一直線上 (all on one straight line: an edge of the triangle)
        (
            [[1, 0, 0], [0, 1, 0], [1, 1, 0]],
            [1.0, 2.0, 3.0],
            "Cannot triangulate",
        ),
        # 正規化すると 2 種類 (only 2 distinct compositions after
        # normalization)
        (
            [[1, 0, 0], [2, 0, 0], [0, 1, 0]],
            [1.0, 2.0, 3.0],
            "Cannot triangulate",
        ),
    ],
    ids=["z-none", "z-length", "two-points", "collinear", "two-distinct"],
)
@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_tripcolor_invalid_input_adds_nothing(td, vector, z, match, shading):
    n_collections = len(td.ax.collections)
    n_axes = len(td.ax.figure.axes)

    with pytest.raises(ValueError, match=match):
        td.tripcolor(vector, z, shading=shading)

    assert len(td.ax.collections) == n_collections
    assert len(td.ax.figure.axes) == n_axes
    assert "tripcolor" not in td.x_


def test_tripcolor_warns_once_about_duplicated_compositions(td):
    # [2, 0, 0] は正規化すると [1, 0, 0] と同じ (the same composition as
    # [1, 0, 0] after normalization)
    vector = VECTOR + [[2, 0, 0]]
    z = Z + [5.0]

    with pytest.warns(
        UserWarning, match="1 composition point was not used"
    ) as record:
        mesh = td.tripcolor(vector, z)

    assert len(record) == 1
    assert record[0].filename == __file__
    assert "Aggregate" in str(record[0].message)
    # 1 点の値だけで描く (drawn with the value of one of them)
    assert len(mesh.get_paths()) == 3


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_tripcolor_skips_triangles_with_non_finite_value(td, shading, bad):
    x, y = _xy(POINTS)
    full = _as_set(
        _painted_triangles(
            td.tripcolor(POINTS, POINTS_Z, shading=shading), x, y
        )
    )
    # 上の頂点 (the top vertex) is used by some but not all triangles
    bad_index = 0
    z = np.array(POINTS_Z)
    z[bad_index] = bad

    mesh = td.tripcolor(POINTS, z, shading=shading, colorbar=False)

    painted = _as_set(_painted_triangles(mesh, x, y))
    expected = {t for t in full if bad_index not in t}
    assert 0 < len(expected) < len(full)
    assert painted == expected
    assert np.isfinite(np.asarray(mesh.get_array().compressed())).all()


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_tripcolor_masked_value_is_skipped_like_nan(td, shading):
    x, y = _xy(POINTS)
    z_nan = np.array(POINTS_Z)
    z_nan[0] = np.nan
    expected = _as_set(
        _painted_triangles(td.tripcolor(POINTS, z_nan, shading=shading), x, y)
    )
    # マスクした点の値 (999) では塗らない (the masked value 999 is not used)
    z_masked = np.ma.masked_array(
        [999.0, *POINTS_Z[1:]], mask=[True] + [False] * (len(POINTS) - 1)
    )

    mesh = td.tripcolor(POINTS, z_masked, shading=shading, colorbar=False)

    assert _as_set(_painted_triangles(mesh, x, y)) == expected
    assert 999.0 not in np.asarray(mesh.get_array().compressed())
    assert mesh.get_clim()[1] < 999.0


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_tripcolor_all_nan_raises_and_adds_nothing(td, shading):
    n_collections = len(td.ax.collections)

    with pytest.raises(ValueError, match="No triangle can be painted"):
        td.tripcolor(VECTOR, [np.nan] * len(VECTOR), shading=shading)

    assert len(td.ax.collections) == n_collections
