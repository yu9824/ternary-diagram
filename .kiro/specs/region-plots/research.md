# Research & Design Decisions: region-plots

## Summary
- **Feature**: `region-plots`
- **Discovery Scope**: Extension（既存の Plotter パターンに 2 つの描画メソッドを足す。light discovery）
- **Key Findings**:
  - `Axes.fill(x, y, **kwargs)` は長さ 1 の `list[Polygon]` を返し、閉じた多角形・`label` による凡例・塗りつぶし専用の色の順番（線の色の順番とは別）をそのまま提供する。自前で `Polygon` を組み立てる必要はない
  - `Axes.text` は、既定値として内部で入れた正式名（`horizontalalignment`）と利用者の別名（`ha`）が同時にあると、matplotlib の内部の順序で一方が黙って勝つ。`fontdict` よりキーワード引数が優先される。既定値は「正式名・別名のどちらも、キーワード引数と `fontdict` のどちらにもないとき」だけ入れる必要がある
  - `plot-side-effects` の設計により、新しい Plotter は `post_draw_context` を必須のキーワード専用引数で受け、`__init__` の最後で `self._post_draw(...)` を 1 回呼ぶだけで、レイアウト・カラーバー・警告の規則に従える。`fill` / `text` は値で色付けしないので、引数なしの `_post_draw()` で足りる
  - cross-spec review（roadmap「横断の取り決め」）により、`text` の `auto_latex_notation` は呼び出しごとの `None` で三角図単位の設定を引き継ぐ形にそろえ、検証は `plot-side-effects` の `utils.check_optional_bool` を使う。docstring の例は tech.md「Docstring Examples」に従い、共通 doctest ランナー（`tests/test_doctests.py`）で実行する。CHANGELOG は `plot-side-effects` がそろえた見出しの「New features」に書く
  - cross-spec review の 2 回目で、docstring の例のブロックはどれも `import matplotlib.pyplot as plt` と `from ternary_diagram import TernaryDiagram` の行から始めることにした（ランナーの名前空間は `_api.py` の globals で、`_api.py` は `pyplot` を import しないため）。三角図単位の設定の保持先は roadmap の取り決めどおり `TernaryDiagram.__auto_latex_notation` とし、最初に必要になった側が足す

## Research Log

### 既存の Plotter パターンと拡張点
- **Context**: `fill` / `text` をどこにどう足すか
- **Sources Consulted**: `src/ternary_diagram/_api.py`、`src/ternary_diagram/utils.py`、`tests/test_annotate.py`、`tests/test_plot.py`、`.kiro/steering/structure.md`
- **Findings**:
  - `TernaryDiagram` の描画メソッドは Plotter を作り、`_append_x_y(plotter)` で `plotter.name` ごとに `x_` / `y_` を記録し、`plotter.collection_` を返すだけ
  - `_BasePlotter.__init__` が `check_2d_vector`（shape `(n, 3)` の検証と行ごとの正規化）、`check_ax`、`three2two` を行う。1 点だけを受ける `annotate` は事前に `check_1d_vector(vector, scale=False)` で `(1, 3)` にそろえる。`check_1d_vector` は `(3,)` と `(1, 3)` を受け、それ以外の要素数で `` "`vector`'s length must be 3." `` を送出する
  - 既定値の注入は `_set_default_params`（キーの有無だけを見る）。zorder 定数は `DEFAULT_ZORDER_CONTOUR = 0`、`GRIDS = 1`、`PLOTS = 2`、`SCATTER = 3`
  - Plotter 固有の入力規則（`contour` の `z` 必須、`scatter` の `annotations` の長さ）は Plotter の中で `ValueError` にしている
  - `_AnnotatePlotter` は `get_label` の `ValueError`（文字列以外）を `try/except` で無視している
- **Implications**: `_FillPlotter` / `_TextPlotter` を同じ形で `_api.py` に足す。頂点数の検査は Plotter 固有の規則として `_FillPlotter` に置く。`text` の文字列以外の扱いは、例外を握りつぶさず `isinstance` で分岐する

