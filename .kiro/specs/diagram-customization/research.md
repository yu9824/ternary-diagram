# Research & Design Decisions

## Summary
- **Feature**: `diagram-customization`
- **Discovery Scope**: Extension（既存の `TernaryDiagram.__init__` の描画を部品化し、公開 API を足す。新しい依存はない）
- **Key Findings**:
  - 現行の土台は「グリッド 27 本 → 外枠 3 本 → 頂点ラベル 3 個 → 目盛りラベル 27 個」の順に、`ax.plot` / `ax.text` で描かれている。線の zorder は `DEFAULT_ZORDER_GRIDS`（1）、文字は matplotlib の既定（3）。外枠とグリッドは同じ zorder なので、重なりは追加順で決まり、外枠がグリッドより手前に来ているのは「後から追加したから」にすぎない
  - 目盛りラベルの配置は「成分 k の目盛りは、成分 (k+1) mod 3 が 0 になる辺に付く」という 1 つの規則で表せる（成分 0 → 右辺、成分 1 → 左辺、成分 2 → 底辺。値は反時計回りに増える）。グリッド線も「成分 k = v の線は、成分 (k+1) mod 3 = 0 の辺上の点と成分 (k+2) mod 3 = 0 の辺上の点を結ぶ」と書け、`three2two` だけで純粋関数にできる
  - matplotlib の公開 API（`Artist.remove`、`Axes.add_line`、`Axes.update_datalim`、`Axes.autoscale_view`、`cbook.normalize_kwargs`）だけで、部品の描き直し・重なり順の維持・表示範囲の維持・kwargs の別名統合ができる

## Research Log

### 現行の土台の描画内容（特性の固定）
- **Context**: 既定の見た目を変えない（要件 1.1）ために、何を固定すべきかを洗い出す
- **Sources Consulted**: `src/ternary_diagram/_api.py`（`TernaryDiagram.__init__`）、`tests/test_ternary_diagram.py`、Agg バックエンドでの実測（matplotlib 3.10.8、numpy 2.4.6）
- **Findings**:
  - 線: グリッド `color="gray", lw=0.5, zorder=1` を i=1..9 で 3 本ずつ、外枠 `color="black", lw=2, linestyle="-", zorder=1` を 3 本。`solid_capstyle` は rcParams 既定の `projecting`
  - 頂点ラベル: 上 `(0.5, √3/2+0.02)` `ha=center, va=bottom`、左下 `(0, -0.05)` `ha=right, va=top`、右下 `(1, -0.05)` `ha=left, va=top`、いずれも `fontsize=16`
  - 目盛りラベル（i=1..9、文字列は `"%d0" % i`、`fontsize=10`）:
    - 右辺（成分 0 = i/10）: 辺上の点そのもの、`va=bottom, ha=left`、回転なし
    - 左辺（成分 1 = i/10）: 辺上の点 + `(-0.01, +0.04)`、`rotation=300, va=top, ha=right`
    - 底辺（成分 2 = i/10）: 辺上の点 + `(+0.02, 0)`、`rotation=60, va=top, ha=right`
    - 追加順は値ごとに「右辺 → 左辺 → 底辺」
  - 表示範囲: 描画後の xlim ≈ (-0.139, 1.139)、ylim ≈ (-0.043, 0.909)（`set_aspect("equal", adjustable="datalim")` と線のデータ範囲から決まる）
  - `__init__` は色のサイクルを進めない（直後の `ax.plot` は `#1f77b4`）
  - 既存の utils の doctest は numpy 2.4 で全件成功するが、CI の `pytest -xs .` は doctest を実行していない
- **Implications**: 特性テストで「線分の集合・色・線幅・線種・zorder」「文字列・位置・回転・文字揃え・フォントサイズ・zorder」「部品間の追加順」「描画後の表示範囲」を固定してからリファクタする。doctest は `plot-side-effects` が作る共通ランナー `tests/test_doctests.py` で CI 実行する（当初は `tests/test_utils.py` から `doctest.testmod` を呼ぶ案だったが、cross-spec review で共通ランナーに一本化した。下の「Cross-spec review での変更」）

