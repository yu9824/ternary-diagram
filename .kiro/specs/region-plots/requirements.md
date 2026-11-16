# Requirements Document

## Project Description (Input)
材料・化学系の研究者は三元系の相図を描く。単相域・二相域・三相域を多角形で塗り分け、領域の中に相の名前を置くのが典型だが、ternary-diagram では `utils.three2two` で自分で座標変換してから `ax.fill` や `ax.text` を呼ぶしかなく、「組成をそのまま渡せる」というこのライブラリの価値が相図では成り立たない。

- **誰が困っているか**: ternary-diagram で三元系の相図（相領域の塗り分けと相の名前）を描きたい材料・化学系の研究者
- **今の状況**: 組成で指定できる描画は `scatter`・`contour`・`plot`（タイライン）・`annotate` だけ。`annotate` は注釈用で、既定で点から右上に 0.02 ずらした位置に小さめの文字（`fontsize=8`）を置くため、領域の中心にラベルを置く用途に合わない。多角形を塗る手段はない
- **何を変えるか**: `td.fill(vector, **kwargs)` で組成で指定した頂点（shape `(n, 3)`、合計は 1 でなくてよい）を結ぶ多角形を塗れるようにし、`label` で凡例に出せるようにする。`td.text(text, vector, **kwargs)` で組成点のちょうどその位置に文字を置けるようにし、化学式の自動整形の有無を選べるようにする。どちらも既存の描画と同じく `**kwargs` を matplotlib に渡し、描いた座標を `x_` / `y_` に記録し、matplotlib のネイティブオブジェクトを返す。既定の重なり順で、塗りつぶしがグリッドや散布図を隠さないようにする。描画後の処理は `plot-side-effects` の共通の仕組みを使い、化学式とみなす判定は `annotate-plain-text` が定める規則をそのまま使う

詳細は同じディレクトリの `brief.md` を参照。

## Introduction

三元系の相図では、相領域を多角形で塗り分け、領域の中に相の名前を置く。ternary-diagram はこの 2 つを組成で指定する手段を持たず、利用者は座標変換を自分で行ってから matplotlib を直接呼んでいる。

本機能では、組成で指定した頂点を結ぶ多角形を塗る `fill` と、組成点のちょうどその位置に文字を置く `text` を `TernaryDiagram` の描画メソッドとして追加する。どちらも既存の描画メソッドと同じく、比率をそのまま受け付け、追加の指定を matplotlib に渡し、matplotlib のオブジェクトを返し、描いた座標を記録する。既定の重なり順は、塗りつぶしがグリッドや散布図を隠さず、相の名前が塗りつぶしや点に隠れないように定める。

## Boundary Context

- **In scope**:
  - 組成で指定した 1 つの多角形の塗りつぶし（`fill`）と、組成で指定した 1 点への文字の配置（`text`）
  - それぞれの既定値（重なり順、文字の配置、化学式の整形の有無）と、その上書き
  - `text` の化学式の整形の有無について、三角図単位の設定（`TernaryDiagram` 作成時の `auto_latex_notation`）の引き継ぎと、呼び出しごとの指定による上書き
  - 入力の検証、描いた座標の記録、テスト、docstring とその使用例、CHANGELOG
- **Out of scope**:
  - 相境界の自動計算、凸包の計算、頂点の並べ替え（頂点は渡された順に結ぶ）
  - 領域ラベルの自動配置（領域の重心などへの自動の位置決め）
  - 1 回の呼び出しで複数の多角形、または複数の文字列を描く API（多角形ごと・文字列ごとに呼び出す）
  - ハッチングなどの見た目のプリセット（matplotlib のプロパティを追加の指定で渡せば足りる）
  - 化学式とみなす判定の規則そのものの定義・変更
  - `TernaryDiagram` 作成時の `auto_latex_notation` の意味・受け付ける値・検証の変更（引き継いで使うだけ）
  - 成分の値そのものの妥当性（負の成分や合計 0 の行）の追加の検査。既存の描画メソッドと同じ扱いとする
  - 描画後のレイアウト調整とカラーバーの方針、三角図の土台（外枠・グリッド・目盛り・ラベル）の描き方、使い方ページ
  - 共通の doctest ランナー（`tests/test_doctests.py`）と、CHANGELOG の Unreleased の見出しの組（どちらも `plot-side-effects` が用意する）
