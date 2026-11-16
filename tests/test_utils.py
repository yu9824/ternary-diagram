import re
from fractions import Fraction
from math import sqrt

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from _skeleton_expected import (
    expected_grid_lines,
    expected_tick_label_texts,
    segment_key,
)

from ternary_diagram.utils import (
    check_1d_vector,
    check_2d_vector,
    check_ax,
    check_bool,
    check_optional_bool,
    get_axis_label_position,
    get_edge_points,
    get_grid_segments,
    get_label,
    get_tick_formatter,
    get_tick_values,
    get_triangular_lattice,
    is_chemical_formula,
    three2two,
    to_latex_notation,
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
    "word",
    [
        "Li2O",
        "La2O3",
        "(LiLa)0.5TiO3",
        "Li0.33La0.55TiO3",
        "Li7La3Zr2O12",
        "(Li2O)",
        "Ca(OH)2",
        "AB2",
        "A",
        "LiF",
    ],
)
def test_is_chemical_formula(word):
    assert is_chemical_formula(word) is True


@pytest.mark.parametrize(
    "word",
    [
        "",
        "Sample",
        "sample1",
        "1",
        "2Li",
        "Run-3",
        "No.2",
        "x=0.5",
        "Li2O,",
        "(Li",
        "Li)",
        ")Li(",
        "Li)(O",
        "α",
        "$Li_2$",
        "Li2.",
    ],
)
def test_is_chemical_formula_rejects(word):
    assert is_chemical_formula(word) is False


@pytest.mark.parametrize("word", [1, None, b"Li2O", ["Li2O"]])
def test_is_chemical_formula_not_str(word):
    with pytest.raises(TypeError, match="`word` must be a str"):
        is_chemical_formula(word)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Li2O", "Li$_{2}$O"),
        ("(LiLa)0.5TiO3", "(LiLa)$_{0.5}$TiO$_{3}$"),
        ("LiF + Li2O", "LiF + Li$_{2}$O"),
        ("Li2O  La2O3", "Li$_{2}$O  La$_{2}$O$_{3}$"),
        ("Li2O\tLa2O3\n", "Li$_{2}$O\tLa$_{2}$O$_{3}$\n"),
        (" Li2O ", " Li$_{2}$O "),
        ("Sample 1", "Sample 1"),
        ("Run-3", "Run-3"),
        ("No.2", "No.2"),
        ("L + α", "L + α"),
        ("$x_1$", "$x_1$"),
        ("Li2O at $T_1$", "Li2O at $T_1$"),
        ("", ""),
    ],
)
def test_to_latex_notation(text, expected):
    assert to_latex_notation(text) == expected


def test_to_latex_notation_formats_formulas_like_get_label():
    for word in ("Li2O", "(LiLa)0.5TiO3", "Li0.33La0.55TiO3"):
        assert to_latex_notation(word) == get_label(word)


@pytest.mark.parametrize("text", [1, None, b"Li2O", ["Li2O"]])
def test_to_latex_notation_not_str(text):
    with pytest.raises(TypeError, match="`text` must be a str"):
        to_latex_notation(text)


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


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        (True, True),
        (False, False),
        (np.bool_(True), True),
        (np.bool_(False), False),
    ],
)
def test_check_optional_bool_accepts(value, expected):
    result = check_optional_bool(value, "flag")

    assert result is expected


@pytest.mark.parametrize(
    "value",
    [True, False, np.bool_(True), np.bool_(False)],
)
def test_check_optional_bool_returns_builtin_bool(value):
    assert type(check_optional_bool(value, "flag")) is bool


@pytest.mark.parametrize("value", [1, 0, "yes", 1.0])
def test_check_optional_bool_invalid(value):
    expected = (
        f"`tight_layout` must be None, True or False, but got {value!r}."
    )

    with pytest.raises(TypeError, match=re.escape(expected)):
        check_optional_bool(value, "tight_layout")


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, True),
        (False, False),
        (np.bool_(True), True),
        (np.bool_(False), False),
    ],
)
def test_check_bool_accepts(value, expected):
    result = check_bool(value, "visible")

    assert type(result) is bool
    assert result is expected


