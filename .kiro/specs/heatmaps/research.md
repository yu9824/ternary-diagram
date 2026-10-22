# Research & Design Decisions: heatmaps

## Summary
- **Feature**: `heatmaps`
- **Discovery Scope**: Extension（既存の Plotter パターンに描画種別を 2 つ足す。外部依存は増やさない）
- **Key Findings**:
  - matplotlib の `Axes.tripcolor` は `Triangulation` を第 1 引数に取り、点ごとの値（flat では 3 頂点の平均、gouraud では線形補間）と、三角形ごとの値（`facecolors=`、flat のみ）の両方を描ける。戻り値は flat で `PolyCollection`、gouraud で `TriMesh`。どちらも `Triangulation.mask` を尊重する
  - `scale=100`（1 万個の小三角形）の格子生成と `tripcolor` は合計 0.05 秒程度で、要件 8.1 の 1 秒に十分な余裕がある。numpy のベクトル演算だけで格子を作れる
  - flat の既定の色の範囲は matplotlib に任せると「三角形ごとの平均値」の最小・最大になり、`scatter` / `contour`（`z` の最小・最大）とずれる。範囲を自前で計算して `vmin` / `vmax` として渡す必要がある

## Research Log

### matplotlib `tripcolor` の入力と戻り値
- **Context**: `tripcolor` と `heatmapf` の両方を 1 つの matplotlib 関数で描けるか、ブリーフの「確認済み」を実装の観点で確かめる
- **Sources Consulted**: matplotlib 3.10.8 の `matplotlib/tri/_tripcolor.py`（ローカル環境の py312）、読み取り専用の動作確認スクリプト
- **Findings**:
  - 呼び出し形: `tripcolor(triangulation, c, *, shading, facecolors, vmin, vmax, norm, cmap, **kwargs)`。`c` の長さが点の数と一致すれば点の値、三角形の数と一致すれば三角形の値として扱う（点の数を優先）
  - `facecolors=` を渡すと三角形ごとの値として扱う。`shading="gouraud"` と `facecolors` の組み合わせは `ValueError`
  - flat で点の値を渡すと、各三角形の色は 3 頂点の値の平均（`point_colors[maskedTris].mean(axis=1)`）
  - flat は `tri.get_masked_triangles()` でマスクした三角形を除き、`facecolors` もマスク分を除く。gouraud の `TriMesh` も描画時に `get_masked_triangles()` を使う
  - `vmin` / `vmax` と `norm` を同時に渡すと `_scale_norm` が `ValueError`。この時点では Axes に何も追加されていない
  - `c` を kwargs で渡すと `PolyCollection.set() got an unexpected keyword argument 'c'`（`AttributeError`）。`flag_cbar` など未知の名前も同様
  - `tripcolor` は内部で `ax.grid(False)`、`update_datalim`、`autoscale_view` を呼ぶ。ternary-diagram は matplotlib の軸グリッドを使わないので影響しない
  - 既定の `edgecolors="none"`、`antialiased=False`、`linewidths=0.25`。PDF ビューアで継ぎ目が見える場合は利用者が `edgecolors="face"` を渡せる（ライブラリでは既定を変えない）
- **Implications**: 2 つの描画を共通の描画手順（三角形分割 + 点または三角形の値 + マスク + 範囲）にまとめられる。kwargs の衝突（`c`、`facecolors`、`flag_cbar`）は matplotlib に届く前に検証する

### 欠損値・無限大・退化した入力
- **Context**: 要件 1.6–1.8 と 4.1–4.3 の挙動を matplotlib の既定と比べる
- **Findings**:
  - matplotlib 3.10 では `set_array` が NaN / inf をマスクするので、flat の点の値で NaN を含む三角形は「bad」色（既定で透明）になる。gouraud では NaN の頂点に向かって透明へ変化するだけで、三角形は消えない
  - すべて NaN でも例外は出ず、`vmin = vmax = 0` の空の図になる
  - `Triangulation(x, y)` は 3 点未満や異なる点が 3 未満で `ValueError`、一直線上の点で qhull の `RuntimeError`（"singular input data"）を出す
  - 完全に同じ組成の点が複数あると、qhull は 1 点だけを使い、残りはどの三角形にも属さない（値は黙って捨てられる）。example の 3 つの CSV に重複はない
  - `vmin > vmax` でも matplotlib は例外を出さない（`scatter` と同じ）。`vmin == vmax` では `colorbar` が範囲を自動で広げる（1.8–2.2）
