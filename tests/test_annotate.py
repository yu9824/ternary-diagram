from __future__ import annotations
from math import sqrt

import pytest
from matplotlib.text import Annotation

ROOT3_OVER_2 = sqrt(3.0) / 2.0


@pytest.mark.parametrize("vector", [[1, 0, 0], [2, 0, 0], [[1, 0, 0]]])
def test_annotate(td, vector):
    annotation = td.annotate("Li2O", vector)

    assert isinstance(annotation, Annotation)
    assert annotation.get_text() == "Li$_{2}$O"
    assert annotation.xy == pytest.approx((0.5, ROOT3_OVER_2))
    assert annotation.xyann == pytest.approx((0.52, ROOT3_OVER_2 + 0.02))
    assert annotation.get_fontsize() == 8


def test_kwargs_override_defaults(td):
    annotation = td.annotate(
        "A", [0, 1, 0], xytext=(0.1, 0.2), fontsize=12, color="red"
    )

    assert annotation.get_text() == "A"
    assert annotation.xy == pytest.approx((0.0, 0.0))
    assert annotation.xyann == pytest.approx((0.1, 0.2))
    assert annotation.get_fontsize() == 12
    assert annotation.get_color() == "red"


def test_records_coordinates(td):
    td.annotate("A", [0, 0, 1])

    assert td.x_["annotate"][0] == pytest.approx([1.0])
    assert td.y_["annotate"][0] == pytest.approx([0.0])


@pytest.mark.parametrize("vector", [[1, 2], [1, 2, 3, 4]])
def test_invalid_vector_length(td, vector):
    with pytest.raises(ValueError, match="length must be 3"):
        td.annotate("A", vector)
