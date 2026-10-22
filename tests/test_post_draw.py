import matplotlib
import matplotlib.pyplot as plt
import pytest

from ternary_diagram import _post_draw
from ternary_diagram._post_draw import LayoutState, get_layout_state

requires_layout_engine = pytest.mark.skipif(
    not _post_draw._HAS_LAYOUT_ENGINE,
    reason="Figure.get_layout_engine needs matplotlib >= 3.6",
)


@pytest.fixture
def without_layout_engine(monkeypatch):
    """Take the branch for matplotlib < 3.6."""
    monkeypatch.setattr(_post_draw, "_HAS_LAYOUT_ENGINE", False)


def test_has_layout_engine_matches_matplotlib():
    # The skipif above relies on this constant, so check it independently.
    assert _post_draw._HAS_LAYOUT_ENGINE == hasattr(
        matplotlib.figure.Figure, "get_layout_engine"
    )


def test_get_layout_state_annotations_are_not_evaluated():
    # Evaluating them would fail on old matplotlib (``FigureBase``) and on
    # Python 3.9 (``X | None``).
    annotations = get_layout_state.__annotations__
    assert annotations
    assert all(isinstance(value, str) for value in annotations.values())


@requires_layout_engine
@pytest.mark.parametrize(
    "fig_kw", [{}, {"layout": None}, {"layout": "none"}], ids=repr
)
def test_get_layout_state_new_figure_has_no_engine(fig_kw):
    fig, _ = plt.subplots(**fig_kw)
    assert fig.get_layout_engine() is None
    assert get_layout_state(fig) is LayoutState.NO_ENGINE


@requires_layout_engine
def test_get_layout_state_after_tight_layout_has_no_engine():
    from matplotlib.layout_engine import PlaceHolderLayoutEngine

    fig, _ = plt.subplots()
    fig.tight_layout()
    # Figure.tight_layout() leaves a placeholder engine behind.
    assert isinstance(fig.get_layout_engine(), PlaceHolderLayoutEngine)
    assert get_layout_state(fig) is LayoutState.NO_ENGINE
    # It stays so after a second adjustment.
    fig.tight_layout()
    assert get_layout_state(fig) is LayoutState.NO_ENGINE


@requires_layout_engine
@pytest.mark.parametrize("layout", ["constrained", "compressed", "tight"])
def test_get_layout_state_layout_argument_has_engine(layout):
    fig, _ = plt.subplots(layout=layout)
    assert get_layout_state(fig) is LayoutState.HAS_ENGINE


@requires_layout_engine
@pytest.mark.parametrize(
    "rc", ["figure.autolayout", "figure.constrained_layout.use"]
)
def test_get_layout_state_rcparams_has_engine(rc):
    with matplotlib.rc_context({rc: True}):
        fig, _ = plt.subplots()
    assert fig.get_layout_engine() is not None
    assert get_layout_state(fig) is LayoutState.HAS_ENGINE


@pytest.mark.parametrize("layout", [None, "constrained"])
def test_get_layout_state_subfigure_is_unsupported(layout):
    subfig = plt.figure(layout=layout).subfigures(1, 2)[0]
    assert get_layout_state(subfig) is LayoutState.UNSUPPORTED
    nested = subfig.subfigures(2, 1)[0]
    assert get_layout_state(nested) is LayoutState.UNSUPPORTED


# matplotlib < 3.6: the state comes from the constrained and tight flags.


@pytest.mark.usefixtures("without_layout_engine")
@pytest.mark.parametrize("layout", [None, "constrained"])
@pytest.mark.parametrize(
    ("constrained", "tight", "expected"),
    [
        (False, False, LayoutState.NO_ENGINE),
        (True, False, LayoutState.HAS_ENGINE),
        (False, True, LayoutState.HAS_ENGINE),
        (True, True, LayoutState.HAS_ENGINE),
    ],
)
def test_get_layout_state_old_matplotlib_uses_flags(
    monkeypatch, layout, constrained, tight, expected
):
    # The actual engine of the figure must not matter, only the flags.
    fig = plt.figure(layout=layout)
    monkeypatch.setattr(fig, "get_constrained_layout", lambda: constrained)
    monkeypatch.setattr(fig, "get_tight_layout", lambda: tight)
    assert get_layout_state(fig) is expected


@pytest.mark.usefixtures("without_layout_engine")
@pytest.mark.parametrize(
    ("fig_kw", "rc", "expected"),
    [
        ({}, {}, LayoutState.NO_ENGINE),
        ({"layout": "constrained"}, {}, LayoutState.HAS_ENGINE),
        ({"layout": "tight"}, {}, LayoutState.HAS_ENGINE),
        ({}, {"figure.autolayout": True}, LayoutState.HAS_ENGINE),
        ({}, {"figure.constrained_layout.use": True}, LayoutState.HAS_ENGINE),
    ],
    ids=["new", "constrained", "tight", "autolayout", "constrained_use"],
)
def test_get_layout_state_old_matplotlib_real_figure(fig_kw, rc, expected):
    with matplotlib.rc_context(rc):
        fig, _ = plt.subplots(**fig_kw)
    assert get_layout_state(fig) is expected


@pytest.mark.usefixtures("without_layout_engine")
def test_get_layout_state_old_matplotlib_after_tight_layout():
    fig, _ = plt.subplots()
    fig.tight_layout()
    assert get_layout_state(fig) is LayoutState.NO_ENGINE


@pytest.mark.usefixtures("without_layout_engine")
def test_get_layout_state_old_matplotlib_subfigure_is_unsupported():
    subfig = plt.figure().subfigures(1, 2)[0]
    assert get_layout_state(subfig) is LayoutState.UNSUPPORTED
