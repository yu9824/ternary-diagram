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

# Drawing phase diagrams

This page shows how to shade phase regions given by their vertex compositions, label them with text placed exactly at a composition, and control how the regions overlap with the grid and the other plots.

The phase diagram on this page is made up for illustration.
Its vertices are real compounds, but the regions, their boundaries and the phase names are fictitious and are not the measured phase diagram of the Li2O–La2O3–TiO2 system.

```{code-cell} ipython3
import matplotlib.pyplot as plt
import numpy as np

from ternary_diagram import TernaryDiagram
from ternary_diagram.utils import to_latex_notation
```

(phase-diagrams-filling)=
## Filling phase regions

{py:meth}`~ternary_diagram.TernaryDiagram.fill` fills a polygon whose vertices are given as compositions, one row per vertex, in the same order of the components as the materials.
As for the other methods, the rows do not have to sum to 1.
Pass `label` to show the region in the legend, and call `td.ax.legend()` after drawing the regions.

```{code-cell} ipython3
---
mystnb:
  image:
    alt: A ternary diagram of Li2O, La2O3 and TiO2 divided into three filled regions that meet at a point inside the triangle. The top region near Li2O is blue, the bottom left region near La2O3 is orange, and the bottom right region near TiO2 is green. A legend in the upper left corner lists the blue region as Liquid, the orange region as La2O3 ss and the green region as TiO2 + Li2TiO3.
---
regions = {
    "Liquid": [[1, 0, 0], [0.6, 0.4, 0], [0.3, 0.3, 0.4], [0.45, 0, 0.55]],
    "La2O3 ss": [[0, 1, 0], [0, 0.45, 0.55], [0.3, 0.3, 0.4], [0.6, 0.4, 0]],
    "TiO2 + Li2TiO3": [
        [0, 0, 1],
        [0.45, 0, 0.55],
        [0.3, 0.3, 0.4],
        [0, 0.45, 0.55],
    ],
}

fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
for name, vertices in regions.items():
    polygons = td.fill(vertices, label=to_latex_notation(name))
legend = td.ax.legend(loc="upper left")
```

`fill` returns a list of one `matplotlib.patches.Polygon`, as `Axes.fill` does, and passes its keyword arguments, such as `facecolor`, `edgecolor`, `alpha` or `hatch`, to matplotlib.
Without a color, each call takes the next color of matplotlib's color cycle, so the regions get different colors.
A polygon needs at least 3 vertices; fewer raise a `ValueError`.

The legend shows the labels as they are given.
Here {py:func}`~ternary_diagram.utils.to_latex_notation` writes the numbers of the chemical formulas in the labels as subscripts, like the vertex labels: `"La2O3 ss"` becomes `"La$_{2}$O$_{3}$ ss"`.

(phase-diagrams-vertex-order)=
## Vertex order

`fill` joins the vertices in the order given and closes the polygon from the last vertex back to the first.
It does not sort the vertices or compute their convex hull, so give them in order along the boundary of the region, clockwise or counterclockwise.
In the next figure, the same four vertices, marked with black points, are given in two orders, and the number next to each vertex shows its position in the list passed to `fill`.
On the right, the second and the third vertices trade places, and following the numbers makes the boundary cross itself.

```{code-cell} ipython3
---
mystnb:
  image:
    alt: Two ternary diagrams of Li2O, La2O3 and TiO2 side by side, each with a translucent blue region drawn from the same four vertices, marked with black points, and a number from 1 to 4 next to each vertex for its position in the given order. Vertex 1 is the Li2O vertex and vertex 4 is on the right edge in both diagrams. On the left, titled In order along the boundary, vertex 2 is on the left edge and vertex 3 is inside the triangle, and joining 1, 2, 3 and 4 gives a four-sided region near the Li2O vertex. On the right, titled Second and third swapped, vertices 2 and 3 trade places, so vertex 2 is inside the triangle and vertex 3 is on the left edge, and joining 1, 2, 3 and 4 makes the boundary cross itself into two triangles that touch at one point.
---
vertices = regions["Liquid"]
orders = {
    "In order along the boundary": [0, 1, 2, 3],
    "Second and third swapped": [0, 2, 1, 3],
}

# put each number a little inside the region, next to its vertex
center = np.mean(vertices, axis=0)
number_positions = [0.75 * np.array(v) + 0.25 * center for v in vertices]

fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), layout="constrained")
for ax, (title, order) in zip(axes, orders.items()):
    td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
    polygons = td.fill([vertices[i] for i in order], alpha=0.6)
    points = td.scatter(vertices, color="black", s=15)
    for number, i in enumerate(order, start=1):
        label = td.text(str(number), number_positions[i], fontweight="bold")
    ax_title = ax.set_title(title, pad=24)
```