### 描き直しと重なり順
- **Context**: 部品を描き直しても重なり順が変わらないようにする（要件 9.1, 9.2）
- **Sources Consulted**: matplotlib 3.10 の `Axes.draw`（zorder による安定ソート）、`Artist.remove`、`Axes.add_line` の実装。実測で検証
- **Findings**:
  - 同じ zorder の artist は `Axes` への追加順に描かれる。グリッドを描き直すと新しいグリッド線は外枠より後ろに追加され、外枠の上に描かれてしまう。`projecting` の線端がはみ出し、黒い外枠の上に灰色の点が出る
  - 同じ `Line2D` を `remove()` してから `ax.add_line()` で戻すと、オブジェクトの同一性・ラベル・データ範囲を保ったまま末尾へ移せる（`ax.lines[-3:]` が元の外枠になることを確認）
- **Implications**: グリッドを描き直した後に外枠を同じオブジェクトのまま積み直す（restack）。利用者が外枠の artist に加えた変更も失われない

### 表示範囲の維持
- **Context**: 外枠やグリッドを消しても三角形の表示範囲を保つ（要件 9.4）
- **Findings**: 空の Axes で `ax.update_datalim([(0,0),(1,0),(0.5,√3/2)])` と `ax.autoscale_view()` を呼ぶと、外枠を描いた場合と同じ xlim / ylim になる（実測で一致）。外枠を描く通常の場合もデータ範囲の和は変わらないので、既定の見た目に影響しない
- **Implications**: `_Skeleton` の構築時に三角形の頂点をデータ範囲へ登録し、自動スケールを要求する

### kwargs の別名と統合
- **Context**: 作成後の変更で、指定しなかった項目は直前の設定を引き継ぐ（要件 2.4）。別名（`lw` と `linewidth`）が混ざると matplotlib が `TypeError` を出す
- **Sources Consulted**: `matplotlib.cbook.normalize_kwargs` の docstring（`alias_mapping` に Artist のサブクラスを渡せる）
- **Findings**: `normalize_kwargs({"lw": 0.5}, Line2D)` → `{"linewidth": 0.5}`、`normalize_kwargs({"ha": "left", "size": 3}, Text)` → `{"horizontalalignment": "left", "fontsize": 3}`。同じ辞書に別名と正式名が両方あると `TypeError`
- **Implications**: 既定値と利用者の指定を正式名にそろえてから統合する。両方を同時に渡す誤りは matplotlib のエラーとしてそのまま送出する（要件 10.7）

### 目盛りの書式の先例
- **Context**: 目盛りの書式を書式文字列にするか関数にするか（brief の設計判断）
- **Sources Consulted**: `matplotlib.axes.Axes.bar_label` の `fmt`（3.7 以降、%-style と {}-style の書式文字列、または値を受け取る関数。両方に解釈できるときは %-style を優先）、`Axis.set_major_formatter`（文字列は `{x}` を使う StrMethodFormatter）
- **Findings**: matplotlib 自身が「書式文字列でも関数でもよい」という `fmt` の先例を持つ
- **Implications**: `fmt` は `bar_label` に合わせ、%-style → {}-style（`{}` と `{x}` の両方）→ 関数を受け付ける。よく使う 2 つは名前（`"percent"`、`"fraction"`）で指定できるようにする

### 軸タイトルと両端の目盛りの配置（試作）
- **Context**: 新しく描く軸タイトルと両端の目盛りラベルの既定の位置を決める
- **Sources Consulted**: scratchpad での試作描画（6×5 インチ、dpi 90）
- **Findings**:
  - 軸タイトルを辺の中点から外向きの法線方向へ 0.12〜0.16 離すと、目盛りラベルとも頂点ラベルとも重ならない。0.15 を既定にする。回転は右辺 300°、左辺 60°、底辺 0° で逆さにならない
  - 両端の目盛りラベルを現行の規則のまま置くと、左下の頂点で左辺の「100」と底辺の「0」が近接し、図が小さいと一部が重なる。上と右下の頂点では読める
