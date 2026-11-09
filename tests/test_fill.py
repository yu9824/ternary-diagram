import matplotlib.text
import pytest

from ternary_diagram import _api


def test_default_zorder_constants():
    # 既存の定数は変えない (existing constants are unchanged)
    assert _api.DEFAULT_ZORDER_CONTOUR == 0
    assert _api.DEFAULT_ZORDER_GRIDS == 1
    assert _api.DEFAULT_ZORDER_PLOTS == 2
    assert _api.DEFAULT_ZORDER_SCATTER == 3

    assert _api.DEFAULT_ZORDER_FILL == 0.5
    assert _api.DEFAULT_ZORDER_TEXT == 4
    assert (
        _api.DEFAULT_ZORDER_CONTOUR
        < _api.DEFAULT_ZORDER_FILL
        < _api.DEFAULT_ZORDER_GRIDS
        < _api.DEFAULT_ZORDER_PLOTS
        < _api.DEFAULT_ZORDER_SCATTER
        < _api.DEFAULT_ZORDER_TEXT
    )
    # annotate と土台の文字は matplotlib の既定 (3) のまま
    # (annotations and skeleton labels keep matplotlib's default zorder)
    assert matplotlib.text.Text.zorder == 3
    assert _api.DEFAULT_ZORDER_TEXT > matplotlib.text.Text.zorder


def test_default_zorder_heatmap_is_behind_fill():
    if not hasattr(_api, "DEFAULT_ZORDER_HEATMAP"):
        pytest.skip(
            "DEFAULT_ZORDER_HEATMAP is not defined because heatmaps is not "
            "merged yet; heatmaps checks HEATMAP < FILL when merged later"
        )
    assert _api.DEFAULT_ZORDER_HEATMAP < _api.DEFAULT_ZORDER_FILL
