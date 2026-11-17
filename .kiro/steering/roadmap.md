# Roadmap

## Overview

python-ternary（月間約 2.4 万 DL、2021 年以降リリースなし）と mpltern（月間約 1.2 万 DL、matplotlib の projection として実装）に比べ、ternary-diagram（月間約 100 DL）は見た目を変えられず、描画の種類が少なく、描画のたびにレイアウトとカラーバーへ副作用を起こす。このため、論文用の図を作る段階で利用者が離れている。

汎用性で mpltern と正面から競うのはやめ、「材料・化学の組成マップを最短で論文品質にする」ことに絞る。今の設計（普通の `Axes` に描く薄いラッパー、化学式の自動整形）を保ったまま、カスタマイズ API・相図向けの描画・ヒートマップを足し、副作用をなくし、使い方のドキュメントを整える。

## Approach Decision

- **Chosen**: A. 今の設計を広げる。三角図の土台（枠・グリッド・目盛り・ラベル）を部品ごとに分けて artist を保持し、matplotlib の `subplot_kw` に倣った `*_kw` 引数と、作成後に変える `set_*` メソッドを用意する。新しい描画は既存の Plotter パターン（`_BasePlotter` のサブクラス）で追加する
- **Why**: 既存ユーザーのコードがそのまま動き、今の強み（任意の `Axes` に混ぜられる、組成比を正規化せず渡せる、化学式の自動整形）を保てる。matplotlib の API だけで実現でき、依存も増えない
- **Rejected alternatives**:
  - B. matplotlib の projection として作り直す: 書き直しの規模が大きく（v4 相当）、すでにそれを完成させている mpltern と正面からぶつかる
  - C. スタイルオブジェクト（`TernaryStyle`）: 一か所だけ変えたいときに冗長で、結局 artist の参照も必要になる。使い回しの利点は `*_kw` の辞書を使い回すことでほぼ得られる

## Scope

- **In**:
  - 描画時の副作用（毎回の `tight_layout`、カラーバーの自動追加）の制御と、段階的な既定値変更のための FutureWarning
  - グリッド・目盛り・軸タイトル・頂点ラベルのカスタマイズ
  - 相領域の塗りつぶし（`fill`）と組成点へのテキスト配置（`text`）
  - 散布データのヒートマップ（tripcolor 系）と関数のヒートマップ
  - docstring の充実、使い方ページ、README の刷新
- **Out**:
  - matplotlib の projection 化、三角形の一部の拡大表示、三角形全体の回転
  - mpltern / python-ternary との使い分け表
  - v4.0.0 での既定値の切り替え（本 roadmap の後に行う。v3.x では FutureWarning まで）
  - 日本語ドキュメント、ドキュメントのホスティング変更

## Constraints

- Python 3.9+、ランタイム依存は numpy と matplotlib のみ（scipy などを足さない）
- v3.x の間は既存ユーザーの図とコードを壊さない。既定値を変える予定のものは引数で切り替えられるようにし、FutureWarning で移行方法を示す。切り替えは v4.0.0 で行う
- matplotlib の古いバージョンでも動かす。バージョンで有無が分かれる API（`Figure.get_layout_engine` は 3.6+ など）は分岐で吸収する
- 公開 API は `TernaryDiagram` に集約する。新しい描画もそのメソッドとして追加し、戻り値は matplotlib のネイティブオブジェクトにする
- テストはネットワークに依存させず、画像比較ではなく artist の状態を assert する
- docstring は NumPy スタイルの英語

## Boundary Strategy

- **Why this split**:
  - `plot-side-effects` は「描画後に何をするか（レイアウト・カラーバー）」の共通の約束事を決める。新しい描画を追加する `region-plots` と `heatmaps` がこれに従えば、後から作り直さずに済むので先に行う
  - `diagram-customization` は三角図の土台（`TernaryDiagram.__init__` が描く部分）だけを扱い、Plotter には触れない。spec は並行して作れたが、`check_bool`・共通 doctest ランナー・`td` fixture・CHANGELOG の見出し・`tight_layout` を前提にするので、実装は `plot-side-effects` の後に行う
  - `region-plots`（z を持たない描画）と `heatmaps`（z を持ちカラーバーと関わる描画）は、互いに独立した新しい Plotter なので別々に進められる
  - `user-guide-docs` は 1〜4 の API がそろってから、使い方を通して書く。各 spec は自分が追加する API の docstring を自分で書く