@pytest.mark.parametrize("value", [None, 0, 1, "yes"])
def test_check_bool_invalid(value):
    expected = f"`visible` must be True or False, but got {value!r}."

    with pytest.raises(TypeError, match=re.escape(expected)):
        check_bool(value, "visible")


@pytest.mark.parametrize(
    "step, expected",
    [
        (0.1, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]),
        (0.25, [0.25, 0.5, 0.75]),
        (0.3, [0.3, 0.6, 0.9]),
        (0.7, [0.7]),
        (0.5, [0.5]),
        (1, []),
        (1.0, []),
    ],
)
def test_get_tick_values(step, expected):
    values = get_tick_values(step)

    assert isinstance(values, np.ndarray)
    assert values.ndim == 1
    assert values.dtype == np.float64
    assert values.tolist() == expected


@pytest.mark.parametrize("step, n_values", [(0.1, 9), (0.05, 19), (0.02, 49)])
def test_get_tick_values_count(step, n_values):
    values = get_tick_values(step)

    assert len(values) == n_values
    assert np.all(np.diff(values) > 0)
    assert np.all((values > 0) & (values < 1))


def test_get_tick_values_rounds_to_12_decimals():
    values = get_tick_values(0.05)

    np.testing.assert_array_equal(values, np.round(values, 12))
    assert values.tolist() == [round(0.05 * i, 12) for i in range(1, 20)]
    assert values[0] == 0.05
    assert values[-1] == 0.95


@pytest.mark.parametrize(
    "step", [np.float64(0.1), np.float32(0.1), Fraction(1, 10)]
)
def test_get_tick_values_accepts_real_numbers(step):
    values = get_tick_values(step)

    assert len(values) == 9
    assert values.dtype == np.float64


def test_get_tick_values_accepts_numpy_integer():
    assert get_tick_values(np.int64(1)).tolist() == []


def test_get_tick_values_endpoints_default_is_false():
    assert get_tick_values(0.25).tolist() == [0.25, 0.5, 0.75]
    assert (
        get_tick_values(0.25).tolist()
        == get_tick_values(0.25, endpoints=False).tolist()
    )


@pytest.mark.parametrize(
    "step, expected",
    [
        (0.25, [0.0, 0.25, 0.5, 0.75, 1.0]),
        (0.3, [0.0, 0.3, 0.6, 0.9, 1.0]),
        (1, [0.0, 1.0]),
    ],
)
def test_get_tick_values_endpoints(step, expected):
    values = get_tick_values(step, endpoints=True)

    assert values.dtype == np.float64
    assert values.tolist() == expected


def test_get_tick_values_endpoints_count():
    values = get_tick_values(0.1, endpoints=True)

    assert len(values) == 11
    assert values[0] == 0.0
    assert values[-1] == 1.0


def test_get_tick_values_accepts_numpy_bool_endpoints():
    assert get_tick_values(0.5, endpoints=np.bool_(True)).tolist() == [
        0.0,
        0.5,
        1.0,
    ]


def test_get_tick_values_is_pure():
    first = get_tick_values(0.1)
    first[0] = 99.0

    assert get_tick_values(0.1).tolist() == [
        0.1,
        0.2,
        0.3,
        0.4,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
    ]


@pytest.mark.parametrize(
    "step",
    [0, 0.0, -0.1, -1, 1.5, 2, float("nan"), float("inf"), float("-inf")],
)
def test_get_tick_values_out_of_range(step):
    expected = f"`step` must satisfy 0 < step <= 1, but got {step!r}."

    with pytest.raises(ValueError, match=re.escape(expected)):
        get_tick_values(step)


def test_get_tick_values_huge_int_is_out_of_range():
    # Too large to convert to float, but still a ValueError, not OverflowError.
    with pytest.raises(ValueError, match=re.escape("0 < step <= 1")):
        get_tick_values(10**400)


@pytest.mark.parametrize("step", [np.float64("nan"), np.float64(0.0)])
def test_get_tick_values_out_of_range_numpy(step):
    with pytest.raises(ValueError, match=re.escape("0 < step <= 1")):
        get_tick_values(step)


