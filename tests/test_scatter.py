import pandas as pd

from ternary_diagram import TernaryDiagram


def test_scatter(df_scatter: pd.DataFrame):
    td = TernaryDiagram(materials=df_scatter.columns[:3])
    td.scatter(df_scatter.iloc[:, :3], df_scatter.loc[:, "z"])


def test_mono_scatter(df_mono_scatter: pd.DataFrame):
    td = TernaryDiagram(materials=df_mono_scatter.columns)
    td.scatter(df_mono_scatter)