(phase-diagrams-labeling)=
## Labeling regions

{py:meth}`~ternary_diagram.TernaryDiagram.text` places a text so that its center is exactly at a composition, which makes it easy to put the name of a phase inside its region.
The keyword arguments are properties of `matplotlib.text.Text`, such as `fontsize` or `color`, and `ha` / `va` change the alignment.

`text` formats the chemical formulas in the text with the same rule as {py:func}`~ternary_diagram.utils.to_latex_notation`: only the words separated by white space that look like chemical formulas get subscripts, and a text that contains `$` (matplotlib's math text) is shown as it is.
Here each region is labeled with the same name as its legend entry, a line break keeps the longest name inside its region, and a white box behind each label keeps it readable over the colors.

```{code-cell} ipython3
---
mystnb:
  image:
    alt: The same three filled regions on a ternary diagram of Li2O, La2O3 and TiO2, with the legend in the upper left corner and a text label inside each region. The blue top region is labeled Liquid, the orange bottom left region is labeled La2O3 ss, and the green bottom right region is labeled TiO2 + Li2TiO3 on two lines, with the numbers of the formulas as subscripts. Each label is on a translucent white box.
---
label_positions = {
    "Liquid": [0.7, 0.15, 0.15],
    "La2O3 ss": [0.15, 0.65, 0.2],
    "TiO2 + Li2TiO3": [0.15, 0.2, 0.65],
}

fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
labels = {}
for name, vertices in regions.items():
    polygons = td.fill(vertices, label=to_latex_notation(name))
    text = name.replace(" + ", " +\n")
    labels[name] = td.text(
        text,
        label_positions[name],
        fontsize=11,
        bbox={"boxstyle": "round", "fc": "white", "ec": "none", "alpha": 0.8},
    )
legend = td.ax.legend(loc="upper left")
```

The texts of the labels show the formatting; `"Liquid"` and `"ss"` do not look like chemical formulas and stay as they are, and the line break is kept:

```{code-cell} ipython3
for label in labels.values():
    print(repr(label.get_text()))
```

`auto_latex_notation` of `text` decides whether the formulas are formatted.
With `None` (the default), `text` follows `auto_latex_notation` of {py:class}`~ternary_diagram.TernaryDiagram`, the setting chosen when the diagram was created (`True` unless changed, the same setting as the vertex labels).
Pass `auto_latex_notation=False` to show a text as it is in one call, for example a sample name such as `"S1"`, which looks like a formula of sulfur.
`True` formats the text of one call on a diagram created with `auto_latex_notation=False`.

```{code-cell} ipython3
---
mystnb:
  image:
    alt: A ternary diagram of Li2O, La2O3 and TiO2 with two black points, each with a text just above it. The text above the left point reads S2 with the 2 as a subscript, like a chemical formula. The text above the right point reads S1 as typed, with the 1 on the baseline.
---
samples = [[0.3, 0.45, 0.25], [0.3, 0.2, 0.5]]

fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
points = td.scatter(samples, color="black")
formatted = td.text("S2", samples[0], va="bottom")
as_typed = td.text("S1", samples[1], va="bottom", auto_latex_notation=False)
print(formatted.get_text(), as_typed.get_text())
```

`va="bottom"` puts the bottom of each text at its composition, just above the point, instead of the center.
For the formatting of the vertex labels and of {py:meth}`~ternary_diagram.TernaryDiagram.annotate`, see {ref}`Chemical formula labels <getting-started-formula-labels>` in Getting started.

(phase-diagrams-layering)=
## Layering and transparency

Each method draws with a default `zorder`, so the layers stay in the same order whatever order you call the methods in.
A larger `zorder` is drawn in front; artists with the same `zorder` are drawn in the order they were added.

| Layer | Drawn by | Default `zorder` |
|---|---|---|
| Heatmaps | {py:meth}`~ternary_diagram.TernaryDiagram.tripcolor`, {py:meth}`~ternary_diagram.TernaryDiagram.heatmapf` | -1 |
| Contour maps | {py:meth}`~ternary_diagram.TernaryDiagram.contour` | 0 |
| Phase regions | {py:meth}`~ternary_diagram.TernaryDiagram.fill` | 0.5 |
| Grid and border | the diagram ({py:meth}`~ternary_diagram.TernaryDiagram.set_grid`, {py:meth}`~ternary_diagram.TernaryDiagram.set_border`) | 1 |
| Lines, such as tie lines | {py:meth}`~ternary_diagram.TernaryDiagram.plot` | 2 |
| Points | {py:meth}`~ternary_diagram.TernaryDiagram.scatter` | 3 |
| Annotations, tick labels, axis titles and vertex labels | {py:meth}`~ternary_diagram.TernaryDiagram.annotate` and the diagram | 3 (matplotlib's default for texts) |
| Texts | {py:meth}`~ternary_diagram.TernaryDiagram.text` | 4 |

So by default a phase region covers a contour map but stays behind the grid, the tie lines, the points and the labels.
A region is opaque by default and hides what is behind it.
Pass `alpha` to make it translucent and `zorder` to move it to another layer.

In the next figure, the left diagram uses the defaults: the grid and the points are drawn over the region.
On the right, `zorder=3.5` moves the region in front of the grid and the points, and `alpha=0.5` keeps them visible through it; the text, with `zorder` 4, stays in front of the region.

```{code-cell} ipython3
---
mystnb:
  image:
    alt: Two ternary diagrams of Li2O, La2O3 and TiO2 side by side, each with the same blue region near the Li2O vertex labeled Liquid and the same 30 black points scattered over the triangle. On the left, titled Defaults, the region is opaque and the grid lines and the points are drawn over it. On the right, titled alpha=0.5, zorder=3.5, the translucent region is drawn over the grid lines and the points, which show through it tinted by the region, and the label Liquid is drawn over the region.
---
rng = np.random.default_rng(0)
measured = rng.dirichlet([2, 2, 2], size=30)
styles = {
    "Defaults": {},
    "alpha=0.5, zorder=3.5": {"alpha": 0.5, "zorder": 3.5},
}

fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), layout="constrained")
for ax, (title, style) in zip(axes, styles.items()):
    td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
    polygons = td.fill(regions["Liquid"], **style)
    points = td.scatter(measured, color="black", s=15)
    label = td.text("Liquid", label_positions["Liquid"], fontsize=11)
    ax_title = ax.set_title(title, pad=24)
```

Regions are drawn over a contour map by default; give them an `alpha` so that the contours show through.
A `zorder` below 0, such as `zorder=-0.5`, puts a region behind the contours, which helps only with contour lines (`contour(..., fill=False)`) or translucent filled contours, because opaque filled contours hide the region.

(phase-diagrams-not-by-color)=
## Not by color alone

Colors alone do not tell the regions apart for every reader: some readers do not see the difference between some colors, and the colors are lost when the figure is printed in grayscale.
The diagram in [Labeling regions](#phase-diagrams-labeling) therefore names each region twice, in the legend and with a text label inside the region, so it can be read without the colors.

Hatching gives each region a pattern in addition, and works even without colors.
`hatch` is a property of the polygon; the patterns are drawn in the `edgecolor`.

```{code-cell} ipython3
---
mystnb:
  image:
    alt: The same three regions on a ternary diagram of Li2O, La2O3 and TiO2, drawn in black and white with different hatch patterns and a text label in each region. The top region, labeled Liquid, has diagonal lines; the bottom left region, labeled La2O3 ss, has dots; and the bottom right region, labeled TiO2 + Li2TiO3, has crossed lines. A legend in the upper left corner shows the three patterns with the same names.
---
hatches = {"Liquid": "///", "La2O3 ss": "..", "TiO2 + Li2TiO3": "xx"}

fig, ax = plt.subplots(layout="constrained")
td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
for name, vertices in regions.items():
    polygons = td.fill(
        vertices,
        label=to_latex_notation(name),
        facecolor="white",
        edgecolor="0.4",
        hatch=hatches[name],
    )
    text = name.replace(" + ", " +\n")
    label = td.text(
        text,
        label_positions[name],
        fontsize=11,
        bbox={"boxstyle": "round", "fc": "white", "ec": "none"},
    )
legend = td.ax.legend(loc="upper left")
```

The white box behind each text label keeps it readable over the pattern.

(phase-diagrams-contour-fill)=
## `contour(fill=...)` vs `fill()`

```{note}
The `fill` argument of {py:meth}`~ternary_diagram.TernaryDiagram.contour` and the {py:meth}`~ternary_diagram.TernaryDiagram.fill` method are unrelated.
`contour(vector, z, fill=True)` (the default) fills the areas between the contour levels of values `z` interpolated between compositions, and `fill=False` draws only the contour lines.
`fill(vector)` fills one polygon whose vertices are the compositions in `vector`, with no values and no interpolation.
Use `fill()` for phase regions and `contour` for maps of a value; see [Heatmaps and contour maps](heatmaps_and_contours.md).
```

## See also

- [Getting started](getting_started.md) explains how to pass compositions and how the chemical formulas of the labels are formatted.
- [Customizing the diagram](customizing.md) explains how to change the grid, the border and the labels that the regions are drawn with.
- [Heatmaps and contour maps](heatmaps_and_contours.md) explains how to draw values that vary with the composition.
