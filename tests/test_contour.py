import pytest
import pandas as pd

from ternary_diagram import TernaryDiagram


def test_contour(df_contour: pd.DataFrame):
    td = TernaryDiagram(materials=df_contour.columns[:3])
    td.contour(df_contour.iloc[:, :3], df_contour.loc[:, "z"])


def test_contour_without_z(td):
    with pytest.raises(ValueError, match="`z` is required"):
        td.contour([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