- **Shared seams to watch**:
  - `_api.py` は 1 つのモジュールに `TernaryDiagram` とすべての Plotter が入っているので、並行して進めると衝突しやすい
  - zorder の定数（`DEFAULT_ZORDER_*`）: 新しい描画の重なり順と、グリッドの描き直しで変わらないようにする
  - カラーバーの扱い: `plot-side-effects` で決めた方針を `heatmaps` がそのまま使う
  - 非推奨・FutureWarning の出し方: `plot-side-effects` で共通の仕組みを作り、他の spec も使う
  - 化学式の自動整形（`utils.get_label`）: `region-plots` の `text` と、直接実装する候補の `annotate-plain-text` が同じ判定を使う

## Implementation Order

spec の依存とは別に、`_api.py` での衝突を避けるため、実装は次の順に 1 つずつマージする。

1. `plot-side-effects`（`TernaryDiagram.__init__` の最終的なシグネチャ、共通 doctest ランナー、CHANGELOG の見出しの組を確定させる） — 実装済み（2026-10-24）
2. `diagram-customization`（1 に合わせる） — 実装済み（2026-11-06）
3. `annotate-plain-text`（直接実装） — 実装済み（2026-11-08）
4. `region-plots` と `heatmaps`（どちらが先でもよいが、1 つずつ） — `region-plots` は実装済み（2026-11-09）、`heatmaps` は実装済み（2026-11-10）
5. `user-guide-docs` — 実装済み（2026-11-16）

`typing-cleanup` はいつ入れてもよい。

### 横断の取り決め（cross-spec review で確定）

- `TernaryDiagram.__init__` の最終形: `(materials, ax=None, auto_latex_notation=True, *, tight_layout=None, border_kw=None, grid_kw=None, tick_kw=None, axis_label_kw=None, vertex_label_kw=None)`。検証の順は `ax` → `materials` → `tight_layout` → `*_kw`
- `__init__` の docstring: 新しい引数の Parameters は、それを足す spec が書く。Examples 節は `user-guide-docs` だけが持つ。`*_kw` の使用例は対応する `set_*` メソッドの docstring に書く（`border_kw` → `set_border`、`grid_kw` → `set_grid`、`tick_kw` → `set_ticks`、`axis_label_kw` → `set_axis_labels`、`vertex_label_kw` → `set_vertex_labels`）
- docstring の例の書き方と共通 doctest ランナーは steering の tech.md「Docstring Examples」に従う。ランナー（`tests/test_doctests.py`）は `plot-side-effects` が作る
- CHANGELOG の `Unreleased` の見出しは Breaking changes / New features / Deprecations / Bug fixes / Other changes。`plot-side-effects` が最初にこの組をそろえ、他の spec は該当する見出しに追記する
- `_deprecation.warn_external` はパッケージ全体で利用者向けの警告を出す入口で、種類は `category` で選ぶ（既定は FutureWarning）
- 真偽値の検証は `utils.check_bool(value, name)`（`plot-side-effects` が `check_optional_bool` と一緒に足す）を使う
- 新しく足す `utils` の公開関数の docstring は、それを足す spec が書く
- 三角図単位の化学式整形の設定は private な bool 属性 `TernaryDiagram.__auto_latex_notation` に保持する。最初に必要になった側（`annotate-plain-text` か `region-plots`）が `__init__` に 1 行足し、もう一方はそれを使う。別名の属性を作らない

## Direct Implementation Candidates

- [x] annotate-plain-text -- `annotate` と `scatter(annotations=...)` が普通の文字列まで化学式として変換する（`"Sample 1"` → `"Sample $_{1}$"`）。化学式とみなす条件を絞るか、変換の有無を引数で選べるようにする小さな修正。`region-plots` の `text` と `user-guide-docs` の説明が同じ判定を前提にするので、それより前に入れる。既存ユーザーの `annotate` の表示を v3.x で黙って変えないこと（変えるなら FutureWarning を出す）。`region-plots` の `text` は新しい API なので、呼び出しごとの `auto_latex_notation=None` で `TernaryDiagram` の設定を引き継ぐ
  - 実装結果: 整形の入口は `utils.to_latex_notation`（空白で区切った語のうち、`utils.is_chemical_formula` が化学式とみなすものだけを `get_label` で整形する。`$` を含む文字列はそのまま）。`annotate` と `scatter` の切り替え引数は `auto_latex_notation: bool | None = None`（キーワード専用）。`None` は v3.x の表示を保ち、表示が変わる文字列にだけ FutureWarning を出す（三角図ごとに 1 回）。`TernaryDiagram.__auto_latex_notation` は本件が `__init__` に足した。`region-plots` の `text` は `None` を三角図の設定で解決し、`to_latex_notation` を呼ぶ（警告の経路は通らない）