- **Implications**:
  - 値を決められない三角形は `Triangulation.mask` で除き、値は `np.ma.masked_invalid` で渡す。matplotlib の版による `set_array` の差に依存せず、flat / gouraud で同じ結果になる
  - 自動の三角形分割の失敗は、理由を示す `ValueError` に変換し、元の例外を `from` でつなぐ（握りつぶさない）
  - 重複は「どの三角形にも使われない点の数」で検出する。qhull の重複判定と一致し、許容誤差を自前で決めずに済む
  - `vmin > vmax` の検証は `scatter` に合わせて行わない

### 速度
- **Context**: 要件 8.1（`scale=100` で関数の評価と保存を除いて 1 秒以内）
- **Sources Consulted**: ローカル計測（Apple Silicon、matplotlib 3.10.8、numpy 2.4.6、Agg）
- **Findings**:

  | scale | 格子点 | 小三角形 | 格子生成 | `tripcolor` 呼び出し | PNG 保存 | PDF 保存 |
  |---|---|---|---|---|---|---|
  | 50 | 1,326 | 2,500 | 0.7 ms | 12 ms | 51 ms | 0.28 s |
  | 100 | 5,151 | 10,000 | 0.5 ms | 43 ms | 61 ms | 0.41 s |
  | 200 | 20,301 | 40,000 | 5 ms | 195 ms | 141 ms | 1.6 s |
  | 400 | 80,601 | 160,000 | 8 ms | 721 ms | 427 ms | 6.0 s |

- **Implications**: 処理時間は `tripcolor`（`PolyCollection` の頂点配列の構築）が支配的で、格子生成は無視できる。ベクトル保存（PDF）は三角形の数に比例して重くなるので、既定の `scale` は控えめにする

### 既存コードと上流・隣接 spec の接点
- **Context**: 規約に従った Plotter の追加と、並行 spec との衝突回避
- **Sources Consulted**: `src/ternary_diagram/_api.py`、`utils.py`、`.kiro/specs/plot-side-effects/design.md`、`.kiro/specs/diagram-customization/design.md`、`.kiro/specs/region-plots/brief.md`
- **Findings**:
  - `_BasePlotter.__init__` は `z` が `None` でないときだけ `self.z_min` / `self.z_max` を設定する。`_merge_alias` は `self.kwargs` から別名を取り出す。どちらも `heatmapf` の値を基底に `z` として渡せばそのまま使える
  - plot-side-effects の規約: `_BasePlotter.__init__(..., *, post_draw_context, **kwargs)`、`__init__` の最後で `self._post_draw(mappable=..., colorbar=...)` を 1 回、`colorbar` は公開メソッドの層で `check_optional_bool` により検証、警告は `_deprecation.warn_external` から出す（`category` 引数あり）
  - plot-side-effects の重複カラーバーの警告文は、当初「`{func}` added another colorbar because `z` was given ...」で、`heatmapf` には `z` 引数がないので文面が合わなかった。cross-spec review で上流が `z` に触れない一般的な文面にすることになった（上流の所有物なので本 spec は変更しない）
  - diagram-customization は `utils.py` に `get_tick_values`、`get_edge_points`、`get_grid_segments`、`get_axis_label_position`、`get_tick_formatter`、`TickFormat` を足し、グリッドの描き直しでは Line2D を `remove()` → `add_line()` し直す（zorder は `DEFAULT_ZORDER_GRIDS` = 1 のまま）
  - region-plots は `DEFAULT_ZORDER_FILL` / `DEFAULT_ZORDER_TEXT` を足す（値は並行して決まる）
