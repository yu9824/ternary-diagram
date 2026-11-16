# Tutorials

Step-by-step examples of `ternary_diagram`.
The notebooks and their data live in the
[example](https://github.com/yu9824/ternary-diagram/tree/main/example) folder.
For explanations organized by goal, see the [User guide](../user_guide/index.md).

- {doc}`Quick start <quickstart>`: the minimal example of the README, with a colored scatter plot and a line.
- {doc}`Scatter plot colored by values <scatter>`: compositions read from a CSV file, colored by a measured value.
- {doc}`Scatter plot with annotations <scatter_with_annotations>`: a composition computed from chemical formulas with `element_recognition`, labeled with its formula.
- {doc}`Scatter plot and tie lines <mono_scatter>`: points in a single color, then two groups of points and a tie line with a legend.
- {doc}`Contour map <contour>`: filled and line contours of a value over the compositions.
- {doc}`Multiple diagrams in one figure <multiple_figure>`: two diagrams side by side with `layout="constrained"`.

```{toctree}
:maxdepth: 1

quickstart
scatter
scatter_with_annotations
mono_scatter
contour
multiple_figure
```
