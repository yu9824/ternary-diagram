import pandas as pd

from ternary_diagram import TernaryDiagram


def test_contour(df_contour: pd.DataFrame):
    td = TernaryDiagram(materials=df_contour.columns[:3])
    td.contour(df_contour.iloc[:, :3], df_contour.loc[:, "z"])
