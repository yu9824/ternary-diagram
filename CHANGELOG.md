# Changelog

See [GitHub Releases](https://github.com/yu9824/ternary-diagram/releases) for the release notes generated from pull requests.

## Unreleased

### Breaking changes

- Drop Python 3.8. Python 3.9 to 3.14 are supported.

### Bug fixes

- Malformed inputs raise `ValueError` with a clear message: a vector whose shape is not `(n, 3)`, `annotations` whose length differs from the number of points, and `contour` without `z`.
- The `ternary-diagram` command works (`ternary-diagram --version`).

### Other changes

- Derive the version from git tags with setuptools-scm.
- Ship `py.typed`.
- Fill in the PyPI description and keywords.
- Rebuild the documentation with MyST-NB and sphinx-book-theme, and publish the example notebooks as tutorials.
- Run the tests offline and cover every plotting method.

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
