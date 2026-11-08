# Product Overview

`ternary-diagram` は、matplotlib 上で三元系の三角図（ternary diagram）を手軽に描くための Python ライブラリ。pymatgen のような重い依存を持たず、`numpy` と `matplotlib` だけで動くことが最大の特徴。主な利用者は材料科学・化学の研究者で、三成分の組成比とそれに対応する物性値を可視化する用途を想定している。

## Core Capabilities

- **三角図の土台生成**: 外枠、10% 刻みのグリッド、軸目盛り、頂点ラベルをインスタンス生成だけで描画。5 つの部品（外枠・グリッド・目盛りラベル・軸タイトル・頂点ラベル）は、作成時の `*_kw` か後からの `set_*` で見た目（表示、間隔、書式、matplotlib のプロパティ）を変えられ、描いた artist も取り出せる
- **組成データのプロット**: 散布図（物性値によるカラーマップ付き）、等高線図（塗りつぶし / 線）、タイライン、注釈
- **化学式の自動整形**: `Li2O` → `Li$_{2}$O` のように数字を下付きの LaTeX 表記へ変換（`auto_latex_notation=False` で無効化）
- **matplotlib との透過的な統合**: 任意の `Axes` に描画でき、`**kwargs` はそのまま matplotlib に渡り、戻り値も matplotlib のネイティブオブジェクト

## Target Use Cases

- 実験や計算で得た三成分系の組成と物性値（イオン伝導度など）の分布を、等高線や散布図で示す
- 論文・発表用の図を、既存の matplotlib ワークフロー（`plt.subplots` による複数パネル配置、`savefig`）の中で作る
- 組成比を正規化せずにそのまま渡す（合計が 1 でなくてよい）探索的な可視化

## Value Proposition

- **軽量**: ランタイム依存は `numpy>=1.20` と `matplotlib` のみ
- **学習コストが低い**: matplotlib の知識がそのまま使える薄いラッパー
- **広い互換性**: Python 3.9〜3.14、matplotlib 3.7 前後の API 差異も吸収
- **入手しやすい**: PyPI と conda-forge の両方で配布

## Product Boundaries

- 描画ライブラリであり、相図計算や熱力学計算は扱わない
- 公開 API は `TernaryDiagram` クラス 1 つに集約する。新しい描画種別もこのクラスのメソッドとして追加する
- matplotlib の機能を隠さない。独自オプションは三角図特有のもの（`z_min` / `z_max`、`colorbar`、`annotations`、土台の `step` / `fmt` など）に限り、見た目は matplotlib のプロパティとして素通しする

---
_Focus on patterns and purpose, not exhaustive feature lists_

_updated_at: 2026-10-20 — Python 3.9+, setuptools-scm, offline test suite, MyST-NB docs への移行を反映_
_updated_at: 2026-11-08 — diagram-customization（土台の部品化 `_skeleton.py`、`set_*` / `*_kw` / 取り出し口）を反映_