@pytest.mark.parametrize(
    "step", ["0.1", True, False, np.bool_(True), None, [0.1], 1j]
)
def test_get_tick_values_not_real(step):
    expected = f"`step` must be a real number, but got {step!r}."

    with pytest.raises(TypeError, match=re.escape(expected)):
        get_tick_values(step)


@pytest.mark.parametrize("endpoints", [None, 0, 1, "yes"])
def test_get_tick_values_endpoints_not_bool(endpoints):
    expected = f"`endpoints` must be True or False, but got {endpoints!r}."

    with pytest.raises(TypeError, match=re.escape(expected)):
        get_tick_values(0.1, endpoints=endpoints)


@pytest.mark.parametrize(
    "value, expected",
    [(0.1, "10"), (0.025, "2.5"), (0, "0"), (0.0, "0"), (1, "100")],
)
def test_get_tick_formatter_percent(value, expected):
    assert get_tick_formatter("percent")(value) == expected


def test_get_tick_formatter_percent_reproduces_v3_labels():
    formatter = get_tick_formatter("percent")

    labels = [formatter(v) for v in get_tick_values(0.1)]

    assert labels == ["%d0" % i for i in range(1, 10)]


def test_get_tick_formatter_percent_has_no_unnecessary_digits():
    formatter = get_tick_formatter("percent")

    assert [formatter(v) for v in get_tick_values(0.05)] == [
        str(5 * i) for i in range(1, 20)
    ]
    assert [formatter(v) for v in get_tick_values(0.02)] == [
        str(2 * i) for i in range(1, 50)
    ]


@pytest.mark.parametrize(
    "value, expected",
    [(0.1, "0.1"), (0.05, "0.05"), (0, "0"), (1, "1"), (0.3, "0.3")],
)
def test_get_tick_formatter_fraction(value, expected):
    assert get_tick_formatter("fraction")(value) == expected


def test_get_tick_formatter_fraction_with_tick_values():
    formatter = get_tick_formatter("fraction")

    assert [formatter(v) for v in get_tick_values(0.1)] == [
        f"0.{i}" for i in range(1, 10)
    ]


@pytest.mark.parametrize(
    "fmt, value, expected",
    [
        ("%.2f", 0.1, "0.10"),
        ("%s", 0.5, "0.5"),
        ("%.0f%%", 0.5, "0%"),
        ("{:.0%}", 0.1, "10%"),
        ("{x:.1f}", 0.1, "0.1"),
        ("{}", 0.25, "0.25"),
        ("{:.1f} %", 0.1, "0.1 %"),
    ],
)
def test_get_tick_formatter_format_string(fmt, value, expected):
    assert get_tick_formatter(fmt)(value) == expected


def test_get_tick_formatter_tries_percent_style_first():
    # Valid in both styles: %-style gives "0.5{}", {}-style "%.1f0.5".
    assert get_tick_formatter("%.1f{}")(0.5) == "0.5{}"


def test_get_tick_formatter_callable():
    formatter = get_tick_formatter(lambda v: f"{v * 100:.1f}%")

    assert formatter(0.1) == "10.0%"


def test_get_tick_formatter_callable_result_is_converted_to_str():
    formatter = get_tick_formatter(lambda v: round(v * 100))

    assert formatter(0.1) == "10"


def test_get_tick_formatter_passes_builtin_float():
    received = []

    def fmt(value):
        received.append(value)
        return ""

    get_tick_formatter(fmt)(np.float64(0.3))

    assert received == [0.3]
    assert type(received[0]) is float


@pytest.mark.parametrize("fmt", ["percent", "fraction", "%s", "{}"])
def test_get_tick_formatter_accepts_numpy_float(fmt):
    formatter = get_tick_formatter(fmt)

    assert formatter(np.float64(0.5)) == formatter(0.5)


def test_get_tick_formatter_callable_error_propagates_when_called():
    def fmt(value):
        raise RuntimeError("boom")

    formatter = get_tick_formatter(fmt)

    with pytest.raises(RuntimeError, match="boom"):
        formatter(0.1)