- **Implications**: 格子生成関数は `get_triangular_lattice` とし、diagram-customization の名前と重ならないようにする。ヒートマップの zorder は新しい定数で持ち、グリッド（1）より下に置けば土台の描き直しの影響を受けない

### 負の zorder
- **Context**: 既存の `DEFAULT_ZORDER_CONTOUR = 0` より下に置けるか
- **Findings**: Agg で `zorder=-1` の塗りが Axes の背景より手前に描かれることを画素で確認した。Axes の背景（patch）は artist の並べ替えとは別に最初に描かれる。`ax.set_rasterization_zorder(0)` を使う利用者には、ヒートマップだけがラスタ化される（ベクトル保存のファイルが軽くなる）という副次的な利点がある
- **Implications**: `DEFAULT_ZORDER_HEATMAP = -1` を採用できる

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| A. 2 つの Plotter + 共通基底 + 純粋関数モジュール | `_MeshPlotter` が描画手順を持ち、`_TripcolorPlotter` / `_HeatmapfPlotter` は入力の準備だけを持つ。検証と計算は `_mesh.py` の純粋関数 | 規約どおりの Plotter パターン。図なしで単体テストできる。`_api.py` の差分が小さい | 新しいモジュールが 1 つ増える | 採用。plot-side-effects の `_post_draw.py` と同じ考え方 |
| B. 2 つの Plotter に処理を重複して書く | 共通基底もヘルパーも作らない | ファイルが増えない | マスク・範囲・kwargs 検証が 2 か所に分かれ、片方だけ直す事故が起きやすい | 不採用 |
| C. `heatmapf` を `tripcolor` の上に組み立てる | `TernaryDiagram.heatmapf` が格子と値を作り、`_TripcolorPlotter` に渡す | Plotter が 1 つで済む | flat の重心評価は三角形ごとの値なので `tripcolor`（点の値）に載らない。`x_` / `y_` の種類名と警告文の名前が `tripcolor` になる | 不採用 |

## Design Decisions

### Decision: メソッド名は `tripcolor` と `heatmapf`
- **Context**: ブリーフの未決事項（`tripcolor` / `heatmap` / `heatmapf`）
- **Alternatives Considered**:
  1. `tripcolor` と `heatmapf`
  2. `heatmap`（散布データ）と `heatmapf`
  3. 1 つの `heatmap` で引数の型により切り替える
- **Selected Approach**: 1
- **Rationale**: 既存のメソッド（`scatter`・`contour`・`plot`・`annotate`）はラップする matplotlib 関数の名前に合わせている。`heatmapf` は python-ternary から移る利用者に通じる。python-ternary の `heatmap` は辞書を受け取る API（本 spec の範囲外）なので、同じ名前で別の入力を受けると混乱を招く
- **Trade-offs**: 「ヒートマップ」という語で探す利用者は `tripcolor` に気づきにくい。docstring の See Also と `user-guide-docs` の使い分けページで補う

### Decision: 関数は配列で 1 回だけ呼ぶ（`func(a, b, c)`）
- **Context**: ブリーフの未決事項（配列を渡すか、1 点ずつ呼ぶか）
- **Alternatives Considered**:
  1. 3 つの 1 次元配列 `func(a, b, c)` で 1 回だけ呼ぶ
  2. 1 点ずつ `func(a, b, c)` をスカラーで呼ぶ
  3. 形 `(m, 3)` の 1 つの配列 `func(vector)` で呼ぶ（scikit-learn の `predict` 向き）
  4. `vectorized=True/False` の引数で 1 と 2 を切り替える