### matplotlib の `Axes.fill` / `Axes.text` の挙動（3.10.8 で確認）
- **Context**: 戻り値、凡例、色、既定値の注入方法を確かめる
- **Sources Consulted**: py312 環境（matplotlib 3.10.8）での読み取り専用の実行、`matplotlib.text.Text._alias_map`、`matplotlib.patches.Patch._alias_map`
- **Findings**:
  - `ax.fill([0, 1, 0.5], [0, 0, 0.8], label="A", zorder=0.5)` → `list` に `Polygon` が 1 つ。`get_closed()` は `True`、`get_xy()` は先頭の頂点を末尾に重ねた `(n + 1, 2)`。`get_legend_handles_labels()` にラベルが出る
  - 色を指定しない `fill` は呼ぶたびに C0、C1、… と進む。`ax.plot` で線の色の順番を進めても、`fill` の色は C0 から始まる（塗りつぶし専用の順番）
  - 頂点が 2 個や 0 個でもエラーにならず、面積のない多角形ができる
  - `Polygon` の既定 zorder は 1、`Text` の既定 zorder は 3、既定の配置は `ha="left"`・`va="baseline"`、`clip_on=False`
  - `ax.text(0, 0, "y", ha="center", horizontalalignment="left")` は `center` になる（例外なし）。`fontdict={"ha": "left"}` と `horizontalalignment="center"` では `left` になる。どちらの名前が勝つかは matplotlib の内部の順序で決まり、公開の仕様ではない
  - `Text` の別名は `ha` ↔ `horizontalalignment`、`va` ↔ `verticalalignment` ほか。`zorder` に別名はない
  - `ax.text(0, 0, 1.5)` は `"1.5"` を表示する（matplotlib が文字列に変換する）
- **Implications**: `fill` は `Axes.fill` の戻り値をそのまま返す。`text` の配置の既定値は、正式名と別名の両方をキーワード引数と `fontdict` の中で確かめてから入れる。`zorder` は既存の `_set_default_params` で足りる

### 上流 spec `plot-side-effects` の規約
- **Context**: 新しい Plotter が従うべき描画後処理の契約
- **Sources Consulted**: `.kiro/specs/plot-side-effects/design.md`（「BasePlotter `_post_draw`」「Deprecation」「TernaryDiagram の変更点」）
- **Findings**:
  - `_BasePlotter.__init__(vector, ax=None, z=None, z_min=None, z_max=None, *, post_draw_context, **kwargs)`。`post_draw_context` は必須のキーワード専用引数で、各サブクラスは自分のシグネチャで明示的に受けて基底へ渡す
  - `_post_draw(*, mappable=None, colorbar=None)` を `__init__` の最後でちょうど 1 回呼ぶ。Plotter は `fig.tight_layout()` やカラーバーの追加を直接呼ばない
  - `TernaryDiagram` は `self.__post_draw_context` に `PostDrawContext` を保持し、描画メソッドから Plotter へ渡す
  - 警告文に Plotter の `name` を使うので、`name` は利用者に見えるメソッド名と同じにする
  - 既定値変更を予告するときは `PostDrawContext.first_time("<feature>.<topic>")` と `warn_external(format_default_change(...))` を使う
  - `utils.check_optional_bool(value, name)` が `None` / 真偽値（`numpy.bool_` を含む）以外を `TypeError`（`` `{name}` must be None, True or False, but got ... ``）にする。roadmap の横断の取り決めにより、`None` を受け付けない引数用の `utils.check_bool(value, name)` も `plot-side-effects` が一緒に足す
  - roadmap の横断の取り決めにより、`plot-side-effects` は共通 doctest ランナー `tests/test_doctests.py`（公開 API の例を一時ディレクトリで、FutureWarning をエラーにして実行）と、CHANGELOG の Unreleased の見出しの組（Breaking changes / New features / Deprecations / Bug fixes / Other changes）を用意する。各 spec は自分のランナーを作らず、該当する見出しに追記する
- **Implications**: `fill` / `text` は新しい API で既定値の変更がないため、`_deprecation.py` は使わない。値で色付けしないので `_post_draw()` を引数なしで呼ぶ。`text` の `auto_latex_notation` は `None` を受け付ける（三角図単位の設定を引き継ぐ）ので、検証は `check_optional_bool` を使い、`check_bool` は使わない（後述の決定）。docstring の例はランナーで通る形で書き、CHANGELOG の見出しは足さない

