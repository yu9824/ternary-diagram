# Project Structure

## Organization Philosophy

小規模な単一パッケージのライブラリ。src レイアウトを採り、公開 API はクラス 1 つに絞り、実装はプライベートモジュールに置く。中身は「公開ファサード（`TernaryDiagram`）→ 描画種別ごとの Plotter → 状態を持たないユーティリティ関数」の 3 層構造。

## Directory Patterns

### Package Source
**Location**: `src/ternary_diagram/`
**Purpose**: ライブラリ本体。`__init__.py` はメタデータ（`__version__` など）と公開 API の re-export だけを持つ
**Example**: `_api.py` に `TernaryDiagram` と `_XxxPlotter` 群、`utils.py` に入力検証・座標変換・化学式整形の純粋関数

### Tests
**Location**: `tests/`
**Purpose**: pytest のテスト。`test_<描画種別>.py` という命名。`_` で始まるファイルは収集対象外の旧コード。まだ書いていないテストは `tests/TODO.md` に記録する
**Example**: `test_scatter.py`, `test_mono_scatter.py`

### Examples
**Location**: `example/<use_case>/`
**Purpose**: ユースケースごとにディレクトリを作り、Notebook・入力 CSV・出力 PNG を同じ場所に置く。README とテストはこの CSV / PNG を GitHub raw URL で参照する
**Example**: `example/contour/example_contour.{ipynb,csv,png}`

### Documentation
**Location**: `docs_src/`
**Purpose**: Sphinx の設定と手書きページのみ。API リファレンスは CI で sphinx-apidoc が生成する

## Naming Conventions

- **配布名 / import 名**: `ternary-diagram`（ハイフン）/ `ternary_diagram`（アンダースコア）
- **Modules**: snake_case。プライベート実装は `_` 接頭辞（`_api.py`）
- **Classes**: PascalCase。内部クラスは `_` 接頭辞（`_BasePlotter`, `_ContourPlotter`）
- **Functions / methods**: snake_case。入力検証は `check_*`、変換は `three2two` のように内容をそのまま表す名前
- **Constants**: UPPER_SNAKE_CASE。モジュールレベルのデフォルトは `DEFAULT_*`。関数内のローカル定数も大文字（`ROOT3_OVER_2`, `N_LEVELS`）
- **派生属性**: scikit-learn 風に末尾 `_`（`x_`, `y_`, `collection_`）
- **読み取り専用属性**: name mangling（`self.__ax`）+ `@property`。setter は `AttributeError` を送出する

## Import Organization

```python
# Python 3.8 互換のための typing（isort の対象外としてファイル先頭に固定）
from typing import Tuple, List  # isort: skip

# 標準ライブラリ
from math import sqrt
from typing import Optional

# サードパーティ（matplotlib はサブモジュールを明示的に import する）
import matplotlib.axes
import numpy as np
from numpy.typing import ArrayLike

# パッケージ内は絶対 import
from ternary_diagram.utils import check_2d_vector, three2two
```

- パッケージ内の参照は絶対 import（`from ternary_diagram.utils import ...`）。`__init__.py` の re-export だけは相対 import（`from ._api import TernaryDiagram`）
- 公開シンボルは `__all__` で明示する

## Code Organization Principles

### Plotter パターン（描画種別を追加するとき）

`TernaryDiagram` の描画メソッドは、対応する `_BasePlotter` サブクラスを生成し、座標を記録して、matplotlib のオブジェクトを返すだけにする。

```python
class _NewPlotter(_BasePlotter):
    def __init__(self, vector, ax=None, **kwargs):
        super().__init__(vector, ax=ax, **kwargs)  # 検証・正規化・3D→2D 変換
        self._set_default_params(zorder=DEFAULT_ZORDER_PLOTS)  # ユーザー指定が優先
        self.collection_ = self.ax.some_mpl_func(self.x_, self.y_, **self.kwargs)
        self.fig.tight_layout()

    @property
    def name(self):
        return "new"


# TernaryDiagram 側
def new(self, vector: ArrayLike, **kwargs):
    plotter = _NewPlotter(vector=vector, ax=self.ax, **kwargs)
    self._append_x_y(plotter)  # plotter.name ごとに x_ / y_ を記録
    return plotter.collection_  # matplotlib のネイティブオブジェクト
```

### 座標と入力の規約

- 頂点の順序は「上 → 左下 → 右下」（反時計回り）。`materials` の並びと `vector` の列の並びは一致させる
- `vector` は shape `(n, 3)` の ArrayLike。1 点だけを受ける API（`annotate`）は `check_1d_vector` で `(1, 3)` に揃える
- 3 成分から 2 次元座標への変換は `utils.three2two` に一元化する
- `ax` を受け取る処理はすべて `check_ax` を通す。未指定なら `plt.gca()`
- `z`（物性値）を伴う描画は `flag_cbar=True` のとき colorbar を自動で付け、共通実装の `_BasePlotter.colorbar` を使う

### Comments

- docstring は英語で統一。行コメントは日本語・英語・`日本語 (English)` 併記が混在しており、周囲のスタイルに合わせる

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_