@pytest.mark.parametrize(
    "fmt", ["abc", "", "Percent", "{y}", "{1}", "{:d}", "{x.foo}"]
)
def test_get_tick_formatter_invalid_str(fmt):
    with pytest.raises(ValueError, match=re.escape(repr(fmt))) as excinfo:
        get_tick_formatter(fmt)

    message = str(excinfo.value)
    for accepted in ("'percent'", "'fraction'", "format string", "callable"):
        assert accepted in message


@pytest.mark.parametrize("fmt", [1, None, 0.1, b"%.1f", ["percent"]])
def test_get_tick_formatter_not_str_or_callable(fmt):
    expected = f"`fmt` must be a str or a callable, but got {fmt!r}."

    with pytest.raises(TypeError, match=re.escape(expected)):
        get_tick_formatter(fmt)


# Vertices of the triangle: top, bottom left and bottom right.
VERTICES = ((0.5, ROOT3_OVER_2), (0.0, 0.0), (1.0, 0.0))
EDGE_VALUES = [0.0, 0.1, 0.25, 0.5, 0.9, 1.0]
INVALID_COMPONENTS = [3, -1, 10**400, 1.0, True, np.bool_(False), "0", None]


def _compositions_of(x, y):
    """Invert ``three2two`` independently of the code under test.

    Returns the compositions as an array of shape ``(n, 3)``. A component
    is negative for a point outside the triangle beyond the edge where it
    is 0.
    """
    top = np.asarray(y, dtype=float) / ROOT3_OVER_2
    bottom_right = np.asarray(x, dtype=float) - top / 2.0
    bottom_left = 1.0 - top - bottom_right
    return np.stack((top, bottom_left, bottom_right), axis=-1)


@pytest.mark.parametrize("component", [0, 1, 2])
def test_get_edge_points_lie_on_the_tick_edge(component):
    x, y = get_edge_points(EDGE_VALUES, component)

    compositions = _compositions_of(x, y)
    np.testing.assert_allclose(
        compositions[:, component], EDGE_VALUES, atol=1e-12
    )
    # The ticks of component k are on the edge where component k+1 is 0.
    np.testing.assert_allclose(
        compositions[:, (component + 1) % 3], 0.0, atol=1e-12
    )


@pytest.mark.parametrize(
    "component, start, end",
    [
        (0, VERTICES[2], VERTICES[0]),  # right edge: bottom right -> top
        (1, VERTICES[0], VERTICES[1]),  # left edge: top -> bottom left
        (2, VERTICES[1], VERTICES[2]),  # bottom edge: left -> right
    ],
)
def test_get_edge_points_increase_counterclockwise(component, start, end):
    values = np.array(EDGE_VALUES)

    x, y = get_edge_points(values, component)

    np.testing.assert_allclose(
        x, start[0] + values * (end[0] - start[0]), atol=1e-12
    )
    np.testing.assert_allclose(
        y, start[1] + values * (end[1] - start[1]), atol=1e-12
    )


@pytest.mark.parametrize("component", [0, 1, 2])
def test_get_edge_points_match_three2two(component):
    values = get_tick_values(0.1, endpoints=True)
    compositions = np.zeros((len(values), 3))
    compositions[:, component] = values
    compositions[:, (component + 2) % 3] = 1.0 - values

    x, y = get_edge_points(values, component)

    expected_x, expected_y = three2two(compositions)
    np.testing.assert_allclose(x, expected_x, rtol=0, atol=1e-15)
    np.testing.assert_allclose(y, expected_y, rtol=0, atol=1e-15)


@pytest.mark.parametrize(
    "component, rotation, offset",
    [
        # v3 tick labels: rotation and offset from the edge point, by edge
        (0, 0.0, (0.0, 0.0)),
        (1, 300.0, (-0.01, 0.04)),
        (2, 60.0, (0.02, 0.0)),
    ],
)
def test_get_edge_points_reproduce_v3_tick_positions(
    component, rotation, offset
):
    expected = {
        text.text: text.position
        for text in expected_tick_label_texts()
        if text.rotation == rotation
    }
    values = get_tick_values(0.1)

    x, y = get_edge_points(values, component)

    assert len(expected) == len(values) == 9
    for value, point_x, point_y in zip(values, x, y):
        label = "%d0" % round(value * 10)
        assert (point_x + offset[0], point_y + offset[1]) == pytest.approx(
            expected[label], abs=1e-9
        )