### 隣接 spec `diagram-customization` との重なり
- **Context**: 土台の部品と重なり順の扱いを確かめ、所有の重複を避ける
- **Sources Consulted**: `.kiro/specs/diagram-customization/design.md`（Boundary Commitments、`_SkeletonPart`、要件 9.x）
- **Findings**:
  - 土台の線（外枠・グリッド）は zorder `DEFAULT_ZORDER_GRIDS`（1）、文字（目盛りラベル・頂点ラベル・軸タイトル）は matplotlib の既定（3）。描き直しても同じ zorder を保ち、外枠をグリッドより後ろに積み直す
  - zorder 定数の値の変更と、新しい描画の重なり順は `region-plots` / `heatmaps` の担当と明記されている
  - `utils.py` に配置の純粋関数（`get_tick_values` など）を足すが、本機能はどれも使わない
- **Implications**: 本機能の重なり順は zorder の値だけで決まり、土台の描き直し（artist の追加順の変化）に影響されない。`_skeleton.py` と配置の関数には触れない

### 化学式の整形規則（`annotate-plain-text`）
- **Context**: `text` の整形を、判定規則を持たずにどう使うか
- **Sources Consulted**: `.kiro/steering/roadmap.md`（Direct Implementation Candidates、Shared seams）、`utils.get_label`、`_AnnotatePlotter`
- **Findings**:
  - roadmap は、化学式とみなす条件の絞り込み（または変換の有無を選ぶ引数）を `annotate-plain-text` が行い、`region-plots` より前に入れるとしている（Implementation Order で `plot-side-effects` → `diagram-customization` → `annotate-plain-text` → `region-plots` / `heatmaps`）。共有点は `utils.get_label`
  - roadmap は「`region-plots` の `text` は新しい API なので、呼び出しごとの `auto_latex_notation=None` で `TernaryDiagram` の設定を引き継ぐ」としている。`annotate` の表示を v3.x で変えるなら FutureWarning を出すことも求めている
  - 現在の `get_label` は文字列中の数字をすべて下付きにする（`"Sample 1"` → `"Sample $_{1}$"`）
  - 現在の `annotate` は常に `get_label` を通す。`TernaryDiagram` は `auto_latex_notation` を頂点ラベルに使うだけで、属性として保持していない
- **Implications**: `text` は「整形を行う設定の `annotate` と同じ表示」を契約にし、`annotate` と同じ入口（`annotate-plain-text` 適用前は `utils.get_label`）を呼ぶ。規則が絞られれば `text` も自動で追従する。テストは期待値を固定せず、`annotate` との一致で確かめる。三角図単位の設定を引き継ぐには、`TernaryDiagram` がその値を保持する必要がある。保持先は roadmap「横断の取り決め」で private な bool 属性 `TernaryDiagram.__auto_latex_notation` に決まっており、最初に必要になった側（`annotate-plain-text` か本 spec）が `__init__` に 1 行足し、もう一方はそれを使う（別名の属性は作らない）。`text` は新しい API なので、`annotate` の互換のための警告の経路は通らない

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| 既存の Plotter パターンで `_api.py` に追加 | `_FillPlotter` / `_TextPlotter` を `_BasePlotter` のサブクラスにし、`TernaryDiagram` に `fill` / `text` を足す | steering の構造どおり。検証・正規化・座標記録・描画後処理を基底から受け継ぐ | `heatmaps` と同じファイルを編集するので、テキスト上の衝突が起きやすい | 採用。追加位置をまとまったブロックにして衝突を解きやすくする |
| 別モジュール（`_region.py`）に Plotter を置く | `_api.py` の差分を減らす | 並行開発の衝突が減る | `_BasePlotter` は `_api.py` にあり、`_api.py` からも import するので循環 import になる | 不採用 |
| `ax.add_patch(Polygon(...))` で自前に組み立て | `fill` を `Axes.fill` を使わずに実装 | 戻り値を `Polygon` 単体にできる | 色の自動割り当て・データ範囲の更新を自前で行う必要がある。「matplotlib の関数をラップする」形から外れる | 不採用 |

## Design Decisions

### Decision: 1 回の呼び出しで 1 つの多角形を塗る
- **Context**: brief の「複数の多角形を一度に渡す API にするか（`ax.fill` のように）」
- **Alternatives Considered**:
  1. 1 呼び出し 1 多角形（`fill(vector)`、`vector` は `(n, 3)`）
  2. 多角形のリストを受ける（`fill([v1, v2, ...])`）
  3. `ax.fill(x1, y1, x2, y2, ...)` のような可変長の位置引数
