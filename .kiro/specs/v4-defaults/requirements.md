# Requirements Document

## Project Description (Input)

**誰が困っているか**: `ternary-diagram` の利用者（matplotlib で三角図を描く材料科学・化学の研究者）と、v4.0.0 を出すメンテナ。

**今の状況**:

- v3.x の既定値（エンジンのない図で描画ごとに `tight_layout()`、`z` 付きの描画ごとにカラーバーを自動追加）は、利用者のレイアウトを上書きし、カラーバーを重複させる。v3.2.1 から FutureWarning で v4.0.0 での変更を予告しており、非推奨の `flag_cbar` も残っている（CHANGELOG の Deprecations、`docs_src/user_guide/migration_v4.md`）
- `PostDrawContext.has_colorbar` は、登録済みのカラーバーと同じ mappable に利用者が `fig.colorbar` で別のカラーバーを足すと、登録済みのものを削除済みと判定する。v3.x では重複の FutureWarning が出ないだけだが、v4.0.0 の既定（既存ありなら自動追加しない）では 1 本余分に付く
- ロードマップより前からあるメソッドはオプションを位置引数でも受け付ける（`TernaryDiagram` の `ax` / `auto_latex_notation`、`scatter` / `contour` の `z_min` 以降、`colorbar` の `shrink` 以降）。後から足したメソッド（`tripcolor` / `heatmapf` / `set_*` など）はキーワード専用で、API が揃っていない。`scatter` / `contour` の 6 番目の位置引数は v3.2.1 から意味が変わった（`colorbar`）
- 三角図の縦横比を `adjustable="datalim"` で固定しているため、matplotlib 3.11 では constrained layout にカラーバーが付く図で、左下の頂点ラベルが図の端からはみ出す（README の例の図で左の余白が 0px。`adjustable="box"` ならどちらの版でも 8〜9px）

**何を変えるか**: v3.x での予告（FutureWarning）と v4.0.0 での切り替えの 2 段で、次の破壊的変更をまとめて行う。

1. 既定値の切り替え: `_post_draw.py` の決定表の未指定の行を v4 の値にし、非推奨の `flag_cbar` を削除する
2. `PostDrawContext.has_colorbar` の判定を直す
3. オプション引数のキーワード専用化: データ（`materials`、`vector`、`z`、`text`、`func`、`mappable`、`set_*` の先頭の引数）だけを位置引数に残す。v3.4.0 から、キーワード専用にする引数を位置引数で渡したときに `warn_external` で FutureWarning を出す
4. 縦横比の固定を `adjustable="box"` に変える（凡例の `loc` の位置と自動で付くカラーバーの長さが変わる）

CHANGELOG の Deprecations と移行ページ（`docs_src/user_guide/migration_v4.md`）を更新する。出典は `.kiro/steering/roadmap.md` の「Deferred to v4.0.0」。

## Requirements
<!-- Will be generated in /kiro-spec-requirements phase -->
