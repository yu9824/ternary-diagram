# Brief: heatmaps

## Problem

物性値の分布を見せる手段が、補間した等高線（`contour`）と点の色分け（`scatter`）しかない。

- 実験点がまばらなとき、`contour` の滑らかな補間はデータがない場所まで値があるように見せてしまう。生データを三角形単位で塗って見せたい
- 理論式や機械学習モデルの予測 f(a, b, c) を三角形全体に描きたい利用者は、自分で格子を作って評価する必要がある。python-ternary の `heatmapf` に当たる機能がない

## Current State

- `contour` は `tricontourf` / `tricontour` に 101 段階の levels を与えて補間する。`z_min` / `z_max`（別名 `vmin` / `vmax`）とカラーバーの自動追加がある
- `scatter` は `z` で点を色分けする
- 三角形の格子を作る機能はない

## Desired Outcome

- `td.tripcolor(vector, z, **kwargs)` で、測定点から三角形分割して、補間せずに色を塗れる（`shading` は matplotlib と同じく flat / gouraud）
- `td.heatmapf(func, scale=..., **kwargs)` で、三角形内の正則な格子上で関数を評価して塗れる
- どちらも `z_min` / `z_max`（`vmin` / `vmax`）とカラーバーの扱いが既存の `scatter` / `contour` とそろっている
- 戻り値は matplotlib のネイティブオブジェクトで、`TernaryDiagram.colorbar()` にそのまま渡せる

## Approach

A 案（今の設計を広げる）に沿って、`_TripcolorPlotter` と関数ヒートマップ用の Plotter を追加する。値の範囲は既存の `_merge_alias` で扱い、描画後処理とカラーバーは `plot-side-effects` の方針に従う。正則な三角格子の生成は `utils` の純粋関数にする。

matplotlib 3.10 で、`Axes.tripcolor` に `Triangulation` と三角形ごとの `facecolors` を渡す方法で両方とも描けることを確認済み。

設計で決めること:

- 関数の受け取り方（`func(a, b, c)` に配列を渡すか、1 点ずつ呼ぶか）
- `scale`（格子の細かさ）の既定値と、三角形の頂点で評価するか重心で評価するか
- メソッド名（`tripcolor` / `heatmap` / `heatmapf`）

## Scope

- **In**: 散布データのヒートマップ、関数のヒートマップ、三角格子の生成関数、値の範囲とカラーバーの統一、テスト、docstring、CHANGELOG
- **Out**:
  - 六角形のヒートマップ（python-ternary の hexagonal）
  - 辞書でデータを渡す API
  - matplotlib にない補間方法

## Boundary Candidates

- 散布データのヒートマップ
- 関数のヒートマップと三角格子の生成

## Out of Boundary

- カラーバーの追加方針そのもの。`plot-side-effects` が持つ
- 等高線（`contour`）の挙動の変更

## Upstream / Downstream

- **Upstream**: `plot-side-effects`（描画後処理とカラーバー方針）
- **Downstream**: `user-guide-docs`（ヒートマップと等高線の使い分けのページ）

## Existing Spec Touchpoints

- **Extends**: なし
- **Adjacent**: `region-plots`（同じく新しい Plotter を追加する。zorder の定数を一緒に整理する）

## Constraints

- scipy などの依存を足さず、numpy のベクトル演算で格子を作る
- `scale` が 100 程度（約 1 万個の三角形）でも実用的な速さで描ける
