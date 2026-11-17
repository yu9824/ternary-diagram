"""Behavior shared by `TernaryDiagram.tripcolor` and `TernaryDiagram.heatmapf`.

Each test is parametrized over the two methods, which paint triangles with
the same procedure: the color range and its aliases, the default colormap,
the colorbar, the layout, the stacking order, the keyword arguments and the
recorded coordinates. Tests that check a layout create the diagram on the
spot; the others use the ``td`` fixture (``tight_layout=True``).
"""

from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.colorbar import Colorbar
from matplotlib.colors import LogNorm

from ternary_diagram import TernaryDiagram, _post_draw
from ternary_diagram.utils import check_2d_vector, three2two

MATERIALS = ("Li2O", "La2O3", "TiO2")
METHODS = ["tripcolor", "heatmapf"]
SHADINGS = ["flat", "gouraud"]
SUBPLOT_PARAMS = ("left", "bottom", "right", "top", "wspace", "hspace")

# 三角形の 3 頂点と内部の 1 点 (the 3 vertices and a point inside): the
# automatic triangulation gives 3 triangles.
VECTOR = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1]]
Z = [1.0, 2.0, 3.0, 4.0]
# A small lattice keeps the tests fast; the default is tested elsewhere.
SCALE = 6

requires_layout_engine = pytest.mark.skipif(
    not _post_draw._HAS_LAYOUT_ENGINE,
    reason="Figure.get_layout_engine needs matplotlib >= 3.6",
)


def _positive(a, b, c):
    """A function of the composition with values from 1 to 3."""
    return 1.0 + b + 2.0 * c


def _paint(td, method, *, z=Z, vector=VECTOR, func=_positive, **kwargs):
    """Paint with `method` of `td`.

    Returns the returned object, the values that determine the colors (`z`
    for ``tripcolor``, the return value of the function for ``heatmapf``)
    and the compositions at which the values are given.
    """
    if method == "tripcolor":
        mesh = td.tripcolor(vector, z, **kwargs)
        return mesh, np.asarray(z, dtype=float), check_2d_vector(vector)

    calls = []

    def recording(a, b, c):
        value = func(a, b, c)
        calls.append((np.column_stack((a, b, c)), np.asarray(value, float)))
        return value

    kwargs.setdefault("scale", SCALE)
    mesh = td.heatmapf(recording, **kwargs)
    assert len(calls) == 1
    points, values = calls[0]
    return mesh, values, points


def _snapshot(td):
    """What a failed call must leave unchanged."""
    return (
        len(td.ax.get_children()),
        len(td.fig.axes),
        {key: len(value) for key, value in td.x_.items()},
    )


def _subplotpars(fig) -> dict:
    return {name: getattr(fig.subplotpars, name) for name in SUBPLOT_PARAMS}


def _messages(record) -> list:
    return [f"{w.category.__name__}: {w.message}" for w in record]


# --- color range (z_min / z_max and their aliases) --------------------------


@pytest.mark.parametrize("shading", SHADINGS)
@pytest.mark.parametrize("method", METHODS)
def test_z_min_z_max_and_vmin_vmax_give_the_same_range(td, method, shading):
    by_name, _, _ = _paint(
        td, method, z_min=1.5, z_max=2.5, shading=shading, colorbar=False
    )
    by_alias, _, _ = _paint(
        td, method, vmin=1.5, vmax=2.5, shading=shading, colorbar=False
    )

    assert (by_name.norm.vmin, by_name.norm.vmax) == (1.5, 2.5)
    assert (by_alias.norm.vmin, by_alias.norm.vmax) == (1.5, 2.5)


@pytest.mark.parametrize(
    ("name", "alias"), [("z_min", "vmin"), ("z_max", "vmax")]
)
@pytest.mark.parametrize("method", METHODS)
def test_name_and_alias_together_raise_the_message_of_scatter(
    td, method, name, alias
):
    with pytest.raises(ValueError) as scatter_error:
        td.scatter(VECTOR, z=Z, **{name: 2.0, alias: 2.0})
    before = _snapshot(td)

    with pytest.raises(ValueError) as error:
        _paint(td, method, **{name: 2.0, alias: 2.0})

    assert str(error.value) == str(scatter_error.value)
    assert f"`{name}`" in str(error.value)
    assert f"`{alias}`" in str(error.value)
    assert _snapshot(td) == before