- **Selected Approach**: 1。戻り値は形 `(m,)`、`(m, 1)`、`(1, m)` を受け付け、マスク付き配列のマスクは NaN として扱う
- **Rationale**: 1 万点を Python の繰り返しで呼ぶと、機械学習モデルの予測では 1 点ごとのオーバーヘッドが支配的になる。numpy の式（`a * np.log(a)` など）はそのまま配列で動く。スカラー専用の関数は `numpy.vectorize` で包めば 1 で扱える。3 は理論式の書き方として不自然で、ブリーフの f(a, b, c) とも合わない。モデルは `lambda a, b, c: model.predict(np.column_stack([a, b, c]))` で渡せる
- **Trade-offs**: スカラー専用の関数を渡すと、関数自身の例外（`TypeError` など）か形の検証の `ValueError` になる。後者のメッセージで `numpy.vectorize` を案内する
- **Follow-up**: Keras などが返す `(m, 1)` を受け付けることをテストで確認する

### Decision: 評価点は塗り方で決める（flat は重心、gouraud は格子点）
- **Context**: ブリーフの未決事項（頂点で評価するか重心で評価するか）
- **Alternatives Considered**:
  1. 常に格子点で評価し、flat は 3 頂点の平均で塗る
  2. 常に重心で評価する（gouraud は使えない）
  3. 塗り方で決める: flat は重心（三角形ごとの値）、gouraud は格子点（点の値）
- **Selected Approach**: 3
- **Rationale**: 混合エントロピー `a ln a` のように辺や頂点（純物質）で定義されない式は材料系で多い。flat の重心評価は辺上で関数を呼ばず、各小三角形の色がその場所の関数値そのものになる。gouraud は点の値が必要なので格子点で評価する。`shading` の名前と意味を `tripcolor` とそろえられ、別の引数を増やさずに済む
- **Trade-offs**: gouraud で辺上の値が有限でない関数は、辺に接する小三角形が塗られない（要件 4.2）。docstring で flat を勧める
- **Follow-up**: 評価点の数（flat は n²、gouraud は (n+1)(n+2)/2）をテストで確認する

### Decision: `scale` の既定値は 50
- **Context**: ブリーフの未決事項（格子の細かさの既定値）
- **Alternatives Considered**: 10（python-ternary と同程度）、50、100
- **Selected Approach**: 50（2,500 個の小三角形、組成の刻み 2%）
- **Rationale**: 10 では flat の段差が目立ち論文用には粗い。100 は描画が速くても PDF 保存が 0.4 秒・ファイルも大きくなる。50 は既存の example（`example/contour/example_contour.csv` は 1,326 点 = 50 分割の格子）と同じ細かさで、組成マップとして十分な分解能がある
- **Trade-offs**: 滑らかさが欲しい場合は gouraud か大きい `scale` を指定する。docstring に速度とファイルサイズの目安を書く

### Decision: 既定の重なり順は新しい定数 `DEFAULT_ZORDER_HEATMAP = -1`
- **Context**: 要件 7.2（呼び出し順によらず、グリッド・外枠・線・散布図・等高線より奥）。region-plots と zorder 定数を分担する
- **Alternatives Considered**:
  1. `DEFAULT_ZORDER_CONTOUR`（0）を再利用する
  2. 新しい定数を 0 と同じ値で持つ
  3. 新しい定数を等高線より下（-1）に置く
- **Selected Approach**: 3。既存の 4 定数の名前・値・並びは変えず、その後ろに追加する
- **Rationale**: ヒートマップの上に等高線（`fill=False`）を重ねるのは定番の組み合わせで、0 を共有すると呼び出し順で線が隠れる。「zorder で呼び出し順によらず重なり順を固定する」という既存の方針（tech.md）に沿うには等高線より下にする必要がある。Axes の背景より手前に描かれることは確認済み
- **Trade-offs**: `contour(fill=True)` とヒートマップを重ねると、ヒートマップは常に隠れる（両方を塗りで重ねる使い方は想定しない）。region-plots の `DEFAULT_ZORDER_FILL` が -1 以下になると、塗りつぶしがヒートマップに隠れる
- **Follow-up**: 統合時に `DEFAULT_ZORDER_HEATMAP < DEFAULT_ZORDER_FILL`（region-plots）を確認する