- **Implications**: 両端の表示は既定で無効のままにし、近接は既知の制約として docstring に書く。個別の調整は `tick_labels_` の artist で行える

### Cross-spec review での変更（2026-10-22）
- **Context**: roadmap に「Implementation Order」と「横断の取り決め」が加わり、steering の tech.md に「Docstring Examples」と新規モジュールの型注釈の規約が加わった。本 spec をそれに合わせる
- **Sources Consulted**: `.kiro/steering/roadmap.md`、`.kiro/steering/tech.md`、`.kiro/specs/plot-side-effects/design.md`（`tight_layout`、`check_optional_bool`、`td` fixture、`__init__` の統合点）
- **Findings / Decisions**:
  - 実装順: `plot-side-effects` が先にマージされ、`__init__` に `tight_layout` を足す。本 spec はその後に `*_kw` を `tight_layout` の後ろへ足す。「後に入る側が合わせる」という取り決めはやめ、最終形 `(materials, ax=None, auto_latex_notation=True, *, tight_layout=None, border_kw=None, grid_kw=None, tick_kw=None, axis_label_kw=None, vertex_label_kw=None)` と検証の順 `ax` → `materials` → `tight_layout` → `*_kw` に固定した
  - `__init__` の docstring: 本 spec が書くのは 5 つの `*_kw` の Parameters の項目だけ。Examples 節は `user-guide-docs` だけが持つ。`*_kw` の使用例は対応する `set_*` の docstring に置き、作成時の `<part>_kw` がその `set_*` の呼び出しと同じ意味であることを書く（要件 12.1 を改めた）
  - docstring の例: tech.md の「Docstring Examples」に従い、docstring ごとに必要な import の行から始め（下の「2 回目」）、`fig, ax = plt.subplots(layout="constrained")` と `ax=ax` で図を描き、ファイルを書き出さず、FutureWarning を出さない。実行は共通ランナー `tests/test_doctests.py` に任せ、本 spec の `doctest.testmod` のテストはやめた（要件 12.4 を追加）。`utils` の 5 関数は図を使わないので、図を作らずに関数を呼ぶ例にする
  - 真偽値の検証（`visible`、`endpoints`）は、`plot-side-effects` が足す `utils.check_bool(value, name)` を使う。独自の判定は書かない
  - テスト: `plot-side-effects` が `td` fixture を `tight_layout=True` にする。描画メソッドを呼ぶテストは `td` を使うか `tight_layout=True` を明示し、FutureWarning をエラーにしても通るようにする
  - `_skeleton.py` は新規モジュールなので `from __future__ import annotations` と組み込みジェネリクス・`X | None` を使う。実行時に評価される型別名（`Spec`）は Python 3.9 で `|` が使えないので `typing.Union` のままにする
  - CHANGELOG: `plot-side-effects` がそろえる `Unreleased` の見出しの組（Breaking changes / New features / Deprecations / Bug fixes / Other changes）に従い、追加した API は New features に書く。`materials` の要素不足のエラーの変化（`IndexError` → `ValueError`）は、既存の「Malformed inputs raise `ValueError`」と同じ Bug fixes に書く
  - `user-guide-docs` が Sphinx の `autoclass_content="both"` を設定すると、クラスの docstring の Notes と `__init__` の Parameters の表示順が変わる。Revalidation Trigger に加えた
- **Implications**: design の Boundary Commitments、構築のフロー、`TernaryDiagram` のシグネチャと Implementation Notes、「`*_kw` と `set_*` の対応」「Docstring Examples」、Testing Strategy と、tasks の各タスクの `_Boundary:_` をファイルとシンボルの粒度に改めた