def _with_non_finite(method, bad):
    """Data with one non-finite value: `bad`."""
    if method == "tripcolor":
        # an inner point with the non-finite value, the others as `Z`
        return {
            "vector": VECTOR + [[2, 1, 1]],
            "z": Z + [bad],
        }

    def func(a, b, c):
        return np.where(a > 0.7, bad, _positive(a, b, c))

    return {"func": func}


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("shading", SHADINGS)
@pytest.mark.parametrize("method", METHODS)
def test_default_range_is_min_and_max_of_finite_values(
    td, method, shading, bad
):
    mesh, values, _ = _paint(
        td,
        method,
        shading=shading,
        colorbar=False,
        **_with_non_finite(method, bad),
    )

    assert not np.isfinite(values).all()  # the data has a non-finite value
    finite = values[np.isfinite(values)]
    assert np.isfinite([mesh.norm.vmin, mesh.norm.vmax]).all()
    assert mesh.norm.vmin == finite.min()
    assert mesh.norm.vmax == finite.max()


def test_tripcolor_flat_default_range_is_wider_than_triangle_means(td):
    mesh = td.tripcolor(VECTOR, Z, shading="flat", colorbar=False)

    means = mesh.get_array()
    # The colors are the means of the 3 vertices, but the range is the one
    # of `z`, so that it matches `scatter` with the same `z`.
    assert (mesh.norm.vmin, mesh.norm.vmax) == (min(Z), max(Z))
    assert mesh.norm.vmin < means.min()
    assert means.max() < mesh.norm.vmax


@pytest.mark.parametrize("alias", [False, True])
@pytest.mark.parametrize("method", METHODS)
def test_only_z_min_keeps_the_default_maximum(td, method, alias):
    key = "vmin" if alias else "z_min"

    mesh, values, _ = _paint(td, method, colorbar=False, **{key: 1.5})

    assert (mesh.norm.vmin, mesh.norm.vmax) == (1.5, values.max())


@pytest.mark.parametrize("alias", [False, True])
@pytest.mark.parametrize("method", METHODS)
def test_only_z_max_keeps_the_default_minimum(td, method, alias):
    key = "vmax" if alias else "z_max"

    mesh, values, _ = _paint(td, method, colorbar=False, **{key: 2.5})

    assert (mesh.norm.vmin, mesh.norm.vmax) == (values.min(), 2.5)


@pytest.mark.parametrize("shading", SHADINGS)
@pytest.mark.parametrize("method", METHODS)
def test_norm_is_used_without_the_default_range(td, method, shading):
    norm = LogNorm()

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mesh, _, _ = _paint(td, method, norm=norm, shading=shading)

    assert mesh.norm is norm
    # matplotlib scales the norm to the painted colors, which are the means
    # of the vertices for `tripcolor` with flat shading, not the range of
    # `z`.
    colors = mesh.get_array()
    assert (norm.vmin, norm.vmax) == (colors.min(), colors.max())


@pytest.mark.parametrize("shading", SHADINGS)
@pytest.mark.parametrize("method", METHODS)
def test_range_of_the_given_norm_is_kept(td, method, shading):
    # 範囲を持つ norm は既定の範囲で上書きされない (the range of a norm that
    # has one is not replaced by the default range)
    norm = LogNorm(vmin=0.5, vmax=10.0)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mesh, _, _ = _paint(td, method, norm=norm, shading=shading)

    assert mesh.norm is norm
    assert (norm.vmin, norm.vmax) == (0.5, 10.0)


@pytest.mark.parametrize("method", METHODS)
def test_default_colormap_is_the_one_of_scatter_and_contour(td, method):
    scatter = td.scatter(VECTOR, z=Z, colorbar=False)
    contour = td.contour(VECTOR, z=Z, colorbar=False)

    mesh, _, _ = _paint(td, method, colorbar=False)

    assert mesh.get_cmap().name == scatter.get_cmap().name
    assert mesh.get_cmap().name == contour.get_cmap().name


@pytest.mark.parametrize("method", METHODS)
def test_given_colormap_is_used(td, method):
    mesh, _, _ = _paint(td, method, cmap="viridis", colorbar=False)

    assert mesh.get_cmap().name == "viridis"


# --- colorbar ---------------------------------------------------------------


