import pytest

from ternary_diagram.utils import check_2d_vector


@pytest.mark.parametrize(
    "vector",
    [[1, 2, 3], [[1, 2]], [[1, 2, 3, 4]], [[[1, 2, 3]] * 3]],
)
def test_check_2d_vector_invalid_shape(vector):
    with pytest.raises(ValueError, match=r"shape must be \(n, 3\)"):
        check_2d_vector(vector)