- **Adjacent expectations**:
  - roadmap の実装順により、`plot-side-effects`・`diagram-customization`・`annotate-plain-text` の順にマージされた後で本機能をマージする。`heatmaps` は本機能の前でも後でもよいが、同時には入れず 1 つずつマージする
  - `plot-side-effects` が定める描画後の処理（三角図単位のレイアウト自動調整の設定、カラーバーの自動追加の規則、既定値変更の警告の出し方）に、`fill` と `text` も既存の描画メソッドと同じく従う。真偽値の検証関数、共通の doctest ランナー、CHANGELOG の見出しの組も `plot-side-effects` が用意したものを使う
  - `annotate-plain-text`（直接実装する候補）が、化学式とみなす判定の規則を定める。`text` はその規則を `annotate` と同じ形で使い、規則を自分では定めない。`annotate-plain-text` は本機能より先に入る
  - `diagram-customization` が持つ三角図の土台の見た目と重なり順は変えない。土台を描き直しても、本機能の重なり順は保たれる
  - `heatmaps` は自分の描画の重なり順を自分で定める。本機能は既存の描画と本機能の描画の間の重なり順を定める。両方が入った時点で、ヒートマップが `fill` より奥（最も奥のデータ層）にあることを、後からマージする側が確かめる
  - `user-guide-docs` は、本機能の docstring をもとに相図の描き方のページを書く

## Requirements

### Requirement 1: 組成で指定した多角形の塗りつぶし
**Objective:** As a 三元系の相図を描く研究者, I want 相領域の頂点を組成のまま渡して多角形を塗りたい, so that 座標変換を自分で書かずに相領域を塗り分けられる

#### Acceptance Criteria
1. When 利用者が 3 個以上の頂点を組成（各行が 3 成分の比率）の並びとして `fill` に渡した, the TernaryDiagram shall 各頂点を三角図上の対応する位置に置き、渡された順に結んで閉じた 1 つの多角形を塗る
2. The TernaryDiagram shall `fill` の頂点の各行を合計 1 に正規化してから位置を決め、合計が 1 でない比率をそのまま受け付ける
3. When `fill` の描画が完了した, the TernaryDiagram shall 描いた多角形を表す matplotlib のネイティブオブジェクトを返す
4. When 利用者が `fill` にラベルを指定して凡例を作成した, the TernaryDiagram shall そのラベルを多角形の凡例の項目として表示する
5. While 色が指定されていない, the TernaryDiagram shall matplotlib の既定の色の割り当てに従って多角形を塗り、続けて呼んだ `fill` には matplotlib の既定の順番で次の色を割り当てる

### Requirement 2: 組成点への文字の配置
**Objective:** As a 相領域に相の名前を置く研究者, I want 組成で指定した点のちょうどその位置に文字を置きたい, so that 領域の中心に相の名前を配置できる

#### Acceptance Criteria
1. When 利用者が文字列と 3 成分の組成 1 つを `text` に渡した, the TernaryDiagram shall その組成に対応する三角図上の位置に文字列を 1 つ配置する
2. The TernaryDiagram shall `text` の組成を合計 1 に正規化してから位置を決め、合計が 1 でない比率をそのまま受け付ける
3. While 文字の水平方向・垂直方向の配置が指定されていない, the TernaryDiagram shall 文字列の中心を組成点に重ねて配置し、組成点から位置をずらさない
4. When `text` の描画が完了した, the TernaryDiagram shall 配置した文字列を表す matplotlib のネイティブオブジェクトを返す

### Requirement 3: 文字の化学式の整形
**Objective:** As a 相の名前に化学式を使う研究者, I want 化学式の自動整形を使うかどうかを三角図全体の設定で決め、必要な呼び出しだけ切り替えたい, so that `Li2TiO3` のような化学式は下付き文字で、普通の名前はそのまま表示できる

#### Acceptance Criteria
1. The TernaryDiagram shall `text` で化学式の自動整形を行うかどうかを呼び出しごとに指定する手段を提供し、指定された場合はその指定を三角図単位の設定（`TernaryDiagram` 作成時の `auto_latex_notation`）より優先して、その呼び出しの文字列にだけ適用する（三角図単位の設定と他の呼び出しは変えない）
2. Where 化学式の自動整形を行う設定である, the TernaryDiagram shall 化学式とみなす判定と整形を `annotate` と同じ共通の規則（`annotate-plain-text` が定める）で行い、化学式の整形を行う設定の `annotate` が同じ文字列に対して表示するのと同じ文字列を表示する
3. Where 化学式の自動整形を行わない設定である, the TernaryDiagram shall 渡された文字列を変更せずに表示する
4. When `text` に文字列以外の値が渡された, the TernaryDiagram shall 化学式の整形を行わずに、その値を matplotlib と同じ方法で文字列に変換して表示する
5. If 化学式の自動整形の呼び出しごとの指定に、指定なしを表す `None` と真偽値のどれでもない値が渡された, the TernaryDiagram shall 受け付けられる値（`None`・`True`・`False`）を示すメッセージ付きの `TypeError` を送出する
6. While 化学式の自動整形の呼び出しごとの指定がない（`None`）, the TernaryDiagram shall 三角図単位の設定を引き継いで整形の有無を決め、三角図単位の設定が既定のまま（整形する）なら整形を行う

### Requirement 4: 既定の重なり順
**Objective:** As a 相図に組成点やタイラインを重ねる研究者, I want 塗りつぶしがグリッドや点を隠さず、相の名前が塗りつぶしや点に隠れないこと, so that 呼び出しの順番を気にせずに読みやすい相図が得られる

