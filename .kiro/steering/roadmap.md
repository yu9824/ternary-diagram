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
2. `diagram-customization`（1 に合わせる）
3. `annotate-plain-text`（直接実装）
4. `region-plots` と `heatmaps`（どちらが先でもよいが、1 つずつ）
5. `user-guide-docs`

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

- [ ] annotate-plain-text -- `annotate` と `scatter(annotations=...)` が普通の文字列まで化学式として変換する（`"Sample 1"` → `"Sample $_{1}$"`）。化学式とみなす条件を絞るか、変換の有無を引数で選べるようにする小さな修正。`region-plots` の `text` と `user-guide-docs` の説明が同じ判定を前提にするので、それより前に入れる。既存ユーザーの `annotate` の表示を v3.x で黙って変えないこと（変えるなら FutureWarning を出す）。`region-plots` の `text` は新しい API なので、呼び出しごとの `auto_latex_notation=None` で `TernaryDiagram` の設定を引き継ぐ
- [ ] typing-cleanup -- `TernaryDiagram.x_` / `y_` に残っている `# FIXME: mypy` を型注釈で解消する。挙動は変えない

## Specs (dependency order)

- [x] plot-side-effects -- 毎回の tight_layout とカラーバーの自動追加を切り替え可能にし、既存のレイアウトエンジンを上書きしないようにする。将来の既定値変更に向けて FutureWarning を出す共通の仕組みを作る。Dependencies: none
- [x] diagram-customization -- グリッド・目盛り・軸タイトル・頂点ラベル・外枠を、作成時の `*_kw` 引数と作成後の `set_*` メソッドで変えられるようにする。既定の見た目は今と同じ。Dependencies: plot-side-effects
- [x] region-plots -- 組成で指定した多角形を塗る `fill` と、組成点にテキストを置く `text` を追加し、相図を描けるようにする。Dependencies: plot-side-effects
- [x] heatmaps -- 散布データを補間せず三角形で塗る `tripcolor` と、関数 f(a, b, c) を格子で評価して塗るヒートマップを追加する。Dependencies: plot-side-effects
- [x] user-guide-docs -- 既存メソッドの docstring の充実、機能ごとの使い方ページ、README の刷新を行う。Dependencies: plot-side-effects, diagram-customization, region-plots, heatmaps
