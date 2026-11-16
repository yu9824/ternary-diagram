---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Migrating to v4.0.0

ternary-diagram 4.0.0 will change some defaults and remove a deprecated argument.
This page lists each change, the `FutureWarning` that announces it in v3.x, the calls that emit it, and how to keep the current behavior or adopt the new one now.
Code that follows the advice in the warnings runs without warnings in v3.x and draws the same figure in v3.x and v4.0.0.

Each section shows the code that emits the warning in a static block, followed by the warning that the code emits when this page is built with the current version of ternary-diagram.
Expand "Show code cell source" above that output to see how the warning is caught: the code of the block runs unchanged between the `Begin` and `End` comments inside `warnings.catch_warnings`, and the caught warnings are printed, wrapped at spaces to fit the page.

The values on this page are made up for illustration.
They come from a smooth function of the composition of Li2O, La2O3 and TiO2, evaluated at 40 random compositions, and are not measured properties of this system.

```{code-cell} ipython3
import matplotlib.pyplot as plt
import numpy as np

from ternary_diagram import TernaryDiagram
from ternary_diagram.utils import get_label

materials = ["Li2O", "La2O3", "TiO2"]


def property_value(a, b, c):
    """A made-up property between 0 and 1, highest near (0.5, 0.3, 0.2)."""
    distance2 = (a - 0.5) ** 2 + (b - 0.3) ** 2 + (c - 0.2) ** 2
    return np.exp(-distance2 / 0.08)


rng = np.random.default_rng(0)
compositions = rng.dirichlet([1.5, 1.5, 1.5], size=40)
values = property_value(*compositions.T)
```

(migration-v4-summary)=
## Summary of changes

