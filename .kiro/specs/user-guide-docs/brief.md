# Brief: user-guide-docs

## Problem

使い方を知る手段が少ない。docstring には説明が空の引数（`, by default None` だけのもの）が多く、`contour` の `fill` と `flag_cbar` は説明すらない。ドキュメントサイトは API の自動生成とサンプルノートブックだけで、「軸タイトルを付けたい」「相図を描きたい」といった目的から使い方をたどれない。README は同じコードを 2 回載せていて長い。新しい機能（カスタマイズ、相図、ヒートマップ、副作用の制御）が増えるほど、この問題は大きくなる。

## Current State

- ドキュメントは Sphinx + MyST-NB + sphinx-book-theme（Jupyter Book 形式）。ノートブックは実行せず、保存済みの出力を表示する
- `docs_src/tutorials/` は `example/` のノートブックへのシンボリックリンク
- API リファレンスは CI で sphinx-apidoc が生成する
- `_templates/layout.html` がフッターに広告スクリプトを差し込んでいる

## Desired Outcome

- すべての公開メソッドと引数に、意味・既定値・例が書かれた docstring がある
- 目的別の使い方ページがある。例: はじめに、見た目の変え方、相図の描き方（`fill` / `text`）、ヒートマップと等高線の使い分け、レイアウトとカラーバー（v4.0.0 への移行方法を含む）
- README は概要・インストール・最小の例・ドキュメントへのリンクに絞られている
- ドキュメントが警告なしでビルドでき、広告スクリプトも残っている

## Approach

各 spec は自分が追加する API の docstring を自分で書く。この spec は、既存メソッドの docstring の不足を埋めて全体の書き方をそろえ、MyST の Markdown ページまたはノートブック（jupytext で py:percent と対にする）で使い方ページを作り、README を刷新する。

設計で決めること:

- 使い方ページをノートブックにするか Markdown にするか、ノートブックを CI で実行するか（`nb_execution_mode`）
- サンプルノートブック（`example/`）と使い方ページの役割分担

## Scope

- **In**: 既存メソッドの docstring の充実と書き方の統一、使い方ページ、ドキュメントの目次の整理、README の刷新
- **Out**:
  - mpltern / python-ternary との使い分け表
  - 日本語ドキュメント
  - ホスティングの変更（Read the Docs への移行など）

## Boundary Candidates

- docstring（API リファレンスの中身）
- 使い方ページ（目的別のガイド）
- README

## Out of Boundary

- 新しい API の docstring。その API を追加する spec が書く
- テーマやビルドの仕組みの変更。3d のブランチで移行済み

## Upstream / Downstream

- **Upstream**: `plot-side-effects`、`diagram-customization`、`region-plots`、`heatmaps`、直接実装の `annotate-plain-text`（化学式の整形の規則）
- **Downstream**: v4.0.0 のリリース（移行方法のページを参照する）

## Existing Spec Touchpoints

- **Extends**: なし
- **Adjacent**: 1〜4 の各 spec（それぞれの docstring と重複させない）

## Constraints

- docstring は NumPy スタイルの英語
- 正式版タグで GitHub Pages にデプロイされる今の仕組みを保つ
- テーマを変える場合も、フッターの広告スクリプトが残ることを確認する
