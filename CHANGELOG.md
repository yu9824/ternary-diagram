# Changelog

See [GitHub Releases](https://github.com/yu9824/ternary-diagram/releases) for the release notes generated from pull requests.

## Unreleased

### Breaking changes

- Drop Python 3.8. Python 3.9 to 3.14 are supported.
- `scatter` and `contour` raise `TypeError` when the 6th positional argument (formerly `flag_cbar`, now `colorbar`) is not a bool, such as `0` or `1`. Pass `True` or `False`, or use the keyword argument `flag_cbar`, which is still interpreted as true or false (deprecated). `None` in this position now means that `colorbar` is not specified, so a colorbar is added when `z` is given, where it used to add none; pass `False` to add none.

### New features

- `TernaryDiagram(tight_layout=...)` chooses whether the figure margins are adjusted with `Figure.tight_layout()` after each plotting call.
- `scatter(colorbar=...)` and `contour(colorbar=...)` choose whether a colorbar is added automatically.
- `ternary_diagram.utils` gains `check_optional_bool` and `check_bool`, public functions that validate optional and required boolean arguments.

### Deprecations

- `flag_cbar` of `scatter` and `contour` is deprecated and will be removed in 4.0.0. Use `colorbar` instead.
- The following defaults will change in 4.0.0. A `FutureWarning` is emitted, once per diagram for each of these changes, when a call made with the default would give a different result under the new default. Pass `tight_layout` or `colorbar` explicitly to keep the current behavior or to adopt the new one.
  - `TernaryDiagram` will use `tight_layout=False` and no longer adjust the figure layout after plotting.
  - `scatter` and `contour` will not add a colorbar automatically to a diagram that already has one.

### Bug fixes

- Malformed inputs raise `ValueError` with a clear message: a vector whose shape is not `(n, 3)`, `annotations` whose length differs from the number of points, and `contour` without `z`.
- The `ternary-diagram` command works (`ternary-diagram --version`).
- Plotting no longer replaces a layout engine already set on the figure (constrained, compressed, tight, and so on), and no longer makes matplotlib warn that the figure layout has changed to tight.
- Plotting that adds a colorbar (for example `contour(z)`) on a figure created with `layout="constrained"` no longer raises `RuntimeError`.
- Plotting on Axes of a subfigure no longer raises `AttributeError`.

### Other changes

- Derive the version from git tags with setuptools-scm.
- Ship `py.typed`.
- Fill in the PyPI description and keywords.
- Rebuild the documentation with MyST-NB and sphinx-book-theme, and publish the example notebooks as tutorials.
- Run the tests offline and cover every plotting method.
- Run the docstring examples of the public API in the tests.

## v3.2.2

### Bug fixes

- `contour` draws when all `z` values are equal. The check was broken by floating point rounding (for example `z = 1.7`).
- `contour(levels=...)`, `scatter(vmin=..., vmax=...)` and `scatter(c=...)` no longer raise `TypeError` for duplicate keyword arguments.
  - `levels` is used instead of the automatic levels and cannot be combined with `z_min` / `z_max`.
  - `vmin` / `vmax` are aliases of `z_min` / `z_max`.
  - `c` together with `z` raises `ValueError` because the colors are determined by `z`.

## v3.1.0

- Delete `.utils._BasePlotter.get_x_y` (we should access directly).
- Resolve #10 (Create `fill` argument in `TernaryDiagram.contour`).
- Resolve #11 (Create `auto_latex_notation` argument in `TernaryDiagram`).
- Update documentation.
- Update docstrings and typings.
