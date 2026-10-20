import pytest
import pandas as pd

from ternary_diagram import TernaryDiagram


def test_scatter(df_scatter: pd.DataFrame):
    td = TernaryDiagram(materials=df_scatter.columns[:3])
    td.scatter(df_scatter.iloc[:, :3], df_scatter.loc[:, "z"])


def test_mono_scatter(df_mono_scatter: pd.DataFrame):
    td = TernaryDiagram(materials=df_mono_scatter.columns)
    td.scatter(df_mono_scatter)


def test_scatter_annotations_length_mismatch(td):
    with pytest.raises(ValueError, match="annotations"):
        td.scatter([[1, 0, 0], [0, 1, 0]], annotations=["a"])