### Cross-spec review での変更（2026-10-22、2 回目）
- **Context**: tech.md の「Docstring Examples」に、例を docstring ごとに import の行から始める規則と、Parameters の書き方の規則が加わった。roadmap では本 spec の依存が `plot-side-effects` と明記された
- **Sources Consulted**: `.kiro/steering/tech.md`（Docstring Examples）、`.kiro/steering/roadmap.md`、`.kiro/specs/plot-side-effects/design.md`（DoctestRunner の収集対象と名前空間）
- **Findings / Decisions**:
  - 共通ランナーは docstring ごとに定義元のモジュールの globals の写しで実行し、名前を足さない。`_api.py` は `matplotlib.pyplot` を import していないので、`set_*` の例は docstring ごとに `>>> import matplotlib.pyplot as plt` と `>>> from ternary_diagram import TernaryDiagram` から始める。同じ docstring の 2 つ目のブロック（作成時の `*_kw` の例）は先頭の import を使う。取り出し口のプロパティも収集対象なので、例を書くなら同じく自分の import から始める
  - `utils` の 5 関数の例は、使う名前を `>>> from ternary_diagram.utils import ...` で import してから呼び、図を作らない。定義元のモジュールの globals にあるので import がなくても通るが、規則に合わせ、確認はレビューで行う
  - Parameters: `*_kw` と `set_*` の名前付き引数は既定値が `None` なので、意味（`*_kw` は `set_*` と同じ意味であること、`set_*` は `None` で直前の設定を引き継ぐことと作成時の初期値）を書いた文の後に `, by default None` を添える。`**kwargs` には `, by default` を付けない
  - 実装順: `plot-side-effects` の後に実装する（spec は並行して作れたが、実装は並行しない）。代替案の比較表にあった「並行開発で衝突しやすい」という書き方を、同じ `_api.py` を編集する他 spec との衝突に改めた
- **Implications**: design の「Docstring Examples」を改め、「Docstring Parameters」を足し、`utils` の Implementation Notes、Testing Strategy の Doctest、tasks 2.1 / 2.2 / 4.3、要件 12.4 の規約の列挙をこれに合わせた

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| 部品クラス + 集約（採用） | 部品ごとに設定と artist を持つクラスを作り、`_Skeleton` が構築順と積み直しを管理する。`TernaryDiagram` は引数の受け口だけ | 部品の責務が明確。`_api.py` の差分が小さく、先にマージされる `plot-side-effects` の変更の上に載せやすい。後に続く `region-plots` / `heatmaps` の `_api.py` の変更とも衝突しにくい | クラス数が増える（基底 1 + 部品 5 + 集約 1） | roadmap の A 案に沿う |
| `TernaryDiagram` に直接メソッドを書く | `set_*` の中で直接描き直す | ファイルが増えない | `_api.py` が肥大化し、同じファイルを編集する他 spec の変更と衝突しやすい。設定の統合と巻き戻しを 5 回書くことになる | 不採用 |
| matplotlib の `Axis` / `Tick` を流用 | 三角形の各辺を `Axis` として扱う | matplotlib の目盛り機構が使える | 実質 projection 化で、brief の対象外（mpltern と競合） | 不採用 |
| スタイルオブジェクト（C 案） | `TernaryStyle` で見た目を一括指定 | 使い回しやすい | roadmap で不採用が決まっている | 不採用 |

## Design Decisions

### Decision: `*_kw` 引数は対応する `set_*` メソッドへそのまま渡す
- **Context**: 作成時と作成後で同じ項目を同じ名前で受け付ける（要件 2.1, 2.2）
- **Alternatives Considered**:
  1. 作成時に部品ごとの専用引数（`grid_step=` など）を並べる
  2. `<part>_kw` を `set_<part>(**<part>_kw)` と同じ意味にする