def test_get_edge_points_return_one_dimensional_float_arrays():
    x, y = get_edge_points([0, 1], 2)

    for coordinates in (x, y):
        assert isinstance(coordinates, np.ndarray)
        assert coordinates.shape == (2,)
        assert coordinates.dtype == np.float64
    assert x.tolist() == [0.0, 1.0]
    assert y.tolist() == [0.0, 0.0]


def test_get_edge_points_accepts_scalar():
    x, y = get_edge_points(0.5, 2)

    assert x.tolist() == [0.5]
    assert y.tolist() == [0.0]


def test_get_edge_points_accepts_numpy_integer_component():
    x, y = get_edge_points([0.5], np.int64(0))
    expected_x, expected_y = get_edge_points([0.5], 0)

    assert x.tolist() == expected_x.tolist()
    assert y.tolist() == expected_y.tolist()


def test_get_edge_points_empty():
    x, y = get_edge_points(get_tick_values(1), 0)

    assert x.shape == y.shape == (0,)


@pytest.mark.parametrize("component", [0, 1, 2])
def test_get_grid_segments_shape(component):
    xs, ys = get_grid_segments(get_tick_values(0.1), component)

    for coordinates in (xs, ys):
        assert isinstance(coordinates, np.ndarray)
        assert coordinates.shape == (9, 2)
        assert coordinates.dtype == np.float64


@pytest.mark.parametrize("component", [0, 1, 2])
def test_get_grid_segments_are_iso_composition_lines(component):
    values = np.array(EDGE_VALUES)

    xs, ys = get_grid_segments(values, component)

    start = _compositions_of(xs[:, 0], ys[:, 0])
    end = _compositions_of(xs[:, 1], ys[:, 1])
    np.testing.assert_allclose(start[:, component], values, atol=1e-12)
    np.testing.assert_allclose(end[:, component], values, atol=1e-12)
    # Column 0 is on the edge where component k+1 is 0 (the tick edge),
    # column 1 on the edge where component k+2 is 0.
    np.testing.assert_allclose(start[:, (component + 1) % 3], 0.0, atol=1e-12)
    np.testing.assert_allclose(end[:, (component + 2) % 3], 0.0, atol=1e-12)


@pytest.mark.parametrize("component", [0, 1, 2])
def test_get_grid_segments_start_at_the_edge_points(component):
    values = get_tick_values(0.1)

    xs, ys = get_grid_segments(values, component)

    x, y = get_edge_points(values, component)
    np.testing.assert_array_equal(xs[:, 0], x)
    np.testing.assert_array_equal(ys[:, 0], y)


@pytest.mark.parametrize("component", [0, 1, 2])
def test_get_grid_segments_end_match_three2two(component):
    values = get_tick_values(0.1)
    compositions = np.zeros((len(values), 3))
    compositions[:, component] = values
    compositions[:, (component + 1) % 3] = 1.0 - values

    xs, ys = get_grid_segments(values, component)

    expected_x, expected_y = three2two(compositions)
    np.testing.assert_allclose(xs[:, 1], expected_x, rtol=0, atol=1e-15)
    np.testing.assert_allclose(ys[:, 1], expected_y, rtol=0, atol=1e-15)


def test_get_grid_segments_reproduce_v3_grid():
    values = get_tick_values(0.1)
    segments = []

    for component in range(3):
        xs, ys = get_grid_segments(values, component)
        segments.extend(
            segment_key((x0, y0), (x1, y1))
            for (x0, x1), (y0, y1) in zip(xs, ys)
        )

    assert len(segments) == len(set(segments)) == 27
    assert set(segments) == {line.segment for line in expected_grid_lines()}


def test_get_grid_segments_empty():
    xs, ys = get_grid_segments(get_tick_values(1), 1)

    assert xs.shape == ys.shape == (0, 2)