@pytest.mark.parametrize("shading", SHADINGS)
@pytest.mark.parametrize("method", METHODS)
def test_default_adds_one_colorbar_referable_from_the_result(
    td, method, shading
):
    axes_before = list(td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mesh, _, _ = _paint(td, method, shading=shading)

    assert isinstance(mesh.colorbar, Colorbar)
    assert mesh.colorbar.mappable is mesh
    added_axes = [a for a in td.fig.axes if a not in axes_before]
    assert added_axes == [mesh.colorbar.ax]


@pytest.mark.parametrize("method", METHODS)
def test_second_default_colorbar_is_added_with_one_future_warning(td, method):
    _paint(td, method)
    n_axes = len(td.fig.axes)

    # The wording belongs to plot-side-effects: only stable fragments.
    with pytest.warns(FutureWarning, match="colorbar") as record:
        mesh, _, _ = _paint(td, method)

    assert len(td.fig.axes) == n_axes + 1
    assert isinstance(mesh.colorbar, Colorbar)
    assert len(record) == 1, _messages(record)
    assert method in str(record[0].message)
    assert record[0].filename == __file__


@pytest.mark.parametrize("has_colorbar", [False, True])
@pytest.mark.parametrize(("colorbar", "added"), [(True, 1), (False, 0)])
@pytest.mark.parametrize("method", METHODS)
def test_explicit_colorbar_adds_or_not_without_warnings(
    td, method, colorbar, added, has_colorbar
):
    if has_colorbar:
        td.contour(VECTOR, z=Z)
    n_axes = len(td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mesh, _, _ = _paint(td, method, colorbar=colorbar)

    assert len(td.fig.axes) == n_axes + added
    assert (mesh.colorbar is not None) is bool(added)


@pytest.mark.parametrize("value", [1, 0, "yes"])
@pytest.mark.parametrize("method", METHODS)
def test_non_bool_colorbar_raises_the_type_error_of_scatter(td, method, value):
    with pytest.raises(TypeError) as scatter_error:
        td.scatter(VECTOR, z=Z, colorbar=value)
    before = _snapshot(td)

    with pytest.raises(TypeError) as error:
        _paint(td, method, colorbar=value)

    assert str(error.value) == str(scatter_error.value)
    assert _snapshot(td) == before


@pytest.mark.parametrize("value", [False, True])
@pytest.mark.parametrize("method", METHODS)
def test_flag_cbar_raises_type_error_pointing_to_colorbar(td, method, value):
    before = _snapshot(td)

    with pytest.raises(TypeError, match="`colorbar`") as error:
        _paint(td, method, flag_cbar=value)

    assert "`flag_cbar`" in str(error.value)
    assert _snapshot(td) == before


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"z_min": 1.5, "z_max": 2.5, "cmap": "viridis"}],
    ids=["default", "given"],
)
@pytest.mark.parametrize("method", METHODS)
def test_colorbar_of_the_result_has_its_range_and_colormap(td, method, kwargs):
    mesh, _, _ = _paint(td, method, colorbar=False, **kwargs)

    cbar = td.colorbar(mesh)

    assert isinstance(cbar, Colorbar)
    assert cbar.mappable is mesh
    assert (cbar.norm.vmin, cbar.norm.vmax) == (
        mesh.norm.vmin,
        mesh.norm.vmax,
    )
    assert cbar.cmap.name == mesh.get_cmap().name


# --- layout -----------------------------------------------------------------


@requires_layout_engine
@pytest.mark.parametrize("method", METHODS)
def test_tight_layout_false_leaves_layout_untouched(method):
    fig, ax = plt.subplots()
    default = _subplotpars(fig)
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=False)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _paint(td, method)

    assert _subplotpars(fig) == default
    assert fig.get_layout_engine() is None


@requires_layout_engine
@pytest.mark.parametrize("tight_layout", [None, True, False])
@pytest.mark.parametrize("method", METHODS)
def test_constrained_layout_engine_is_kept_without_warnings(
    method, tight_layout
):
    from matplotlib.layout_engine import ConstrainedLayoutEngine

    fig, ax = plt.subplots(layout="constrained")
    engine = fig.get_layout_engine()
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=tight_layout)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        mesh, _, _ = _paint(td, method)

    assert isinstance(engine, ConstrainedLayoutEngine)
    assert fig.get_layout_engine() is engine
    assert isinstance(mesh.colorbar, Colorbar)
    assert _messages(record) == []


