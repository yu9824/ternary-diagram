from __future__ import annotations
from pathlib import Path

import matplotlib

# Select a non-interactive backend before pyplot is imported anywhere.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from ternary_diagram import TernaryDiagram  # noqa: E402

EXAMPLE_DIR = Path(__file__).resolve().parent.parent / "example"
MATERIALS = ("Li2O", "La2O3", "TiO2")


def _read_example(name: str) -> pd.DataFrame:
    # The example CSV files start with a UTF-8 BOM.
    return pd.read_csv(
        EXAMPLE_DIR / name / f"example_{name}.csv", encoding="utf-8-sig"
    )


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


@pytest.fixture
def ax():
    _, ax = plt.subplots()
    return ax


@pytest.fixture
def td(ax) -> TernaryDiagram:
    return TernaryDiagram(MATERIALS, ax=ax, tight_layout=True)


@pytest.fixture
def df_scatter() -> pd.DataFrame:
    return _read_example("scatter")


@pytest.fixture
def df_mono_scatter() -> pd.DataFrame:
    return _read_example("mono_scatter")


@pytest.fixture
def df_contour() -> pd.DataFrame:
    return _read_example("contour")