def test_get_grid_segments_accepts_scalar():
    xs, ys = get_grid_segments(0.5, 2)

    assert xs.shape == ys.shape == (1, 2)
    assert xs[0] == pytest.approx([0.5, 0.75])
    assert ys[0] == pytest.approx([0.0, ROOT3_OVER_2 / 2.0])


def test_edge_points_and_grid_segments_do_not_change_values():
    values = np.array([0.1, 0.5])

    first = get_edge_points(values, 0)
    get_grid_segments(values, 1)
    second = get_edge_points(values, 0)

    assert values.tolist() == [0.1, 0.5]
    np.testing.assert_array_equal(first[0], second[0])
    np.testing.assert_array_equal(first[1], second[1])


@pytest.mark.parametrize("func", [get_edge_points, get_grid_segments])
@pytest.mark.parametrize("component", INVALID_COMPONENTS)
def test_edge_points_and_grid_segments_invalid_component(func, component):
    expected = f"`component` must be 0, 1 or 2, but got {component!r}."

    with pytest.raises(ValueError, match=re.escape(expected)):
        func([0.5], component)


@pytest.mark.parametrize("func", [get_edge_points, get_grid_segments])
def test_edge_points_and_grid_segments_values_not_one_dimensional(func):
    with pytest.raises(ValueError, match=r"one-dimensional.*\(1, 2\)"):
        func([[0.1, 0.2]], 0)


@pytest.mark.parametrize(
    "component, midpoint, normal",
    [
        (0, (0.75, ROOT3_OVER_2 / 2.0), (ROOT3_OVER_2, 0.5)),  # right edge
        (1, (0.25, ROOT3_OVER_2 / 2.0), (-ROOT3_OVER_2, 0.5)),  # left edge
        (2, (0.5, 0.0), (0.0, -1.0)),  # bottom edge
    ],
)
@pytest.mark.parametrize("pad", [0.15, 0.3, 0.0, -0.05])
def test_get_axis_label_position(component, midpoint, normal, pad):
    x, y, _ = get_axis_label_position(component, pad)

    assert (x, y) == pytest.approx(
        (midpoint[0] + pad * normal[0], midpoint[1] + pad * normal[1]),
        abs=1e-12,
    )


@pytest.mark.parametrize("component", [0, 1, 2])
@pytest.mark.parametrize("pad", [0.15, 0.4])
def test_get_axis_label_position_is_pad_away_outside_the_edge(component, pad):
    x, y, _ = get_axis_label_position(component, pad)

    (title,) = _compositions_of([x], [y])
    zero = (component + 1) % 3
    # Distance from the edge where component k+1 is 0 is pad (the height
    # of the triangle corresponds to 1), on the outer side of the edge.
    assert title[zero] == pytest.approx(-pad / ROOT3_OVER_2)
    # On the perpendicular bisector of the edge: the other two components
    # are equal, so the title is pad away from the midpoint of the edge.
    assert title[component] == pytest.approx(title[(component + 2) % 3])
    (mid_x,), (mid_y,) = get_edge_points([0.5], component)
    assert np.hypot(x - mid_x, y - mid_y) == pytest.approx(pad)


@pytest.mark.parametrize("component, rotation", [(0, 300), (1, 60), (2, 0)])
def test_get_axis_label_position_rotation(component, rotation):
    *_, actual = get_axis_label_position(component, 0.15)

    assert actual == rotation
    # Parallel to the edge and not upside down (the text runs rightward).
    x, y = get_edge_points([0.0, 1.0], component)
    angle = np.deg2rad(actual)
    direction = (np.cos(angle), np.sin(angle))
    cross = direction[0] * (y[1] - y[0]) - direction[1] * (x[1] - x[0])
    assert cross == pytest.approx(0.0, abs=1e-12)
    assert direction[0] > 0


@pytest.mark.parametrize("component", [0, 1, 2])
def test_get_axis_label_position_returns_builtin_floats(component):
    result = get_axis_label_position(component, np.float64(0.15))

    assert isinstance(result, tuple)
    assert len(result) == 3
    assert all(type(value) is float for value in result)