# --- stacking order ---------------------------------------------------------


@pytest.mark.parametrize("shading", SHADINGS)
@pytest.mark.parametrize("method", METHODS)
def test_heatmap_drawn_last_is_behind_everything(td, method, shading):
    skeleton_lines = list(td.ax.lines)
    scatter = td.scatter(VECTOR, z=Z, colorbar=False)
    contour = td.contour(VECTOR, z=Z, colorbar=False)
    td.plot(VECTOR[:2])
    lines = [line for line in td.ax.lines if line not in skeleton_lines]
    assert skeleton_lines and lines

    mesh, _, _ = _paint(td, method, shading=shading, colorbar=False)

    zorder = mesh.get_zorder()
    assert all(zorder < line.get_zorder() for line in skeleton_lines)
    assert all(zorder < line.get_zorder() for line in lines)
    assert zorder < contour.get_zorder()
    assert zorder < scatter.get_zorder()
    others = [a for a in td.ax.get_children() if a is not mesh]
    assert zorder < min(a.get_zorder() for a in others if a.get_visible())


@pytest.mark.parametrize("method", METHODS)
def test_given_zorder_is_used(td, method):
    mesh, _, _ = _paint(td, method, zorder=5, colorbar=False)

    assert mesh.get_zorder() == 5


# --- keyword arguments ------------------------------------------------------


@pytest.mark.parametrize("shading", SHADINGS)
@pytest.mark.parametrize("method", METHODS)
def test_alpha_and_edgecolors_reach_the_result(td, method, shading):
    default, _, _ = _paint(td, method, shading=shading, colorbar=False)
    mesh, _, _ = _paint(
        td,
        method,
        shading=shading,
        alpha=0.5,
        edgecolors="face",
        colorbar=False,
    )

    assert default.get_alpha() != 0.5  # matplotlib passes 1.0 by default
    assert mesh.get_alpha() == 0.5
    # matplotlib draws no edges by default, and the edges in the colors of
    # the faces with "face".
    assert len(default.get_edgecolor()) == 0
    assert len(mesh.get_edgecolor()) > 0
    np.testing.assert_array_equal(mesh.get_edgecolor(), mesh.get_facecolor())


@pytest.mark.parametrize("shading", ["smooth", "Flat", None])
@pytest.mark.parametrize("method", METHODS)
def test_invalid_shading_raises_value_error(td, method, shading):
    before = _snapshot(td)

    with pytest.raises(ValueError, match="'flat' or 'gouraud'"):
        _paint(td, method, shading=shading)

    assert _snapshot(td) == before


@pytest.mark.parametrize("name", ["c", "facecolors"])
@pytest.mark.parametrize("method", METHODS)
def test_conflicting_color_kwargs_raise_value_error(td, method, name):
    before = _snapshot(td)

    with pytest.raises(ValueError, match=f"`{name}` cannot be used"):
        _paint(td, method, **{name: "red"})

    assert _snapshot(td) == before


# --- recorded coordinates and the skeleton ----------------------------------


@pytest.mark.parametrize("shading", SHADINGS)
@pytest.mark.parametrize("method", METHODS)
def test_coordinates_are_recorded_once_per_draw_under_the_name(
    td, method, shading
):
    td.scatter(VECTOR)

    _, _, points = _paint(td, method, shading=shading, colorbar=False)

    assert set(td.x_) == {"scatter", method}
    assert set(td.y_) == {"scatter", method}
    assert len(td.x_[method]) == len(td.y_[method]) == 1
    x, y = three2two(points)
    np.testing.assert_allclose(td.x_[method][0], x)
    np.testing.assert_allclose(td.y_[method][0], y)

    _paint(td, method, shading=shading, colorbar=False)

    assert len(td.x_[method]) == len(td.y_[method]) == 2
    assert len(td.x_["scatter"]) == len(td.y_["scatter"]) == 1


@pytest.mark.parametrize("shading", SHADINGS)
@pytest.mark.parametrize("method", METHODS)
def test_heatmap_leaves_the_skeleton_lines_and_texts(td, method, shading):
    lines = list(td.ax.lines)
    texts = list(td.ax.texts)
    assert lines and texts

    _paint(td, method, shading=shading)

    assert td.ax.lines[:] == lines
    assert td.ax.texts[:] == texts
