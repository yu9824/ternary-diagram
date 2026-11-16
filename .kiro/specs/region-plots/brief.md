# Brief: region-plots

## Problem

材料系の利用者は三元系の相図を描く。単相域・二相域・三相域を多角形で塗り分け、領域の中に相の名前を置くのが典型だが、今は `utils.three2two` で自分で座標変換してから `ax.fill` や `ax.text` を呼ぶしかない。「組成をそのまま渡せる」というこのライブラリの価値が、相図では成り立たない。

## Current State

- 組成で指定できる描画は `scatter`、`contour`、`plot`（タイライン）、`annotate` だけ
- `annotate` は注釈用で、既定で点から右上に 0.02 ずらした位置に文字を置く（`xytext`、`fontsize=8`）。領域の中心にラベルを置く用途には合わない
- 多角形を塗る手段はない

## Desired Outcome

- `td.fill(vector, **kwargs)` で、組成で指定した頂点（shape `(n, 3)`、合計は 1 でなくてよい）を結ぶ多角形を塗れる。`label` を渡せば凡例に出る。戻り値は matplotlib のネイティブオブジェクト
- `td.text(text, vector, **kwargs)` で、組成点のちょうどその位置に文字を置ける。化学式の自動整形の有無を選べる
- どちらも既存の描画と同じく `**kwargs` を matplotlib に渡し、描いた座標を `x_` / `y_` に記録する
- 既定の重なり順で、塗りつぶしがグリッドや散布図を隠さない

## Approach

A 案（今の設計を広げる）に沿って、`_FillPlotter` と `_TextPlotter` を既存の Plotter パターンで追加し、描画後の処理は `plot-side-effects` で作る共通の仕組みを使う。

設計で決めること:

- `fill` の既定の zorder（等高線とグリッドの間など）と、新しい `DEFAULT_ZORDER_*` 定数
- `text` の既定の配置（`ha` / `va`）と化学式整形の既定値
- 複数の多角形を一度に渡す API にするか（`ax.fill` のように）

## Scope

- **In**: `fill`、`text`、それぞれの既定値、テスト、docstring、CHANGELOG
- **Out**:
  - 相境界の自動計算や凸包の計算
  - 領域ラベルの自動配置
  - ハッチングなどの見た目のプリセット（`**kwargs` で matplotlib の機能を使えば足りる）

## Boundary Candidates

- 多角形の塗りつぶし（`fill`）
- 組成点へのテキスト配置（`text`）

## Out of Boundary

- 描画後のレイアウト・カラーバーの処理。`plot-side-effects` が持つ
- 化学式とみなす判定そのものの変更。直接実装する候補の `annotate-plain-text` が持つ

## Upstream / Downstream

- **Upstream**: `plot-side-effects`（描画後処理の共通の仕組み）、`annotate-plain-text`（化学式とみなす判定）
- **Downstream**: `user-guide-docs`（相図の描き方のページ）

## Existing Spec Touchpoints

- **Extends**: なし
- **Adjacent**: `heatmaps`（同じく新しい Plotter を追加する。zorder の定数を一緒に整理する）

## Constraints

- 公開 API は `TernaryDiagram` のメソッドとして追加する
- 入力の検証は `utils.check_*` を使い、不正な入力には `ValueError` を返す