- **Selected Approach**: 1。複数の領域は呼び出しを繰り返す
- **Rationale**: 相図では領域ごとに色とラベルが違うので、ループで呼ぶ形が自然。`_BasePlotter` の「1 つの `(n, 3)` 配列を受ける」契約と `x_` / `y_` の記録をそのまま使える。`plot` が 1 本の線を描くのと対になる
- **Trade-offs**: 同じ見た目の多角形を大量に描くときは呼び出しが増える。必要になれば、戻り値の型（`list`）を変えずに後から受け口を広げられる
- **Follow-up**: 3 次元の配列や長さの違うリストを渡すと、既存の shape 検証で `ValueError` になることをテストで確かめる

### Decision: `fill` の戻り値は `Axes.fill` の戻り値（`list[Polygon]`）そのもの
- **Context**: 戻り値を `Polygon` 単体にするか、matplotlib と同じリストにするか
- **Alternatives Considered**:
  1. `list[matplotlib.patches.Polygon]`（長さ 1）
  2. `matplotlib.patches.Polygon`
- **Selected Approach**: 1
- **Rationale**: 既存の `plot` が `Axes.plot` の戻り値（`list[Line2D]`）をそのまま返すのと同じ規則になり、「matplotlib の関数の薄いラッパー」という価値に合う。将来、1 呼び出しで複数の多角形を受けるようにしても型が変わらない
- **Trade-offs**: 1 つだけ取り出すには `(polygon,) = td.fill(...)` と書く必要がある。docstring の Examples にこの書き方を載せる

### Decision: 既定の zorder（`DEFAULT_ZORDER_FILL = 0.5`、`DEFAULT_ZORDER_TEXT = 4`）
- **Context**: 塗りつぶしがグリッドや散布図を隠さず、相の名前が塗りつぶしや点に隠れないようにする（要件 4）
- **Alternatives Considered**:
  1. fill を等高線とグリッドの間（0.5）、text を散布図より上（4）
  2. fill を等高線より下（-1）
  3. text を matplotlib の既定（3）のままにする
- **Selected Approach**: 1。既存の定数の値と名前は変えず、`DEFAULT_ZORDER_SCATTER` の直後に追加する
- **Rationale**:
  - fill を等高線より上にすると、等高線図の上に半透明の相領域を重ねられる。等高線より下にすると、`tricontourf` が三角形全体を覆うので fill が見えなくなる
  - fill をグリッド（1）より下にすると、グリッドと外枠が塗りつぶしの上に見える
  - text を 4 にすると、散布図（3）や `annotate`（matplotlib の既定 3）と同じ値にならず、呼び出し順に関係なく相の名前が点の上に出る
- **Trade-offs**: 不透明な fill は等高線図を隠す。docstring に `alpha` か `zorder` で変える方法を書く。`heatmaps` が自分の定数をどの値にするかは `heatmaps` が決める。`heatmaps` は `DEFAULT_ZORDER_HEATMAP = -1`（ヒートマップを最も奥のデータ層にする）を選んでおり、`-1 < 0.5` の関係は後からマージする側のテストで確かめる

### Decision: `text` の既定の配置は中央・中央、文字の大きさは matplotlib の既定
- **Context**: brief の「`text` の既定の配置（`ha` / `va`）」
- **Selected Approach**: `horizontalalignment="center"`、`verticalalignment="center"`。`fontsize` は入れない（rcParams の `font.size`）
- **Rationale**: 相の名前は領域の中心に置くので、文字列の中心を組成点に合わせる。`annotate` の `fontsize=8` は点の横に置く小さな注釈のための値で、領域ラベルには小さすぎる。図全体の文字の大きさに合わせるのが自然
- **Trade-offs**: 利用者が `ha` などの別名で指定したときに、既定値と衝突しないよう注入の判定を広げる必要がある（次の決定）

### Decision: 配置の既定値は、別名と `fontdict` まで見てから入れる
- **Context**: 要件 5.1・5.2（利用者の指定を正式名・別名にかかわらず優先）。`_set_default_params` はキー名の一致しか見ない
- **Alternatives Considered**:
  1. `matplotlib.cbook.normalize_kwargs(kwargs, Text)` で正式名にそろえてから注入
  2. 対象の 2 項目について、正式名と別名の組を固定で持ち、キーワード引数と `fontdict` のキーを調べる
