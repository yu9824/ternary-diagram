import pytest

from ternary_diagram import __version__
from ternary_diagram.__main__ import main


@pytest.mark.parametrize("flag", ["-v", "--version"])
def test_version(flag, capsys):
    with pytest.raises(SystemExit) as excinfo:
        main([flag], prog="ternary-diagram")

    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"ternary-diagram: {__version__}"


def test_no_args():
    main([])