@pytest.mark.parametrize(
    "pad",
    [np.float64(0.15), np.float32(0.25), 1, np.int64(0), Fraction(3, 20)],
)
def test_get_axis_label_position_accepts_real_numbers(pad):
    x, y, rotation = get_axis_label_position(2, pad)

    assert (x, y, rotation) == pytest.approx((0.5, -float(pad), 0.0))


@pytest.mark.parametrize("component", INVALID_COMPONENTS)
def test_get_axis_label_position_invalid_component(component):
    expected = f"`component` must be 0, 1 or 2, but got {component!r}."

    with pytest.raises(ValueError, match=re.escape(expected)):
        get_axis_label_position(component, 0.15)


@pytest.mark.parametrize(
    "pad", ["0.15", None, True, False, np.bool_(True), 1j, [0.15]]
)
def test_get_axis_label_position_pad_not_real(pad):
    expected = f"`pad` must be a real number, but got {pad!r}."

    with pytest.raises(TypeError, match=re.escape(expected)):
        get_axis_label_position(0, pad)


@pytest.mark.parametrize(
    "pad",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        np.float64("nan"),
        np.float64("inf"),
    ],
)
def test_get_axis_label_position_pad_not_finite(pad):
    expected = f"`pad` must be a finite real number, but got {pad!r}."

    with pytest.raises(ValueError, match=re.escape(expected)):
        get_axis_label_position(0, pad)


def test_get_axis_label_position_huge_pad_is_not_finite():
    # Too large to convert to float, but a ValueError, not OverflowError.
    with pytest.raises(ValueError, match="finite real number"):
        get_axis_label_position(0, 10**400)


# get_triangular_lattice