#### Acceptance Criteria
1. While `fill` と比較対象の描画のどちらにも重なり順が指定されていない, the TernaryDiagram shall `fill` の多角形を、三角図のグリッドと外枠、タイライン（`plot`）、散布図（`scatter`）、注釈（`annotate`）、`text` の文字列より奥に描く
2. While `fill` と等高線図のどちらにも重なり順が指定されていない, the TernaryDiagram shall `fill` の多角形を等高線図（`contour`）より手前に描く
3. While `text` と比較対象の描画のどちらにも重なり順が指定されていない, the TernaryDiagram shall `text` の文字列を、`fill` の多角形、三角図のグリッドと外枠、タイライン、散布図より手前に描く
4. The TernaryDiagram shall 1 から 3 の重なり順を、描画メソッドを呼んだ順序や三角図の土台の描き直しに関係なく保つ
5. When 利用者が `fill` または `text` に重なり順を指定した, the TernaryDiagram shall ライブラリの既定値より利用者の指定を優先する
6. The TernaryDiagram shall 既存の描画（等高線図、三角図のグリッドと外枠、タイライン、散布図）の既定の重なり順を変えない

### Requirement 5: matplotlib との統合と座標の記録
**Objective:** As a matplotlib に慣れた研究者, I want `fill` と `text` を既存の描画メソッドと同じ感覚で使いたい, so that matplotlib の知識で見た目を調整し、描いた位置を後から参照できる

#### Acceptance Criteria
1. The TernaryDiagram shall `fill` と `text` に渡された追加のキーワード引数を matplotlib にそのまま渡し、ライブラリの既定値より利用者の指定を優先する
2. When 利用者がプロパティを matplotlib の別名（`ha` などの略称）で指定した, the TernaryDiagram shall 正式名で指定した場合と同じく、ライブラリの既定値より利用者の指定を優先する
3. When `fill` または `text` の描画が完了した, the TernaryDiagram shall 描いた点の 2 次元座標を、既存の描画メソッドと同じく、メソッド名（`fill` / `text`）ごとに TernaryDiagram の `x_` / `y_` に記録する
4. The TernaryDiagram shall 既存の描画メソッドの引数、既定値、戻り値を変えない

### Requirement 6: 入力の検証
**Objective:** As a 相図を描く研究者, I want 誤った入力を描く前に分かりやすいエラーで知りたい, so that 原因をすぐに直せ、図に中途半端な描画が残らない

#### Acceptance Criteria
1. If `fill` の頂点の並びが「行ごとに 3 成分」の 2 次元の形でない, the TernaryDiagram shall 期待する形と実際の形を示すメッセージ付きの `ValueError` を送出する
2. If `fill` の頂点が 3 個未満である, the TernaryDiagram shall 多角形には 3 個以上の頂点が必要であることと実際の個数を示すメッセージ付きの `ValueError` を送出する
3. If `text` の組成が 3 成分でない, the TernaryDiagram shall 成分の数が 3 でなければならない旨のメッセージ付きの `ValueError` を送出する
4. If `fill` または `text` の入力の検証に失敗した, the TernaryDiagram shall 三角図に何も描き加えず、座標の記録も変えない

### Requirement 7: 描画後の処理との整合
**Objective:** As a 三角図を自分の matplotlib の図に組み込む利用者, I want `fill` と `text` も既存の描画メソッドと同じ描画後の規則に従うこと, so that レイアウトやカラーバーの設定を描画メソッドごとに覚え直さなくて済む

#### Acceptance Criteria
1. The TernaryDiagram shall `fill` と `text` の描画後のレイアウト自動調整を、既存の描画メソッドと同じ三角図単位の設定と規則に従って行う
2. The TernaryDiagram shall `fill` と `text` の描画でカラーバーを追加しない
3. The TernaryDiagram shall レイアウト自動調整の既定値の変更に関する警告を、既存の描画メソッドと同じ条件と頻度（同じ三角図・同じ理由で 1 回）で、`fill` と `text` の描画にも適用する

### Requirement 8: ドキュメントと変更履歴
**Objective:** As a 相図を描こうとする利用者, I want `fill` と `text` の使い方と既定値を docstring と CHANGELOG で確認したい, so that 試行錯誤せずに相図を描ける

#### Acceptance Criteria
1. The ternary-diagram shall `fill` と `text` の docstring（英語・NumPy スタイル）に、各引数の意味、既定値（重なり順、文字の配置、化学式の整形とその三角図単位の設定からの引き継ぎ）とその変え方、呼び出しごとの整形の指定が及ぶ範囲、戻り値、使用例、ラップしている matplotlib の関数の説明への URL を記載する
2. The ternary-diagram shall CHANGELOG の Unreleased の「New features」に、`fill` と `text` の追加を記載する
3. When 共通の doctest ランナー（`plot-side-effects` が用意する `tests/test_doctests.py`）が `fill` と `text` の docstring の使用例を実行した, the ternary-diagram shall エラーも FutureWarning も出さず、ファイルを書き出さずに、記載どおりの結果で完了する
