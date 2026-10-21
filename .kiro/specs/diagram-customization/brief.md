# Brief: diagram-customization

## Problem

三角図の見た目がほとんど固定されている。グリッドは 10% 刻み、線の色・太さ、フォントサイズも決め打ちで、軸タイトル（例: 「Li2O / mol%」）を付けられず、0 と 100 の目盛りも出せない。論文用に「5% 刻みにしたい」「軸タイトルを付けたい」「フォントを雑誌の規定に合わせたい」となった時点で、利用者は mpltern や python-ternary に乗り換えてしまう。これが一番大きな弱点。

## Current State

- `TernaryDiagram.__init__` が、外枠・内側のグリッド（3 方向 × 9 本）・目盛りラベル（`"%d0"` 形式で 10〜90）・頂点ラベルを、ハードコードされた定数で一度に描く
- 描いた artist への参照は持っておらず、後から変更・削除する手段がない（`ax.lines` / `ax.texts` を直接いじるしかない）
- 変えられるのは `auto_latex_notation`（頂点ラベルの化学式整形の有無）だけ

## Desired Outcome

- 作成時に、matplotlib の `subplot_kw` に倣った `*_kw` 引数（例: `grid_kw`、`tick_kw`）で見た目を指定できる
- 作成後に、`set_*` メソッド（例: `set_grid`、`set_ticks`、`set_axis_labels`、`set_vertex_labels`）で変更でき、変更前の artist は残らない
- 少なくとも次を変えられる: グリッドの間隔・線種・色・表示有無、目盛りの間隔・書式（パーセント / 割合）・0 と 100 の表示・フォントサイズ、各辺の軸タイトル（新規）、頂点ラベルのフォントサイズと位置、外枠の線種
- 何も指定しなければ、今とまったく同じ見た目になる（既存テストの構造的な assert がそのまま通る）

## Approach

A 案（今の設計を広げる）に沿って、`__init__` の描画を部品（外枠・グリッド・目盛り・軸タイトル・頂点ラベル）ごとに分け、それぞれが自分の artist を保持して描き直せるようにする。辺上の位置や目盛り位置の計算は `utils` の純粋関数にする。

設計で決めること:

- `*_kw` 引数と `set_*` メソッドの名前と引数（matplotlib の命名に寄せる）
- 目盛りの書式の指定方法（書式文字列か関数か）
- 目盛りがどの辺に付き、どの成分を表すか（今の配置を既定とし、ドキュメントに明記する）

## Scope

- **In**:
  - 外枠・グリッド・目盛り・軸タイトル・頂点ラベルの部品化と artist の保持
  - 作成時の `*_kw` 引数と作成後の `set_*` メソッド
  - 目盛り位置などの幾何計算の純粋関数化
  - テスト、docstring、CHANGELOG
- **Out**:
  - 三角形の一部の拡大表示、三角形全体の回転、projection 化
  - スタイルオブジェクトや rcParams によるグローバルな既定値の変更（C 案は採らない）
  - カラーバーの見た目

## Boundary Candidates

- 土台の各部品（外枠、グリッド、目盛り、軸タイトル、頂点ラベル）
- 幾何計算の純粋関数（`utils`）

## Out of Boundary

- 描画メソッド（scatter など）とその後処理。`plot-side-effects`、`region-plots`、`heatmaps` が持つ
- レイアウトの自動調整。`plot-side-effects` が持つ

## Upstream / Downstream

- **Upstream**: なし（steering の規約に従う）
- **Downstream**: `user-guide-docs`（見た目の変え方のページ）

## Existing Spec Touchpoints

- **Extends**: なし
- **Adjacent**: `plot-side-effects`（同じ `_api.py` を触る。Plotter には手を出さない）

## Constraints

- 既定の見た目を変えない（v3.x の互換性方針）
- 部品の zorder は今の `DEFAULT_ZORDER_GRIDS` を保ち、描き直しても重なり順が変わらないようにする
- `auto_latex_notation` は今の意味のまま残す