def _lattice_areas(vertices, triangles):
    """Signed areas of the small triangles in the 2D coordinates."""
    x, y = three2two(vertices)
    x0, x1, x2 = x[triangles].T
    y0, y1, y2 = y[triangles].T
    return ((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2.0


@pytest.mark.parametrize("scale", [1, 2, 3, 50])
def test_get_triangular_lattice_counts_and_dtypes(scale):
    vertices, triangles = get_triangular_lattice(scale)

    assert vertices.shape == ((scale + 1) * (scale + 2) // 2, 3)
    assert triangles.shape == (scale**2, 3)
    assert vertices.dtype == np.float64
    assert triangles.dtype == np.intp


@pytest.mark.parametrize("scale", [1, 2, 3, 50])
def test_get_triangular_lattice_compositions(scale):
    vertices, triangles = get_triangular_lattice(scale)

    np.testing.assert_allclose(vertices.sum(axis=1), 1.0)
    # Each component is a multiple of 1/scale.
    integers = vertices * scale
    np.testing.assert_allclose(integers, np.round(integers), atol=1e-9)
    # The set of compositions equals the full enumeration.
    actual = {tuple(row) for row in np.round(integers).astype(int).tolist()}
    expected = {
        (i, j, scale - i - j)
        for i in range(scale + 1)
        for j in range(scale + 1 - i)
    }
    assert actual == expected
    assert len(actual) == len(vertices)
    # Every lattice point is used and every index is valid.
    assert triangles.min() == 0
    assert triangles.max() == len(vertices) - 1
    assert set(np.unique(triangles).tolist()) == set(range(len(vertices)))


@pytest.mark.parametrize("scale", [1, 2, 3, 50])
def test_get_triangular_lattice_vertex_order(scale):
    vertices, _ = get_triangular_lattice(scale)
    integers = np.round(vertices * scale).astype(int)

    # Descending i, then descending j within the same i.
    keys = [(-i, -j) for i, j, _ in integers.tolist()]
    assert keys == sorted(keys)
    # In 2D: rows from top to bottom, left to right within a row.
    x, y = three2two(vertices)
    for i in range(scale + 1):
        row = integers[:, 0] == i
        assert np.all(np.diff(x[row]) > 0)


@pytest.mark.parametrize("scale", [1, 2, 3, 50])
def test_get_triangular_lattice_areas(scale):
    vertices, triangles = get_triangular_lattice(scale)
    areas = _lattice_areas(vertices, triangles)

    # Counterclockwise (positive), all equal and covering the diagram.
    assert np.all(areas > 0)
    np.testing.assert_allclose(areas, sqrt(3.0) / 4.0 / scale**2)
    np.testing.assert_allclose(areas.sum(), sqrt(3.0) / 4.0)


@pytest.mark.parametrize("scale", [1, 2, 3, 50])
def test_get_triangular_lattice_upward_then_downward(scale):
    vertices, triangles = get_triangular_lattice(scale)
    n_up = scale * (scale + 1) // 2
    integers = np.round(vertices * scale).astype(int)
    corners = integers[triangles]  # shape (n_triangles, 3, 3)

    up, down = corners[:n_up], corners[n_up:]
    assert len(down) == scale * (scale - 1) // 2
    # Upward: top, bottom left, bottom right of a base (i, j, k).
    base_up = up[:, 0] - [1, 0, 0]
    np.testing.assert_array_equal(up[:, 1], base_up + [0, 1, 0])
    np.testing.assert_array_equal(up[:, 2], base_up + [0, 0, 1])
    # Downward: bottom, upper right, upper left of a base (i, j, k).
    base_down = down[:, 0] - [0, 1, 1]
    np.testing.assert_array_equal(down[:, 1], base_down + [1, 0, 1])
    np.testing.assert_array_equal(down[:, 2], base_down + [1, 1, 0])
    # Bases in descending i, then descending j, within each group.
    for base in (base_up, base_down):
        keys = [(-i, -j) for i, j, _ in base.tolist()]
        assert keys == sorted(keys)


def test_get_triangular_lattice_scale_1():
    vertices, triangles = get_triangular_lattice(1)

    assert vertices.tolist() == [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
    assert triangles.tolist() == [[0, 1, 2]]


def test_get_triangular_lattice_scale_2():
    vertices, triangles = get_triangular_lattice(2)

    assert vertices.tolist() == [
        [1.0, 0.0, 0.0],
        [0.5, 0.5, 0.0],
        [0.5, 0.0, 0.5],
        [0.0, 1.0, 0.0],
        [0.0, 0.5, 0.5],
        [0.0, 0.0, 1.0],
    ]
    assert triangles.tolist() == [[0, 1, 2], [1, 3, 4], [2, 4, 5], [4, 2, 1]]


@pytest.mark.parametrize("scale", [1, 2, 7])
def test_get_triangular_lattice_is_deterministic(scale):
    vertices1, triangles1 = get_triangular_lattice(scale)
    vertices2, triangles2 = get_triangular_lattice(scale)

    np.testing.assert_array_equal(vertices1, vertices2)
    np.testing.assert_array_equal(triangles1, triangles2)
    # Fresh arrays: modifying one result does not affect the next call.
    assert vertices1 is not vertices2
    vertices1[:] = -1.0
    triangles1[:] = -1
    vertices3, triangles3 = get_triangular_lattice(scale)
    np.testing.assert_array_equal(vertices3, vertices2)
    np.testing.assert_array_equal(triangles3, triangles2)


@pytest.mark.parametrize(
    "scale", [np.int64(3), np.int32(3), np.uint8(3), np.intp(3)]
)
def test_get_triangular_lattice_accepts_numpy_integers(scale):
    vertices, triangles = get_triangular_lattice(scale)
    expected_vertices, expected_triangles = get_triangular_lattice(3)

    np.testing.assert_array_equal(vertices, expected_vertices)
    np.testing.assert_array_equal(triangles, expected_triangles)


@pytest.mark.parametrize(
    "scale",
    [1.5, 3.0, "3", True, False, np.bool_(True), None, [3], np.float64(3)],
)
def test_get_triangular_lattice_not_integer(scale):
    expected = f"`scale` must be an integer, but got {scale!r}."

    with pytest.raises(TypeError, match=re.escape(expected)):
        get_triangular_lattice(scale)


@pytest.mark.parametrize("scale", [0, -1, np.int64(0), -(10**20)])
def test_get_triangular_lattice_less_than_one(scale):
    expected = f"`scale` must be 1 or greater, but got {scale!r}."

    with pytest.raises(ValueError, match=re.escape(expected)):
        get_triangular_lattice(scale)
