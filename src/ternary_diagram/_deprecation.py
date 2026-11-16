"""User-facing warnings, deprecations and default changes.

``warn_external`` is the only place in the package that issues warnings to
users. It reports the first frame outside ``ternary_diagram`` as the
location of the warning, so that users see the line of their own code. The
messages for deprecations and default changes are built here too, so that
both share the same structure: what changes, when it changes and how to
write the code.

This module imports no other module of the package.
"""

from __future__ import annotations

import re
import sys
import warnings
from types import FrameType
from typing import Any, Final

__all__ = (
    "FUTURE_VERSION",
    "UNSET",
    "format_default_change",
    "format_renamed_parameter",
    "resolve_renamed_parameter",
    "warn_external",
)

FUTURE_VERSION: Final[str] = "4.0.0"
"""Version planned for the default changes and the removal of old names."""

_PACKAGE_MODULE: Final[re.Pattern[str]] = re.compile(
    r"\Aternary_diagram(\Z|\.)"
)


class _Unset:
    """Type of the sentinel for an omitted argument. Its repr is "<UNSET>"."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<UNSET>"


UNSET: Final[_Unset] = _Unset()
"""The only instance of ``_Unset``, to tell an omitted argument from None."""


def _external_stacklevel(frame: FrameType) -> int:
    """Count the levels from `frame` to the first frame outside the package.

    Parameters
    ----------
    frame : FrameType
        Frame to start from. It counts as level 1.

    Returns
    -------
    int
        Level of the first frame whose module name is not
        ``ternary_diagram`` or one of its submodules. When the stack runs
        out before such a frame is found, the level of the last frame.
    """
    stacklevel = 1
    while (
        _PACKAGE_MODULE.match(frame.f_globals.get("__name__", ""))
        and frame.f_back is not None
    ):
        frame = frame.f_back
        stacklevel += 1
    return stacklevel


def warn_external(
    message: str, category: type[Warning] = FutureWarning
) -> None:
    """Issue a warning located at the first caller outside the package.

    The location does not depend on how deep inside the package this
    function is called from.

    Parameters
    ----------
    message : str
        Text of the warning.
    category : type[Warning], optional
        Class of the warning, by default FutureWarning
    """
    # Level 1 is the frame of this function, which is inside the package.
    stacklevel = _external_stacklevel(sys._getframe())
    warnings.warn(message, category, stacklevel=stacklevel)


def format_default_change(
    *,
    current: str,
    future: str,
    keep: str,
    adopt: str,
    version: str = FUTURE_VERSION,
) -> str:
    """Build the message announcing a change of a default.

    Parameters
    ----------
    current : str
        Complete sentence telling what happened now.
    future : str
        Complete sentence telling the behavior after the change. It follows
        ``"In ternary-diagram {version}, "``.
    keep : str
        Verb phrase, without a trailing period, telling how to keep the
        current behavior.
    adopt : str
        Verb phrase, without a trailing period, telling how to adopt the new
        behavior now.
    version : str, optional
        Version that changes the default, by default FUTURE_VERSION

    Returns
    -------
    str
        The message, in the order of `current`, `version`, `future`, `keep`
        and `adopt`.

    Raises
    ------
    ValueError
        When `current`, `future`, `keep` or `adopt` is empty.
    """
    parts = {
        "current": current,
        "future": future,
        "keep": keep,
        "adopt": adopt,
    }
    for name, text in parts.items():
        if not text:
            raise ValueError(f"`{name}` must be a non-empty string.")
    return (
        f"{current} In ternary-diagram {version}, {future} "
        f"To keep the current behavior, {keep}. "
        f"To adopt the new behavior now, {adopt}."
    )


def format_renamed_parameter(
    *, func: str, old: str, new: str, version: str = FUTURE_VERSION
) -> str:
    """Build the message announcing a renamed parameter.

    Parameters
    ----------
    func : str
        Name of the function or method that has the parameter.
    old : str
        Old name of the parameter.
    new : str
        New name of the parameter.
    version : str, optional
        Version that removes `old`, by default FUTURE_VERSION

    Returns
    -------
    str
        The message telling the new name, the version that removes the old
        name and how to rewrite the call, in this order.
    """
    return (
        f"`{old}` of `{func}` was renamed to `{new}`. "
        f"`{old}` will be removed in ternary-diagram {version}. "
        f"Pass `{new}` instead."
    )


def resolve_renamed_parameter(
    *,
    func: str,
    old: str,
    new: str,
    old_value: Any,
    new_value: Any,
    version: str = FUTURE_VERSION,
) -> Any:
    """Decide the value to use from a renamed parameter and its old name.

    The default of the new parameter must be None.

    Parameters
    ----------
    func : str
        Name of the function or method that has the parameter.
    old : str
        Old name of the parameter.
    new : str
        New name of the parameter.
    old_value : Any
        Value passed with the old name, or ``UNSET`` when it was omitted.
    new_value : Any
        Value passed with the new name. None means that it was omitted.
    version : str, optional
        Version that removes `old`, by default FUTURE_VERSION

    Returns
    -------
    Any
        `new_value` when `old_value` is ``UNSET``. Otherwise `old_value` as
        it is, after a FutureWarning about the rename.

    Raises
    ------
    ValueError
        When both `old_value` and `new_value` are specified.
    """
    if old_value is UNSET:
        return new_value
    if new_value is not None:
        raise ValueError(
            f"`{old}` and `{new}` cannot be specified at the same time."
        )
    warn_external(
        format_renamed_parameter(func=func, old=old, new=new, version=version)
    )
    return old_value