- [x] typing-cleanup -- `TernaryDiagram.x_` / `y_` に残っている `# FIXME: mypy` を型注釈で解消する。`fig` の型注釈を、subfigure の Axes で返る `SubFigure` も含む形にする。挙動は変えない
  - 実装結果（2026-11-16）: 残っていた 7 件をすべて解消し、`mypy src` のエラーは 0 件。`fig` の戻り値は文字列の注釈 `"Union[Figure, SubFigure]"`（`SubFigure` は matplotlib 3.4 から）

## Follow-ups (v3.x)

ロードマップの spec の実装中に見つかった、小さな改善の候補。v3.x のうちに直接実装で扱ってよい。

- [x] `TernaryDiagram.colorbar(location="bottom")` だけを渡すと、既定の `orientation="vertical"` と食い違って matplotlib が TypeError を出す。`location` から向きを決める — 実装済み（2026-11-16、`orientation` の既定を `None` にした。自動で付くカラーバーは変わらない）
- matplotlib 3.11 で、constrained layout にカラーバーが付く図では、左下の頂点ラベルが図の左端から約 3px はみ出す（三角図の `adjustable="datalim"` と constrained layout の組み合わせ。README の画像は matplotlib 3.10 で作った）
- [x] docstring の書き方の残り: `fill` の Returns の `List[...]`（他は `list of ...`）、`text` の `vector` の型の行の `(1, 3)`（`annotate` は説明文に書く）、上流の項目の `bool or None` / `dict or None`（本 spec の担当分は None を説明文に書く） — 実装済み（2026-11-16）。`fill` と `text` は揃えた。`bool or None` / `dict or None` は、None が「指定なし」という独自の意味を持つ三択の引数なので、型の行に None を残す方針にした
- `autoclass_content = "both"` で、クラスの Notes 節が `__init__` の Parameters より前に表示される。並びを変えるなら Notes 節を `__init__` 側に移すか、クラスの説明に溶かす

## Deferred to v4.0.0

v3.x では直さず、v4.0.0 の準備で扱う項目。

- 既定値の切り替えと `flag_cbar` の削除（CHANGELOG の Deprecations のとおり）
- `PostDrawContext.has_colorbar` の判定を直す。登録済みのカラーバーと同じ mappable に利用者が `fig.colorbar` で別のカラーバーを足すと、登録済みのものが削除済みと判定される。v3.x では重複の FutureWarning が出ないだけだが、v4.0.0 の既定（既存ありなら自動追加しない）では 1 本余分に付く
- `scatter` / `contour` の `colorbar` をキーワード専用にする（候補）。6 番目の位置引数は v3.2.1 から意味が変わった（`0` / `1` は `TypeError`、`None` は未指定）。v3.x で位置引数での指定に FutureWarning を出すかは、v4.0.0 の準備で決める
- 三角図の縦横比の固定を `adjustable="datalim"` から `adjustable="box"` に変える。Follow-ups の頂点ラベルがはみ出す件の対処。README の例の図（144 dpi）で左の余白は、`datalim` では matplotlib 3.10 で 3px、3.11 で 0px（はみ出す）、`box` ではどちらも 8〜9px で左右が均等になり、`layout="compressed"` も効く。Axes の枠が三角形まで縮むので、凡例の `loc` の位置と自動で付くカラーバーの長さが変わる。そのため v3.x では変えない

## Specs (dependency order)

- [x] plot-side-effects -- 毎回の tight_layout とカラーバーの自動追加を切り替え可能にし、既存のレイアウトエンジンを上書きしないようにする。将来の既定値変更に向けて FutureWarning を出す共通の仕組みを作る。Dependencies: none
- [x] diagram-customization -- グリッド・目盛り・軸タイトル・頂点ラベル・外枠を、作成時の `*_kw` 引数と作成後の `set_*` メソッドで変えられるようにする。既定の見た目は今と同じ。Dependencies: plot-side-effects
- [x] region-plots -- 組成で指定した多角形を塗る `fill` と、組成点にテキストを置く `text` を追加し、相図を描けるようにする。Dependencies: plot-side-effects
- [x] heatmaps -- 散布データを補間せず三角形で塗る `tripcolor` と、関数 f(a, b, c) を格子で評価して塗るヒートマップを追加する。Dependencies: plot-side-effects
- [x] user-guide-docs -- 既存メソッドの docstring の充実、機能ごとの使い方ページ、README の刷新を行う。Dependencies: plot-side-effects, diagram-customization, region-plots, heatmaps
