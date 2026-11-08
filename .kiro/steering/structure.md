# Project Structure

## Organization Philosophy

小規模な単一パッケージのライブラリ。src レイアウトを採り、公開 API はクラス 1 つに絞り、実装はプライベートモジュールに置く。中身は「公開ファサード（`TernaryDiagram`）→ 描画種別ごとの Plotter → 状態を持たないユーティリティ関数」の 3 層構造。

## Directory Patterns

### Package Source
**Location**: `src/ternary_diagram/`
**Purpose**: ライブラリ本体。`__init__.py` はメタデータ（`__version__` など）と公開 API の re-export だけを持つ
**Example**: `_api.py` に `TernaryDiagram` と `_XxxPlotter` 群、`utils.py` に入力検証・座標変換・化学式整形の純粋関数、`__main__.py` に CLI（`ternary-diagram --version`）、型情報の公開用に `py.typed`。土台の 5 つの部品と、それを束ねる集約は `_skeleton.py`、描画後のレイアウトとカラーバーの判定・三角図ごとの状態は `_post_draw.py`、利用者向けの警告の入口と非推奨の文面は `_deprecation.py`（どちらもパッケージ内の葉に近いモジュールで、`_api.py` から使う）

### Tests
**Location**: `tests/`
**Purpose**: pytest のテスト。テスト対象ごとに `test_<対象>.py`（描画メソッド単位、`utils`、三角図の土台、CLI、private モジュールの単体テスト）。`TernaryDiagram` 経由の副作用（レイアウト・カラーバー・警告）の結合テストは `test_side_effects.py`、公開 API の docstring の例は共通ランナー `test_doctests.py` が実行する。共通 fixture は `conftest.py` に置く。複数のテストファイルで共有する期待値の計算は `test_` の付かない `_` 接頭辞のモジュール（`_skeleton_expected.py`）に置く
**Example**: `test_scatter.py`, `test_contour.py`, `test_utils.py`, `test_ternary_diagram.py`, `test_post_draw.py`, `test_side_effects.py`, `test_skeleton_parts.py`（部品と集約の単体）/ `test_skeleton.py`（公開 API 経由）

### Examples
**Location**: `example/<use_case>/`
**Purpose**: ユースケースごとにディレクトリを作り、Notebook・入力 CSV・出力 PNG を同じ場所に置く。README は PNG を GitHub raw URL で、テストは CSV をリポジトリ内のパスで参照する。Notebook は先頭セルを H1 タイトルにする（ドキュメントのページタイトルになる）
**Example**: `example/contour/example_contour.{ipynb,csv,png}`

### Documentation
**Location**: `docs_src/`
**Purpose**: Sphinx の設定と手書きページ（MyST Markdown）のみ。API リファレンスは CI で sphinx-apidoc が生成する
- `tutorials/` は `example/` の Notebook へのシンボリックリンク。Notebook を追加したらリンクと `tutorials/index.md` の toctree に足す
- `_templates/layout.html` はフッターに広告スクリプトを差し込んでいる。テーマを変えるときは、ビルド結果に残っているか確認する

### Release Docs
**Location**: リポジトリ直下
**Purpose**: `HOW_TO_RELEASE.md`（メンテナ向けのリリース手順）、`CHANGELOG.md`（利用者向けの変更点）

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
# Python 3.8 時代の名残の typing（isort の対象外としてファイル先頭に固定）
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

`TernaryDiagram` の描画メソッドは、対応する `_BasePlotter` サブクラスを生成し、座標を記録して、matplotlib のオブジェクトを返すだけにする。描画後のレイアウト調整とカラーバーの追加は Plotter が直接行わず、`__init__` の最後で `self._post_draw(...)` をちょうど 1 回呼んで任せる（既存のレイアウトエンジンの尊重、カラーバーの重複判定、FutureWarning の 1 回化はそこで行う）。