The table compares v3.x and v4.0.0 for each change, and shows the code that keeps the v3.x behavior or adopts the v4.0.0 behavior.
For the changes of defaults, the v3.x and v4.0.0 columns describe the behavior when the argument named in the first column is not specified.
The code in the last two columns emits no `FutureWarning` and behaves the same in v3.x and v4.0.0.
The [changelog](https://github.com/yu9824/ternary-diagram/blob/main/CHANGELOG.md) lists these changes under "Deprecations".

| Change | v3.x | v4.0.0 | Keep the v3.x behavior | Adopt the v4.0.0 behavior |
|---|---|---|---|---|
| [Layout adjustment](#migration-v4-layout) (`tight_layout` of `TernaryDiagram`) | Calls `Figure.tight_layout()` after each plotting call on a figure without a layout engine | Leaves the layout untouched, as with `tight_layout=False` | `TernaryDiagram(..., tight_layout=True)` | `TernaryDiagram(..., tight_layout=False)` and `fig.tight_layout()`, or a figure created with `layout="constrained"` |
| [Colorbar on a diagram that already has one](#migration-v4-colorbar) (`colorbar` of `scatter`, `contour`, `tripcolor` and `heatmapf`) | Adds another colorbar | Adds none | `colorbar=True` | `colorbar=False` |
| [`flag_cbar`](#migration-v4-flag-cbar) of `scatter` and `contour` | Deprecated name of `colorbar` | Removed | `colorbar=...` with the same value | `colorbar=...` with the same value |
| [Formatting of annotations](#migration-v4-annotations) (`auto_latex_notation` of `annotate` and of `scatter` with `annotations`) | Writes every number as a subscript (`"Sample 1"` is shown as `"Sample $_{1}$"`), whatever the setting of the diagram | Follows `auto_latex_notation` of `TernaryDiagram`, and formats only the words that look like chemical formulas | The text formatted with `get_label`, and `auto_latex_notation=False` | `auto_latex_notation=True` to format the chemical formulas, or `False` to show the text as it is |

The warnings about the defaults are emitted at most once per diagram for each change, and only when the call would give a different result in v4.0.0.
The warning about `flag_cbar` is emitted by every call that passes it.
Each warning points at the line of your code that made the call.
Since later calls on the same diagram do not warn again, fix every call of the same kind, not only the first one; [Finding affected code](#migration-v4-finding) shows how to find them all.

(migration-v4-layout)=
## Layout warning

A plotting call, such as {py:meth}`~ternary_diagram.TernaryDiagram.scatter` or {py:meth}`~ternary_diagram.TernaryDiagram.plot`, emits this warning when the diagram was created without `tight_layout` and its figure has no layout engine, for example a figure created by `plt.subplots()` without `layout`, or by `TernaryDiagram(materials)` without `ax`.
A figure with a layout engine, such as `layout="constrained"`, and a subfigure are never adjusted and never warn.
Creating the diagram and the `set_*` methods do not adjust the layout either.

Code that emits the warning:

```python
fig, ax = plt.subplots()
td = TernaryDiagram(materials, ax=ax)
points = td.scatter(compositions, z=values)
```

```{code-cell} ipython3
---
tags: [hide-input]
---
import textwrap
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    # Begin: the code of the block above, unchanged.
    fig, ax = plt.subplots()
    td = TernaryDiagram(materials, ax=ax)
    points = td.scatter(compositions, z=values)
    # End
plt.close("all")
for w in caught:
    text = f"{w.category.__name__}: {w.message}"
    # Wrap at spaces only, so the text of the warning is unchanged.
    print(
        textwrap.fill(
            text, 79, break_long_words=False, break_on_hyphens=False
        )
    )
```

To keep the current behavior, pass `tight_layout=True` to {py:class}`~ternary_diagram.TernaryDiagram`.
The figure margins are still fitted after each plotting call, without the warning:

```{code-cell} ipython3
---
mystnb:
  image:
    alt: A ternary diagram of Li2O, La2O3 and TiO2 with 40 points colored in the rainbow colormap by the made-up property, red near 50 % Li2O, 30 % La2O3 and 20 % TiO2 and blue to purple farther from it, and a colorbar from about 0 to 1 on the right.
---
fig, ax = plt.subplots()
td = TernaryDiagram(materials, ax=ax, tight_layout=True)
points = td.scatter(compositions, z=values)
```

To adopt the new behavior now, pass `tight_layout=False` and call `fig.tight_layout()` yourself, once after the last plotting call:

```{code-cell} ipython3
---
mystnb:
  image:
    alt: The same ternary diagram of Li2O, La2O3 and TiO2 with 40 points colored in the rainbow colormap by the made-up property and a colorbar from about 0 to 1 on the right.
---
fig, ax = plt.subplots()
td = TernaryDiagram(materials, ax=ax, tight_layout=False)
points = td.scatter(compositions, z=values)
fig.tight_layout()
```

Or create the figure with a layout engine, which arranges the figure every time it is drawn; `tight_layout` does not need to be passed.
This is the way recommended in this user guide:

```{code-cell} ipython3
---
mystnb:
  image:
    alt: The same ternary diagram of Li2O, La2O3 and TiO2 with 40 points colored in the rainbow colormap by the made-up property and a colorbar from about 0 to 1 on the right, laid out by the constrained layout engine.
---
fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(materials, ax=ax)
points = td.scatter(compositions, z=values)
```

[Layout and colorbars](layout_and_colorbars.md) explains the layout engines, multiple panels and subfigures.

(migration-v4-colorbar)=
## Duplicate colorbar warning

The plots colored by values, {py:meth}`~ternary_diagram.TernaryDiagram.scatter` with `z`, {py:meth}`~ternary_diagram.TernaryDiagram.contour`, {py:meth}`~ternary_diagram.TernaryDiagram.tripcolor` and {py:meth}`~ternary_diagram.TernaryDiagram.heatmapf`, emit this warning when they are called without `colorbar` on a diagram that already has a colorbar.
A diagram already has a colorbar when one was added through this `TernaryDiagram`, automatically or with {py:meth}`~ternary_diagram.TernaryDiagram.colorbar`, and was not removed; see {ref}`Automatic colorbars <layout-and-colorbars-automatic-colorbars>` for the details.
The first plot colored by values on a diagram adds a colorbar in both versions and does not warn.

Code that emits the warning, at the second plot colored by values:

```python
fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(materials, ax=ax)
heatmap = td.tripcolor(compositions, values)
points = td.scatter(compositions, z=values, edgecolors="black")
```

```{code-cell} ipython3
---
tags: [hide-input]
---
import textwrap
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    # Begin: the code of the block above, unchanged.
    fig, ax = plt.subplots(layout="constrained")
    td = TernaryDiagram(materials, ax=ax)
    heatmap = td.tripcolor(compositions, values)
    points = td.scatter(compositions, z=values, edgecolors="black")
    # End
plt.close("all")
for w in caught:
    text = f"{w.category.__name__}: {w.message}"
    # Wrap at spaces only, so the text of the warning is unchanged.
    print(
        textwrap.fill(
            text, 79, break_long_words=False, break_on_hyphens=False
        )
    )
```

To keep the current behavior, pass `colorbar=True` to the second plot, which adds a second colorbar on purpose:

```{code-cell} ipython3
---
mystnb:
  image:
    alt: A ternary diagram of Li2O, La2O3 and TiO2 whose inside, within the polygon enclosing 40 compositions, is painted in triangles in the rainbow colormap by the made-up property, with the 40 compositions drawn on top as points with black outlines in the same colors. Two identical colorbars from about 0 to 1 stand side by side on the right.
---
fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(materials, ax=ax)
heatmap = td.tripcolor(compositions, values)
points = td.scatter(
    compositions, z=values, edgecolors="black", colorbar=True
)
```

To adopt the new behavior now, pass `colorbar=False`, and the plots share the colorbar that is already there:

```{code-cell} ipython3
---
mystnb:
  image:
    alt: The same ternary diagram of Li2O, La2O3 and TiO2 with the triangles painted in the rainbow colormap and the 40 points with black outlines on top, and a single colorbar from about 0 to 1 on the right.
---
fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(materials, ax=ax)
heatmap = td.tripcolor(compositions, values)
points = td.scatter(
    compositions, z=values, edgecolors="black", colorbar=False
)
```

The plots here use the same values, so they have the same color range.
When plots with different values share a colorbar, give them the same `z_min`, `z_max` and `cmap`, as shown in {ref}`Adding a colorbar yourself <layout-and-colorbars-adding-a-colorbar>`.

(migration-v4-flag-cbar)=
## `flag_cbar` is renamed to `colorbar`

The argument `flag_cbar` of `scatter` and `contour` is renamed to `colorbar` and will be removed in 4.0.0.
Every call that passes `flag_cbar` emits this warning, whatever its value.

Code that emits the warning:

```python
fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(materials, ax=ax)
points = td.scatter(compositions, z=values, flag_cbar=False)
```

```{code-cell} ipython3
---
tags: [hide-input]
---
import textwrap
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    # Begin: the code of the block above, unchanged.
    fig, ax = plt.subplots(layout="constrained")
    td = TernaryDiagram(materials, ax=ax)
    points = td.scatter(compositions, z=values, flag_cbar=False)
    # End
plt.close("all")
for w in caught:
    text = f"{w.category.__name__}: {w.message}"
    # Wrap at spaces only, so the text of the warning is unchanged.
    print(
        textwrap.fill(
            text, 79, break_long_words=False, break_on_hyphens=False
        )
    )
```

Replace `flag_cbar` with `colorbar` and keep the value.
The code below works the same in v3.x and v4.0.0:

```{code-cell} ipython3
---
mystnb:
  image:
    alt: A ternary diagram of Li2O, La2O3 and TiO2 with 40 points colored in the rainbow colormap by the made-up property, red near 50 % Li2O, 30 % La2O3 and 20 % TiO2 and blue to purple farther from it, and no colorbar.
---
fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(materials, ax=ax)
points = td.scatter(compositions, z=values, colorbar=False)
```

`flag_cbar` is read as true or false, but `colorbar` accepts only `None`, `True` and `False` and raises a `TypeError` for other values, so write `flag_cbar=0` as `colorbar=False` and `flag_cbar=1` as `colorbar=True`.
Passing both `flag_cbar` and `colorbar` raises a `ValueError`.
Code that passed `flag_cbar` by position, as the 6th argument of `scatter` or `contour`, now passes `colorbar`, and the same rule applies to it; there, `None` now means that `colorbar` is not specified, so a colorbar is added when `z` is given.

The new drawing methods do not accept `flag_cbar`.
{py:meth}`~ternary_diagram.TernaryDiagram.tripcolor` and {py:meth}`~ternary_diagram.TernaryDiagram.heatmapf` raise a `TypeError` that names `colorbar` instead:

```{code-cell} ipython3
fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(materials, ax=ax)
try:
    heatmap = td.heatmapf(property_value, flag_cbar=False)
except TypeError as error:
    print(f"TypeError: {error}")
plt.close(fig)  # heatmapf drew nothing, so the figure is not shown.
```

{py:meth}`~ternary_diagram.TernaryDiagram.fill` and {py:meth}`~ternary_diagram.TernaryDiagram.text` never add a colorbar and have neither argument.
They pass their keyword arguments to matplotlib, which raises an `AttributeError` for `flag_cbar` as for any unknown property.

(migration-v4-annotations)=
## Annotation formatting warning

{py:meth}`~ternary_diagram.TernaryDiagram.annotate` and `scatter` with `annotations` emit this warning when they are called without `auto_latex_notation` and a text would be shown differently in v4.0.0.
In v3.x, they write every number in the text as a subscript; in v4.0.0, they will follow `auto_latex_notation` of `TernaryDiagram`, as {py:meth}`~ternary_diagram.TernaryDiagram.text` does, and format only the words that look like chemical formulas.
So the warning is emitted for a text with numbers that are not part of a chemical formula, such as `"Sample 1"`, for formulas joined without spaces, such as `"Li2O-La2O3"`, and for a chemical formula with numbers, such as `"Li2O"`, on a diagram created with `auto_latex_notation=False`.
A text that contains `$` (mathtext) is shown as it is, without the warning.
The warning names only the first text that changes on each diagram, so check the other texts too.

Code that emits the warning:

```python
fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(materials, ax=ax)
note = td.annotate("Sample 1", [0.4, 0.3, 0.3])
```

```{code-cell} ipython3
---
tags: [hide-input]
---
import textwrap
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    # Begin: the code of the block above, unchanged.
    fig, ax = plt.subplots(layout="constrained")
    td = TernaryDiagram(materials, ax=ax)
    note = td.annotate("Sample 1", [0.4, 0.3, 0.3])
    # End
plt.close("all")
for w in caught:
    text = f"{w.category.__name__}: {w.message}"
    # Wrap at spaces only, so the text of the warning is unchanged.
    print(
        textwrap.fill(
            text, 79, break_long_words=False, break_on_hyphens=False
        )
    )
```

To keep the current behavior, format the text with {py:func}`~ternary_diagram.utils.get_label`, which writes every number as a subscript, and pass `auto_latex_notation=False` so that it is shown as it is:

```{code-cell} ipython3
---
mystnb:
  image:
    alt: A ternary diagram of Li2O, La2O3 and TiO2 with the annotation Sample 1 in the middle of the triangle, where the number 1 is a subscript.
---
fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(materials, ax=ax)
note = td.annotate(
    get_label("Sample 1"), [0.4, 0.3, 0.3], auto_latex_notation=False
)
```

To adopt the new behavior now, pass `auto_latex_notation=True` to format only the chemical formulas, or `auto_latex_notation=False` to show the text as it is.
With `True`, `"Sample 1"` is shown as it is and the `2` of `"LiF + Li2O"` is a subscript:

```{code-cell} ipython3
---
mystnb:
  image:
    alt: A ternary diagram of Li2O, La2O3 and TiO2 with two annotations. In the middle of the triangle, the annotation Sample 1 is in plain text. In the upper part, the annotation LiF + Li2O has the number 2 as a subscript.
---
fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(materials, ax=ax)
note = td.annotate("Sample 1", [0.4, 0.3, 0.3], auto_latex_notation=True)
formula = td.annotate(
    "LiF + Li2O", [0.65, 0.2, 0.15], auto_latex_notation=True
)
```

For `scatter`, the same applies to the texts given by `annotations`: pass `[get_label(text) for text in texts]` with `auto_latex_notation=False` to keep the current behavior, or pass `auto_latex_notation=True` or `False` to adopt the new one.
{ref}`Chemical formula labels <getting-started-formula-labels>` in Getting started explains which words count as chemical formulas.

(migration-v4-finding)=
## Finding affected code

Since the warnings about the defaults are emitted only once per diagram, and Python shows a warning from the same line of code only once by default, the warnings that you see may not show every call that needs a change.
Turn `FutureWarning` into an error, so that the first affected call stops the run with a traceback that points at it, fix that call, and run again until no error is raised.

To run a script:

```bash
python -W error::FutureWarning your_script.py
```

To run a test suite with pytest:

```bash
pytest -W error::FutureWarning
```

In a notebook, run this at the top, before the cells that draw:

```python
import warnings

warnings.simplefilter("error", FutureWarning)
```

These settings also turn the `FutureWarning` of other libraries into errors, which shows what else your code needs to update.

## See also

- The [changelog](https://github.com/yu9824/ternary-diagram/blob/main/CHANGELOG.md) lists all the changes of each version.
- [Layout and colorbars](layout_and_colorbars.md) explains the automatic layout and the automatic colorbars, and how to control them.
