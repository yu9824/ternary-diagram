# Brief: plot-side-effects

## Problem

`scatter` などを呼ぶたびに、ライブラリが図全体へ副作用を起こす。

- 描画のたびに `fig.tight_layout()` を呼ぶ。`plt.figure(layout="constrained")` で作った図では、カラーバーがなければレイアウトが tight に切り替わり（"The figure layout has changed to tight" という警告だけが出る）、カラーバーがあると `RuntimeError` で描画自体が失敗する（どちらも matplotlib 3.10.8 で確認）。subfigure や手動で調整したレイアウトも崩れ、描画のたびに余計な計算が走る
- `z` を渡すと、既定（`flag_cbar=True`）で毎回カラーバーを追加する。contour の上に scatter を重ねるだけでカラーバーが 2 本になり、そのたびに本体の Axes が縮む

論文用の図を既存の matplotlib ワークフローに組み込みたい利用者ほど、この副作用に困る。

## Current State

- `_ScatterPlotter` / `_ContourPlotter` / `_LinePlotter` / `_AnnotatePlotter` は、それぞれ描画の最後に `self.fig.tight_layout()` を呼んでいる。止める方法はない
- `scatter` と `contour` は `flag_cbar: bool = True` を持ち、`z` があればカラーバーを追加する。手動で付けるための `TernaryDiagram.colorbar()` もある
- 非推奨や FutureWarning を出す仕組みはまだない

## Desired Outcome

- 自動の `tight_layout` とカラーバーの自動追加を、利用者が切り替えられる
- 図にすでにレイアウトエンジン（constrained など）が設定されていれば、ライブラリはそれを上書きしない
- v4.0.0 で既定値を変える予定の挙動に依存している利用者には、移行方法を書いた FutureWarning が出る。新しい既定を明示した利用者には出ない
- 描画後の処理（レイアウト・カラーバー）が `_BasePlotter` 側の共通の仕組みにまとまり、新しい Plotter（`region-plots`、`heatmaps`）は個別に `tight_layout` を呼ばずにそれを使う
- v3.x の間は、引数を何も変えていない既存ユーザーの図の見た目が変わらない

## Approach

A 案（今の設計を広げる）に沿って、描画後の処理を `_BasePlotter` の共通メソッドにまとめ、`TernaryDiagram` 単位の設定とメソッド単位の引数で切り替える。FutureWarning を出す小さな共通ヘルパーを作り、他の spec でも使う。

設計で決めること:

- 引数の名前と置き場所（`TernaryDiagram(..., tight_layout=...)` かメソッドごとか）
- `flag_cbar` を matplotlib らしい名前（`colorbar=` など）にするか。するなら旧名は非推奨の別名として残す
- FutureWarning を出す条件（既定のままの呼び出しすべてか、挙動が実際に変わるときだけか）と、1 回だけ出すか
- v4.0.0 での新しい既定値

## Scope

- **In**:
  - 自動 `tight_layout` の切り替えと、既存レイアウトエンジンの尊重
  - カラーバーの自動追加の切り替えと、重複追加の扱い
  - 描画後処理の共通化（既存 4 つの Plotter を移行する）
  - 非推奨・FutureWarning の共通ヘルパー
  - テストと CHANGELOG
- **Out**:
  - v4.0.0 での既定値の切り替えそのもの
  - カラーバーの見た目のカスタマイズ（既存の `colorbar()` の範囲を超えるもの）
  - 新しい描画の追加

## Boundary Candidates

- 描画後のレイアウト処理（レイアウトエンジンの判定を含む）
- カラーバーの追加方針（自動か手動か、重複の扱い）
- 非推奨・FutureWarning のヘルパー（他の spec からも使う）

## Out of Boundary

- 三角図の土台（グリッド・目盛り・ラベル）の描き方。`diagram-customization` が持つ
- 新しい描画メソッド。`region-plots` と `heatmaps` が持つ

## Upstream / Downstream

- **Upstream**: Python 3.9+ への移行とテスト整備（3a〜3d のブランチ）
- **Downstream**: `region-plots`、`heatmaps`（描画後処理とカラーバー方針を使う）、`user-guide-docs`（移行方法を書く）、v4.0.0 での既定値の切り替え

## Existing Spec Touchpoints

- **Extends**: なし
- **Adjacent**: `diagram-customization`（同じ `_api.py` を触る。土台の描画には手を出さない）

## Constraints

- v3.x では既存ユーザーの見た目を変えない
- `Figure.get_layout_engine` は matplotlib 3.6+ にしかないので、古いバージョンでは分岐で吸収する
- 警告は `FutureWarning`（利用者向け）を使い、`stacklevel` を利用者のコード位置に合わせる