- **Selected Approach**: 2
- **Rationale**: 注入するのは 2 項目だけで、組は固定。`normalize_kwargs` に Artist のクラスを渡す形は古い matplotlib での挙動確認が要る（`diagram-customization` も同じ注意を記録）。`fontdict` は `normalize_kwargs` の対象外なので、どちらにしても別に調べる必要がある
- **Trade-offs**: 将来、別名のある項目を既定値に足すときは組を足す必要がある

### Decision: `text` の化学式の整形は `auto_latex_notation: Optional[bool] = None`（キーワード専用、三角図単位の設定を引き継ぐ）
- **Context**: brief の「化学式整形の既定値」。要件 3。cross-spec review で roadmap に「`text` は呼び出しごとの `auto_latex_notation=None` で `TernaryDiagram` の設定を引き継ぐ」と確定した
- **Alternatives Considered**:
  1. 既定で整形する（`True`）
  2. 既定で整形しない（`False`）
  3. 既定は `None` で、`TernaryDiagram(auto_latex_notation=...)` の設定に従い、`True` / `False` で呼び出しごとに上書きする
- **Selected Approach**: 3（当初は 1 を選んでいたが、roadmap の横断の取り決めに合わせて改めた）。引数名は `TernaryDiagram.__init__` の既存の `auto_latex_notation` にそろえ、キーワード専用にする
- **Rationale**: 頂点ラベルを整形しない設定の三角図で、相の名前だけが整形されるのは一貫しない。三角図単位の既定（`True`）を引き継ぐので、何も指定しない利用者には当初案 1 と同じく化学式が整形される。相の名前の多くは化学式（`Li2TiO3`、`LiF + Li2O`）で、普通の名前が誤って整形される問題は、`annotate-plain-text` が判定を絞ることで解消する
- **Trade-offs**: `TernaryDiagram` が三角図単位の設定を保持する必要があり、`__init__` の本体に private 属性を 1 行足す（シグネチャ・検証・土台の構築は変えない。roadmap「横断の取り決め」により属性名は `__auto_latex_notation` で、`annotate-plain-text` が先に足していればそれを使い、別名の属性は作らない）。`TernaryDiagram.__init__` は `auto_latex_notation` を検証しない（既存の挙動）ので、引き継いだ値は頂点ラベルと同じく真偽で解釈する
- **Follow-up**: `annotate-plain-text` が `annotate` の切り替え引数に別の名前を選んだ場合は、`text` の引数名をそれにそろえる（`text` は未リリースなので変更の負担はない）

### Decision: `auto_latex_notation` の検証は `TernaryDiagram.text` で `utils.check_optional_bool` を使う
- **Context**: 要件 3.5（`None`・真偽値以外は、受け付けられる値を示すメッセージ付きの `TypeError`）。roadmap の横断の取り決めで、真偽値の検証は `plot-side-effects` の `utils.check_bool` / `check_optional_bool` を使うと確定した
- **Alternatives Considered**:
  1. `TernaryDiagram.text` で `check_optional_bool` を通し、`None` を三角図単位の設定で解決してから Plotter に渡す
  2. `_TextPlotter` で `bool` / `numpy.bool_` の型検査を独自に行う（当初案）
  3. `check_bool` を使う
- **Selected Approach**: 1
- **Rationale**: 引数が `None` を受け付けるようになったので、`check_optional_bool` の文面（`must be None, True or False`）がそのまま正しい案内になる。検証を `utils.check_*` に集約する steering の方針に合い、独自の型検査が要らなくなる。`plot-side-effects` が `colorbar` をファサードで `check_optional_bool` に通すのと同じ置き場所で、`None` の解決には三角図単位の設定が要るので、ファサードで行うのが自然。3 は `None` を受け付けないので合わない
- **Trade-offs**: `_TextPlotter` は解決済みの `bool` を前提にする（private なので `TernaryDiagram.text` 以外からは呼ばない）

### Decision: 頂点数の検査は `_FillPlotter` に置く
- **Context**: 要件 6.2。steering は検証を `utils.check_*` に集約するとしている
- **Selected Approach**: shape の検証は既存の `check_2d_vector`（基底クラス経由）で行い、「多角形には 3 個以上の頂点が必要」という描画固有の規則だけを `_FillPlotter` で検査する
- **Rationale**: `contour` の `z` 必須や `scatter` の `annotations` の長さと同じく、描画種別に固有の規則は Plotter に置かれている。`utils.py` は `plot-side-effects` と `diagram-customization` も編集するので、1 か所でしか使わない関数を足さない（Simplification）

