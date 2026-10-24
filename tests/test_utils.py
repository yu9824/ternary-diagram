import re
from fractions import Fraction
from math import sqrt

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from ternary_diagram.utils import (
    check_1d_vector,
    check_2d_vector,
    check_ax,
    check_bool,
    check_optional_bool,
    get_label,
    get_tick_formatter,
    get_tick_values,
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