- **Selected Approach**: 2。`border_kw` → `set_border`、`grid_kw` → `set_grid`、`tick_kw` → `set_ticks`、`axis_label_kw` → `set_axis_labels`、`vertex_label_kw` → `set_vertex_labels`。新しい引数はすべてキーワード専用
- **Rationale**: matplotlib の `subplot_kw` / `gridspec_kw` と同じ「辞書を下位の呼び出しへ渡す」規則で、覚えることが 1 つで済む。`__init__` の引数が増え続けない
- **Trade-offs**: 軸タイトルの文字列も `axis_label_kw={"labels": ...}` と辞書に入れる必要がある。作成後の `set_axis_labels([...])` で補える
- **Follow-up**: `vertex_label_kw` に `labels` を入れると `materials` と衝突するため `ValueError` にする

### Decision: 作成後の変更は直前の設定に統合する（merge）
- **Context**: 「フォントサイズだけ変えたい」ときに間隔や書式を指定し直させない（要件 2.4, 2.6）
- **Alternatives Considered**:
  1. 指定しなかった項目は既定値に戻す（replace）
  2. 指定しなかった項目は直前の値を引き継ぐ（merge）
- **Selected Approach**: 2。名前付き引数は `None` を「変更しない」とし、matplotlib のプロパティは正式名にそろえて上書き統合する
- **Rationale**: matplotlib の `Axes.grid(**kwargs)` もスタイルを保持する。非表示 → 表示で元に戻る
- **Trade-offs**: 一度指定したプロパティを「未指定」に戻す手段はない（既定値を明示して上書きする）
- **Follow-up**: docstring に「指定しなかった項目は直前の設定を引き継ぐ」と明記する

### Decision: 目盛りの書式は名前・書式文字列・関数のいずれか
- **Context**: brief の設計判断「書式文字列か関数か」（要件 6.3〜6.5, 10.4）
- **Selected Approach**: `fmt` は次の順に解釈する。(1) `"percent"`（既定。値 × 100 を `g` 書式で表示し、不要な桁を出さない）、(2) `"fraction"`（値を `g` 書式で表示）、(3) 文字列なら %-style を試し、失敗したら {}-style（`{}` / `{x}`）、(4) 呼び出し可能なら値を渡した戻り値。関数に渡す値は常に 0〜1 の割合
- **Rationale**: `bar_label(fmt=...)` と同じ解釈順で matplotlib 利用者に馴染みがある。名前付きの 2 つで brief の「パーセント / 割合」を直接満たす
- **Trade-offs**: %-style に割合を渡すため、`"%d"` は 0 になる。docstring で「値は割合」と明記し、百分率は `"percent"` か `"{:.0%}"` を勧める
- **Follow-up**: `%` も `{` も含まない文字列（名前以外）と、試しの値 0.5 で整形に失敗する文字列は `ValueError`

### Decision: 目盛りの配置は現行に固定する
- **Context**: brief「目盛りがどの辺に付き、どの成分を表すか（今の配置を既定とし、ドキュメントに明記する）」
- **Selected Approach**: 成分 0 → 右辺、成分 1 → 左辺、成分 2 → 底辺、値は反時計回りに増える。変更する引数は設けず、`TernaryDiagram` と `set_ticks` の docstring に明記する
- **Rationale**: 要件の範囲で配置の切り替えは求められていない。引数を増やさない
- **Trade-offs**: 時計回りの規約を使いたい利用者には対応しない（将来の拡張候補）

### Decision: 軸タイトルは化学式に自動整形しない
- **Context**: `auto_latex_notation` の意味を変えない制約と、`get_label` が普通の文字列まで変換する既知の問題（roadmap の annotate-plain-text）
- **Selected Approach**: 軸タイトルは与えられた文字列をそのまま表示する。化学式を下付きにしたい場合は利用者が mathtext を書く
- **Rationale**: 「Li2O / mol%」のように単位を含む文字列では誤変換の余地がある。`auto_latex_notation` は頂点ラベルだけに効くという今の意味を保てる

