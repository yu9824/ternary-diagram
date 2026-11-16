# Changelog

See [GitHub Releases](https://github.com/yu9824/ternary-diagram/releases) for the release notes generated from pull requests.

## Unreleased

### New features

- `TernaryDiagram.colorbar` chooses the direction of the colorbar from `location` when `orientation` is not given, so `location="bottom"` or `"top"` alone draws a horizontal colorbar instead of raising `TypeError`. The default colorbar stays vertical on the right.

## v3.3.0

### Breaking changes

- Drop Python 3.8. Python 3.9 to 3.14 are supported.
- `scatter` and `contour` raise `TypeError` when the 6th positional argument (formerly `flag_cbar`, now `colorbar`) is not a bool, such as `0` or `1`. Pass `True` or `False`, or use the keyword argument `flag_cbar`, which is still interpreted as true or false (deprecated). `None` in this position now means that `colorbar` is not specified, so a colorbar is added when `z` is given, where it used to add none; pass `False` to add none.

### New features

- `TernaryDiagram(tight_layout=...)` chooses whether the figure margins are adjusted with `Figure.tight_layout()` after each plotting call.
- `scatter(colorbar=...)` and `contour(colorbar=...)` choose whether a colorbar is added automatically.
- `ternary_diagram.utils` gains `check_optional_bool` and `check_bool`, public functions that validate optional and required boolean arguments.
- The look of the 5 parts that `TernaryDiagram` draws (the border, the grid, the tick labels, the axis titles and the vertex labels) can be customized.
  - At construction with `border_kw`, `grid_kw`, `tick_kw`, `axis_label_kw` and `vertex_label_kw`, and afterwards with `set_border`, `set_grid`, `set_ticks`, `set_axis_labels` and `set_vertex_labels`. Each `*_kw` is equivalent to calling the corresponding method right after construction.
  - They take the items of each part (`visible`; `step` of the grid and the tick labels; `fmt` and `endpoints` of the tick labels; `labels` and `pad` of the axis titles; `labels` and `offsets` of the vertex labels, where `vertex_label_kw` takes only `offsets` because the labels come from `materials`) and matplotlib properties such as `color`, `linewidth` and `fontsize`. Settings not given keep their previous values.
  - Axis titles along the edges can be drawn with `set_axis_labels([...])` or `axis_label_kw={"labels": [...]}`. None are drawn by default.
- The read-only properties `border_lines_`, `grid_lines_`, `tick_labels_`, `axis_labels_` and `vertex_labels_` return the artists that each part draws, to adjust them one by one.
- `ternary_diagram.utils` gains `get_tick_values`, `get_tick_formatter` (with the type alias `TickFormat`), `get_edge_points`, `get_grid_segments` and `get_axis_label_position`, which compute the placement and the format of the tick labels, the grid lines and the axis titles without a figure.
- `annotate(auto_latex_notation=...)` and `scatter(auto_latex_notation=...)` choose whether the chemical formulas in the text are written in LaTeX notation. `True` formats only the words that look like chemical formulas (`"LiF + Li2O"` to `"LiF + Li$_{2}$O"`, while `"Sample 1"` stays as it is), and `False` shows the text as it is.
- `ternary_diagram.utils` gains `is_chemical_formula` and `to_latex_notation`, which tell whether a word looks like a chemical formula and format the chemical formulas in a text.
- `fill` shades a polygon whose vertices are given as compositions, such as a region of a phase diagram, and can be labeled for the legend. By default it is drawn above contours and behind the grid and the other plots.
- `text` places a text exactly at a composition, centered by default and drawn in front of the other plots. The chemical formulas in it are formatted following `auto_latex_notation` of `TernaryDiagram`, which `text(auto_latex_notation=...)` overrides for that call.
- `tripcolor` paints the triangles between scattered compositions with colors given by a value at each composition, without interpolating on a grid (`shading="flat"` or `"gouraud"`). Only the inside of the convex hull of the compositions is painted, and triangles touching a NaN value are left blank.
- `heatmapf` evaluates a function `f(a, b, c)` of the composition on a regular triangular lattice, calling it once with arrays, and paints the result as a heatmap; `scale` sets the number of divisions of each edge (50 by default). A function that returns NaN leaves those triangles blank.
- Both heatmaps are drawn behind every other plot by default and add a colorbar in the same way as `scatter` and `contour` (`colorbar=...`, `z_min` / `z_max` and their aliases `vmin` / `vmax`).
- `ternary_diagram.utils` gains `get_triangular_lattice`, which returns the points and the triangles of a regular triangular lattice without a figure.

### Deprecations

- `flag_cbar` of `scatter` and `contour` is deprecated and will be removed in 4.0.0. Use `colorbar` instead.
- The following defaults will change in 4.0.0. A `FutureWarning` is emitted, once per diagram for each of these changes, when a call made with the default would give a different result under the new default. Pass `tight_layout`, `colorbar` or `auto_latex_notation` explicitly to keep the current behavior or to adopt the new one.
  - `TernaryDiagram` will use `tight_layout=False` and no longer adjust the figure layout after plotting.
  - `scatter`, `contour`, `tripcolor` and `heatmapf` will not add a colorbar automatically to a diagram that already has one.
  - `annotate` and the annotations of `scatter` will format only the words that look like chemical formulas, and only when `auto_latex_notation` of `TernaryDiagram` is true. Now every number in the text is written as a subscript (`"Sample 1"` to `"Sample $_{1}$"`), whatever the setting of the diagram.

### Bug fixes

- Malformed inputs raise `ValueError` with a clear message: a vector whose shape is not `(n, 3)`, `annotations` whose length differs from the number of points, and `contour` without `z`.
- The `ternary-diagram` command works (`ternary-diagram --version`).
- Plotting no longer replaces a layout engine already set on the figure (constrained, compressed, tight, and so on), and no longer makes matplotlib warn that the figure layout has changed to tight.
- Plotting that adds a colorbar (for example `contour(z)`) on a figure created with `layout="constrained"` no longer raises `RuntimeError`.
- Plotting on Axes of a subfigure no longer raises `AttributeError`.
- `TernaryDiagram` raises `ValueError` instead of `IndexError` when `materials` has fewer than 3 items, and `TypeError` with a clear message when `materials` is not iterable.
- `scatter(annotations=...)` accepts annotations that are not str, such as numbers, instead of raising `ValueError`.
- `annotate` and the annotations of `scatter` show a text containing `$` (mathtext) as it is, instead of inserting subscripts into it that could not be drawn.

### Other changes

- Derive the version from git tags with setuptools-scm.
- Ship `py.typed`.
- Fill in the PyPI description and keywords.
- Rebuild the documentation with MyST-NB and sphinx-book-theme, and publish the example notebooks as tutorials.
- Run the tests offline and cover every plotting method.
- Run the docstring examples of the public API in the tests.
- Add a user guide to the documentation with task-oriented pages on getting started, customizing the diagram, drawing phase diagrams, choosing between heatmaps and contour maps, and controlling the layout and colorbars, and a page on [migrating to v4.0.0](https://yu9824.github.io/ternary-diagram/user_guide/migration_v4.html).
- Rewrite the docstrings of `TernaryDiagram` and the existing `utils` functions, with runnable examples.
- Rewrite the README around a minimal example and links to the documentation.
- Update the tutorial notebooks to create figures with `layout="constrained"` and to use `colorbar` instead of `flag_cbar`.

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