## Synthesis Outcomes
- **Generalization**: `fill` と `text` は「組成 → 2 次元 → matplotlib の 1 関数 → 描画後処理」という既存の Plotter の流れの特殊例で、新しい抽象は要らない。重なり順は「描画種別ごとの zorder 定数」という既存の一般化に 2 つ足すだけ
- **Build vs. Adopt**: 多角形・凡例・色の割り当ては `Axes.fill`、文字の配置は `Axes.text`、レイアウトとカラーバーは `plot-side-effects` の `_post_draw`、整形は `annotate` と同じ入口を採用する。自前で作るのは、配置の既定値を別名まで見て入れる小さな判定だけ
- **Simplification**: 新しいモジュール・utils 関数・警告・doctest ランナーは作らない。複数の多角形を一度に受ける API、領域ラベルの自動配置は入れない。`TernaryDiagram` の整形設定への追従は、roadmap の取り決めに従って private 属性 1 つと `None` の解決だけで実現する

## Risks & Mitigations
- `heatmaps` と `_api.py` の同じ箇所（zorder 定数の並び、メソッドの並び、Plotter の並び）を編集する — roadmap の実装順により 1 つずつマージし、本 spec の追加をそれぞれ 1 つのまとまったブロックにし、既存の要素を並べ替えない。後からマージする側が先の追加を残し、`DEFAULT_ZORDER_HEATMAP`（-1）< `DEFAULT_ZORDER_FILL`（0.5）をテストで確かめる
- `annotate-plain-text` が整形の入口を `get_label` 以外に移す — `text` は `annotate` と同じ入口を呼ぶことを契約にし、テストは `annotate` の表示との一致で確かめる。入口が変わったら Revalidation Trigger として `_TextPlotter` を追従させる
- `get_label` が数式（`$\alpha_2$` など）の中の数字まで下付きにする — 判定規則は本 spec の範囲外。docstring に `auto_latex_notation=False` で避けられることを書く
- 不透明な fill が等高線図を隠す — docstring に `alpha` や `zorder` の指定例を載せる
- roadmap の実装順より先に実装を始める — `post_draw_context`・`_post_draw`・`check_optional_bool`・共通 doctest ランナー（`plot-side-effects`）、`set_grid`（`diagram-customization`）、整形の入口（`annotate-plain-text`）がないと動かない・確かめられないので、この 3 つのマージ後に行う（タスクの着手条件に書く）
- docstring の例が FutureWarning を出す — tech.md「Docstring Examples」に従い、レイアウトエンジンのある図（`plt.subplots(layout="constrained")`）に `ax=ax` で描く。共通 doctest ランナーは FutureWarning をエラーにするので、違反は検出される
- `annotate-plain-text` が `annotate` の既定の表示を据え置き、互換の FutureWarning で移行を案内する形をとる — `text` は新しい API なので互換の経路を通らず規則の最終形を使う。要件 3.2 の比較相手は `annotate` の整形を明示した設定にする。タスク 3.2 の着手時に確かめる

## References
- [matplotlib.axes.Axes.fill](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.fill.html) — 戻り値が `list[Polygon]`、`**kwargs` は `Polygon` のプロパティ
- [matplotlib.pyplot.fill](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.fill.html) — docstring に載せる URL（既存メソッドは `pyplot` の URL を載せている）
- [matplotlib.pyplot.text](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.text.html) — 同上
- [Zorder Demo](https://matplotlib.org/stable/gallery/misc/zorder_demo.html) — Artist の種類ごとの既定 zorder（Patch 1、Line2D 2、Text 3）
- `.kiro/specs/plot-side-effects/design.md` — `_post_draw` / `PostDrawContext` / `_deprecation.py` / `check_optional_bool` の契約
- `.kiro/steering/roadmap.md`（Implementation Order、横断の取り決め、annotate-plain-text）と `.kiro/steering/tech.md`（Docstring Examples） — 実装順、真偽値の検証、doctest ランナー、CHANGELOG の見出し、`text` の整形の引き継ぎ
- `.kiro/specs/diagram-customization/design.md` — 土台の zorder と描き直しの規則
