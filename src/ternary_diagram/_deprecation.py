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

import functools
import inspect
import re
import sys
import warnings
from collections.abc import Sequence
from types import FrameType
from typing import Any, Callable, Final, TypeVar

__all__ = (
    "FUTURE_VERSION",
    "UNSET",
    "deprecate_positional",
    "format_default_change",
    "format_positional_deprecation",
    "format_renamed_parameter",
    "positional_options",
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


F = TypeVar("F", bound=Callable[..., Any])


def positional_options(
    parameters: Sequence[str], n_data: int, n_positional: int
) -> tuple[str, ...]:
    """Return the names of the options passed by position.

    Parameters
    ----------
    parameters : Sequence[str]
        Names of the parameters that can be passed by position, in order,
        without ``self``.
    n_data : int
        Number of leading parameters that may stay positional (the data).
    n_positional : int
        Number of arguments passed by position, without ``self``.

    Returns
    -------
    tuple[str, ...]
        The names of the parameters after the first `n_data` that received
        a positional argument. Empty when `n_positional` is at most
        `n_data`.
    """
    return tuple(parameters[n_data:n_positional])


def _join_names(names: Sequence[str]) -> str:
    """Join names as "`a`", "`a` and `b`" or "`a`, `b` and `c`"."""
    quoted = [f"`{name}`" for name in names]
    if len(quoted) == 1:
        return quoted[0]
    return f"{', '.join(quoted[:-1])} and {quoted[-1]}"


def format_positional_deprecation(
    func: str, names: Sequence[str], version: str = FUTURE_VERSION
) -> str:
    """Build the message announcing that options become keyword-only.

    Parameters
    ----------
    func : str
        Name of the function or method that has the parameters, as the user
        calls it.
    names : Sequence[str]
        Names of the parameters passed by position. It must not be empty.
    version : str, optional
        Version that makes the parameters keyword-only, by default
        FUTURE_VERSION

    Returns
    -------
    str
        The message telling the parameters passed by position, the version
        that makes them keyword-only and an example of the call with them
        passed by keyword, in this order.
    """
    pronoun = "it" if len(names) == 1 else "they"
    pronoun_object = "it" if len(names) == 1 else "them"
    example = ", ".join(f"{name}=..." for name in names)
    return (
        f"Passing {_join_names(names)} of `{func}` by position is "
        f"deprecated. In ternary-diagram {version}, {pronoun} will be "
        f"keyword-only. Pass {pronoun_object} by keyword instead, as in "
        f"`{func}(..., {example})`."
    )


def deprecate_positional(
    func_name: str,
    n_data: int,
    *,
    once: Callable[[Any, str], bool] | None = None,
) -> Callable[[F], F]:
    """Warn when options of a method are passed by position.

    The decorated method is called with the arguments as they are, so the
    values keep their meaning. Its signature and docstring stay those of
    the method.

    Parameters
    ----------
    func_name : str
        Name of the method as the user calls it, shown in the message. It
        also makes the key ``"positional.<func_name>"`` passed to `once`.
    n_data : int
        Number of parameters after ``self`` that may stay positional.
    once : Callable[[Any, str], bool] or None, optional
        Called with ``self`` and the key before warning. The warning is
        issued only when it returns True. When None, the warning is issued
        at every call, by default None

    Returns
    -------
    Callable[[F], F]
        Decorator for a method whose first parameter is ``self``.
    """
    key = f"positional.{func_name}"

    def decorator(method: F) -> F:
        positional_kinds = (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
        parameters = [
            parameter.name
            for parameter in inspect.signature(method).parameters.values()
            if parameter.kind in positional_kinds
        ][1:]  # without ``self``

        @functools.wraps(method)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Too many arguments: let the method raise its TypeError.
            if n_data < len(args) <= len(parameters):
                names = positional_options(parameters, n_data, len(args))
                if once is None or once(self, key):
                    warn_external(
                        format_positional_deprecation(func_name, names)
                    )
            return method(self, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