```python
class _NewPlotter(_BasePlotter):
    def __init__(self, vector, ax=None, *, post_draw_context, **kwargs):
        super().__init__(  # 検証・正規化・3D→2D 変換
            vector, ax=ax, post_draw_context=post_draw_context, **kwargs
        )
        self._set_default_params(zorder=DEFAULT_ZORDER_PLOTS)  # ユーザー指定が優先
        self.collection_ = self.ax.some_mpl_func(self.x_, self.y_, **self.kwargs)
        # 値で色付けした描画なら mappable と colorbar（None/True/False）を渡す
        self._post_draw()

    @property
    def name(self):
        return "new"


# TernaryDiagram 側
def new(self, vector: ArrayLike, **kwargs):
    plotter = _NewPlotter(
        vector=vector,
        ax=self.ax,
        post_draw_context=self.__post_draw_context,  # 三角図ごとの状態
        **kwargs,
    )
    self._append_x_y(plotter)  # plotter.name ごとに x_ / y_ を記録
    return plotter.collection_  # matplotlib のネイティブオブジェクト
```

### 土台の部品パターン（三角図の土台に部品を足すとき）

土台の部品は `_skeleton._SkeletonPart` のサブクラスにし、既定値・検証・図形の仕様の計算だけを持たせる。更新の手順、巻き戻し、プロパティ名の照合は基底が受け持つ。

```python
class _NewPart(_SkeletonPart):
    OPTION_DEFAULTS = {"visible": True, "step": 0.1}  # 名前付きの項目
    STYLE_DEFAULTS = {"color": "black"}  # matplotlib のプロパティ
    ARTIST_CLASS = matplotlib.lines.Line2D

    def _validate(self, options):  # visible 以外の項目を検証して返す
        ...

    def _specs(self, options, style):  # Axes を変えずに _LineSpec / _TextSpec を返す
        ...
```

- `_Skeleton` に部品を登録し（`PartName` に名前を足す）、`TernaryDiagram` に `set_<part>`・`<part>_kw`・取り出し口 `<part>_` をそろえて足す。`<part>_kw` は作成直後に `set_<part>(**<part>_kw)` を呼ぶのと同じ意味にする
- 配置の計算（目盛りの値、辺上の点、線分）は図を使わない純粋関数として `utils` に置き、部品から呼ぶ

### 座標と入力の規約

- 頂点の順序は「上 → 左下 → 右下」（反時計回り）。`materials` の並びと `vector` の列の並びは一致させる
- `vector` は shape `(n, 3)` の ArrayLike。1 点だけを受ける API（`annotate`）は `check_1d_vector` で `(1, 3)` に揃える
- 3 成分から 2 次元座標への変換は `utils.three2two` に一元化する
- `ax` を受け取る処理はすべて `check_ax` を通す。未指定なら `plt.gca()`
- 値で色付けした描画は `colorbar=None|True|False` を受け、真偽値は `utils.check_optional_bool` / `check_bool` で厳密に検証する（`0`/`1` は `TypeError`）。カラーバーの追加は `_post_draw` が決定表で判断する
- 内部で matplotlib に渡す引数とユーザーの kwargs が衝突しうるときは、`_merge_alias` で別名を統合するか、`self.kwargs.pop(...)` でユーザー指定を取り出して優先する。kwargs をそのまま `**self.kwargs` で重ねて渡さない

### Comments

- docstring は英語で統一。行コメントは日本語・英語・`日本語 (English)` 併記が混在しており、周囲のスタイルに合わせる

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_

_updated_at: 2026-10-20 — Python 3.9+, setuptools-scm, offline test suite, MyST-NB docs への移行を反映_
_updated_at: 2026-10-24 — plot-side-effects（描画後処理の共通化、`_post_draw.py` / `_deprecation.py`、共通 doctest ランナー）を反映_
_updated_at: 2026-11-08 — diagram-customization（土台の部品化 `_skeleton.py`、`set_*` / `*_kw` / 取り出し口）を反映_