### Decision: 既定の色の範囲は有限な値の最小・最大を自前で計算する
- **Context**: 要件 5.4、5.5
- **Selected Approach**: `z_min` / `z_max`（`_merge_alias` で `vmin` / `vmax` を統合）が `None` の側を、塗りに使う値の有限な値の最小・最大で埋めて `vmin` / `vmax` として渡す。利用者が `norm` を渡し、`z_min` / `z_max` をどちらも指定していないときは何も渡さない
- **Rationale**: matplotlib 任せでは flat の範囲が三角形ごとの平均値になり、同じ `z` を `scatter` で重ねたときに色がずれる
- **Trade-offs**: flat の `tripcolor` では、カラーバーの端の色に届く三角形がないことがある（頂点の値の平均で塗るため）。docstring に書く

### Decision: 重複した組成は 1 点を使って描画し、`UserWarning` で知らせる
- **Context**: 要件 1.8。matplotlib は重複点の値を黙って捨てる
- **Alternatives Considered**: `ValueError` で止める、値を平均する、黙って従う（matplotlib のまま）
- **Selected Approach**: 描画は続け、使われなかった点の数と集約の必要を `UserWarning` で知らせる。発生位置は `_deprecation.warn_external(message, category=UserWarning)` で利用者のコードにする。roadmap の横断の取り決めで `warn_external` はパッケージ全体で利用者向けの警告を出す入口（種類は `category` で選び、既定は FutureWarning）と定められたので、FutureWarning 以外のこの警告に使うのは取り決めどおりである
- **Rationale**: 例外は手早く図を見たい場面を止める。平均は「補間せずに見せる」という目的に反する隠れた加工になる。黙って捨てると繰り返し測定の値が失われたことに気づけない
- **Trade-offs**: 意図して重複を残す利用者には警告が出続ける。事前に集約すれば消える

### Decision: 新しいメソッドのオプションはキーワード専用、`flag_cbar` は受け付けない
- **Context**: plot-side-effects の規約（新しいメソッドは `flag_cbar` を導入しない）と、将来の引数追加
- **Selected Approach**: データの引数（`vector`・`z`・`func`）だけを位置引数にし、`scale`・`z_min`・`z_max`・`shading`・`colorbar` はキーワード専用にする。kwargs に `flag_cbar` があれば `colorbar` を案内する `TypeError` を出す
- **Rationale**: 位置引数の並びに縛られずに後から引数を足せる。matplotlib の `tripcolor` もオプションはキーワード専用。`flag_cbar` を黙って matplotlib に渡すと `AttributeError` になり原因が分かりにくい

### Decision: cross-spec review の取り決めに合わせる（2026-10-22）
- **Context**: roadmap の「Implementation Order」と「横断の取り決め」、tech.md の「Docstring Examples」が確定したので、承認済みの本 spec を対象を絞って直す
- **Selected Approach**
  - docstring の例: `tripcolor` / `heatmapf` は doctest 形式で `fig, ax = plt.subplots(layout="constrained")` と `TernaryDiagram(..., ax=ax)` から始め、`get_triangular_lattice` は純粋関数なので図を作らない。`savefig` は書かず、FutureWarning を出さない（既定の `colorbar` での色付きの描画は 1 つの例で 1 回だけ）。実行は `plot-side-effects` の共通ランナー `tests/test_doctests.py` に任せ、本 spec の `DocTestFinder` による doctest の実行はやめる。要件 9.5 を追加した
  - `colorbar` の検証: `scatter` / `contour` と同じく公開メソッドの層で `utils.check_optional_bool` により Plotter を作る前に行う。単なる真偽値の公開引数はないので `utils.check_bool` は使わない（足す場合は使う）
  - CHANGELOG: `plot-side-effects` がそろえる Unreleased の見出しの組（Breaking changes / New features / Deprecations / Bug fixes / Other changes）の New features に追記する
  - 重複した組成の警告: `warn_external(..., category=UserWarning)` は取り決めで明示的に認められた使い方
  - 重複カラーバーの警告文: 上流が一般化するので Open Question を外し、Revalidation Trigger だけ残す。テストは文面の断片だけで照合する
  - 実装順: `plot-side-effects` と `diagram-customization`（と `annotate-plain-text`）のマージ後に実装する。`region-plots` とは 1 つずつ、どちらが先でもよい。`region-plots` は `DEFAULT_ZORDER_FILL = 0.5` に決めたので `DEFAULT_ZORDER_HEATMAP = -1` との上下関係は満たされ、後からマージする側が統合時に再確認する
  - `_mesh.py` は新規モジュールとして `from __future__ import annotations` と組み込みジェネリクス・`X | None` を使う。実行時に評価される型別名だけは 3.9 で動く `typing` の形にする