### Decision: グリッドを描き直したら外枠を積み直す
- **Context**: 要件 9.2。zorder を変えずに重なり順を保つ
- **Alternatives Considered**:
  1. 外枠の zorder を `DEFAULT_ZORDER_GRIDS` より少し大きくする
  2. グリッドの描き直しのたびに外枠も新しく描く
  3. 外枠の既存の artist を remove → add_line で末尾へ移す
- **Selected Approach**: 3
- **Rationale**: 1 は「部品の zorder は `DEFAULT_ZORDER_GRIDS` を保つ」制約に反する。2 は外枠の artist が勝手に置き換わり、利用者が加えた変更が消える。3 は公開 API だけで、オブジェクトの同一性も保てる
- **Trade-offs**: 利用者が zorder 1 で追加した線との前後関係は、積み直しで変わりうる（まれ）

### Generalization（synthesis）
- 5 つの部品は「既定の設定 → 統合 → 検証 → 図形の仕様（純粋に計算）→ artist の生成 → 古い artist の削除」という同じ手順の変種なので、基底クラス `_SkeletonPart` に手順をまとめ、部品は「既定値」「検証」「図形の仕様の計算」だけを持つ
- 目盛り・グリッド・軸タイトルの位置は、すべて「成分 k の辺」を基準にした計算の変種なので、utils に `get_edge_points` を置き、他の関数はそれを使う

### Build vs. Adopt（synthesis）
- 目盛りの値の生成に `matplotlib.ticker.MultipleLocator` を使う案は、Axis に結び付いた API で、三角形の 0〜1 の範囲に合わせる調整が必要になるため採らない。値の列は numpy の 1 行で作れる
- kwargs の別名統合は `matplotlib.cbook.normalize_kwargs` を採用する（自作しない）
- 書式文字列の解釈は `bar_label` の内部関数（非公開）を使わず、同じ規則を数行で実装する

### Simplification（synthesis）
- 目盛り線（短い刻み線）、目盛りの辺ごとの切り替え、辺ごとの書式は要件にないので設けない
- 線用・文字用の中間基底クラスは作らず、「図形の仕様」を `_LineSpec` / `_TextSpec` の 2 種類にして基底クラスで生成を振り分ける
- 設定の取得 API（`get_grid()` など）は要件にないので設けない。取り出せるのは artist だけ

## Risks & Mitigations
- 両端の目盛りラベルが左下の頂点で近接する — 既定は無効。docstring に制約と `tick_labels_` での調整方法を書く
- 同じ zorder の利用者の artist との前後関係: 描き直した文字の部品（zorder 3）は、先に描かれた散布図（zorder 3）より手前に来る — 目盛りラベルは三角形の外側にあり重なりはまれ。既知の制約として docstring に書く
- `normalize_kwargs` に Artist クラスを渡す呼び方が古い matplotlib にない可能性 — 実装時に CI の全 Python バージョンで確認し、必要なら `Artist.get_aliases` 相当の辞書で代替する分岐を置く
- グリッド線の始点と終点の向きが一部 v3 と逆になる — 実線では見た目に差はない。特性テストは線分を向きのない端点の組として比べる
- 軸タイトルの既定の距離（0.15）とフォントサイズ（12）は既定の図の大きさで目視確認した値 — 実装時に example の図でも確認する

## References
- [matplotlib.axes.Axes.bar_label](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.bar_label.html) — `fmt` の先例（%-style / {}-style / callable）
- [matplotlib.cbook.normalize_kwargs](https://matplotlib.org/stable/api/cbook_api.html#matplotlib.cbook.normalize_kwargs) — kwargs の別名統合
- [matplotlib.axes.Axes.update_datalim](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.update_datalim.html) — 表示範囲の登録
- [matplotlib.artist.Artist.remove](https://matplotlib.org/stable/api/_as_gen/matplotlib.artist.Artist.remove.html) — artist の削除
- `.kiro/steering/roadmap.md` — A 案の採用、zorder 定数と `_api.py` の共有に関する注意