- **Trade-offs**: 共通ランナーの対象の集め方や実行条件が変わると本 spec の例に影響するので、Revalidation Triggers に加えた

### Synthesis
- **Generalization**: `tripcolor` と `heatmapf` は「三角形分割 + 点または三角形の値 + 値を決められない三角形のマスク + 色の範囲 + 描画後処理」という同じ手順の 2 つの入力の作り方にすぎない。この手順を `_MeshPlotter._draw_mesh` 1 つにまとめ、値の位置（点 / 三角形）を引数で切り替える。将来の六角形ヒートマップなどは範囲外なので、手順の一般化はこの 2 つに必要な分にとどめる
- **Build vs. Adopt**: 三角形分割は matplotlib の `Triangulation`（qhull）を使う。描画は `Axes.tripcolor` をそのまま使う。正則な三角格子は numpy で自作する（matplotlib と numpy に該当する関数がなく、scipy は依存に加えない）
- **Simplification**: 格子の重心計算や評価点の選択は 1 行で済むので、専用の関数を作らず Plotter に置く。細長い三角形の自動マスク（matplotlib の `TriAnalyzer`）や重複の自動集約は入れず、利用者の `mask` 指定と事前集約に任せる

## Risks & Mitigations
- `_api.py`・`utils.py`・`tests/test_utils.py`・`CHANGELOG.md` を region-plots / diagram-customization / plot-side-effects と同時に編集する — 追記だけにし、既存の行や他 spec の追加箇所を並べ替えない。`_api.py` の差分は Plotter 2 つ・基底 1 つ・メソッド 2 つ・定数 1 つに限り、計算は `_mesh.py` に置く。roadmap の Implementation Order により、`plot-side-effects` → `diagram-customization` → `annotate-plain-text` のマージ後に、`region-plots` と 1 つずつ（どちらが先でもよい）マージする
- plot-side-effects の重複カラーバー警告の文面 — cross-spec review で上流が `z` に触れない一般的な文面にすることになったので、Open Questions から外した。文面は上流の所有物なので、本 spec のテストは全文に依存せず `"colorbar"` やメソッド名などの変わりにくい断片だけで照合する。文面の変更は Revalidation Triggers で扱う
- 古い matplotlib で `set_array` が NaN をマスクしない — 値を自前で `np.ma.masked_invalid` してから渡し、三角形もマスクする
- `ax.tripcolor` が `ax.grid(False)` を呼ぶ — ternary-diagram の土台は Axes のグリッドを使わないので影響しない。利用者が自分で有効にした Axes のグリッドは matplotlib の仕様どおり消える
- 速度の要件をテストで測ると CI で不安定になりうる — 計測値（0.05 秒）に対して 1 秒の閾値で十分な余裕がある。図の保存は計測に含めない

## References
- [matplotlib.axes.Axes.tripcolor](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.tripcolor.html) — 呼び出し形、`shading`、`facecolors`、戻り値の型
- [matplotlib.tri.Triangulation](https://matplotlib.org/stable/api/tri_api.html#matplotlib.tri.Triangulation) — `triangles`、`mask`、qhull による自動分割
- [python-ternary の heatmapf](https://github.com/marcharper/python-ternary) — `heatmapf(func, scale, ...)` の API（移行する利用者が期待する名前）
- `.kiro/specs/plot-side-effects/design.md` — `_post_draw`、`colorbar` 引数、`check_optional_bool`、`warn_external` の規約
- `.kiro/specs/diagram-customization/design.md` — `utils.py` に追加される関数名と、土台の zorder
