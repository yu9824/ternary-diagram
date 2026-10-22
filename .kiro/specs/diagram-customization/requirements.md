# Requirements Document

## Project Description (Input)
三角図の見た目がほとんど固定されている。`TernaryDiagram.__init__` が外枠・グリッド（3 方向 × 9 本、10% 刻み）・目盛りラベル（`"%d0"` 形式で 10〜90）・頂点ラベルをハードコードされた定数で一度に描き、描いた artist への参照を持たないため、後から変更・削除する手段がない。変えられるのは `auto_latex_notation` だけで、軸タイトル（例: 「Li2O / mol%」）も 0 と 100 の目盛りも出せない。論文用に「5% 刻みにしたい」「軸タイトルを付けたい」「フォントを雑誌の規定に合わせたい」となった時点で、材料・化学の研究者である利用者は mpltern や python-ternary に乗り換えてしまう。

そこで、`__init__` の描画を部品（外枠・グリッド・目盛り・軸タイトル・頂点ラベル）ごとに分け、それぞれが自分の artist を保持して描き直せるようにする。作成時には matplotlib の `subplot_kw` に倣った `*_kw` 引数（例: `grid_kw`、`tick_kw`）で、作成後には `set_*` メソッド（例: `set_grid`、`set_ticks`、`set_axis_labels`、`set_vertex_labels`）で見た目を変えられ、変更前の artist は残らない。少なくともグリッドの間隔・線種・色・表示有無、目盛りの間隔・書式（パーセント / 割合）・0 と 100 の表示・フォントサイズ、各辺の軸タイトル（新規）、頂点ラベルのフォントサイズと位置、外枠の線種を変えられるようにする。辺上の位置や目盛り位置の計算は `utils` の純粋関数にする。何も指定しなければ今とまったく同じ見た目になり（既存テストの構造的な assert がそのまま通る）、部品の zorder は `DEFAULT_ZORDER_GRIDS` を保ち、`auto_latex_notation` は今の意味のまま残す。描画メソッドとその後処理、レイアウトの自動調整、カラーバーの見た目、拡大表示・回転・projection 化、rcParams やスタイルオブジェクトによるグローバル既定値は対象外。

## Introduction
ternary-diagram の三角図の土台（外枠・グリッド・目盛りラベル・軸タイトル・頂点ラベル）を、作成時にも作成後にも部品ごとに指定・変更できるようにする。論文用の図を作る材料・化学の研究者が、図を作り直したり他のライブラリへ乗り換えたりせずに、目盛りの細かさ、書式、文字の大きさ、軸タイトルを雑誌の規定に合わせられることが目的である。何も指定しない場合の見た目は現行版と同一に保つ。

本書での用語:
- **部品**: 外枠、グリッド、目盛りラベル、軸タイトル、頂点ラベルの 5 つ。三角図の作成時に描かれる土台を構成する
- **1 番目 / 2 番目 / 3 番目の成分**: `materials` と組成ベクトルの列の並び順。それぞれ上・左下・右下の頂点に対応する
- **値**: 各成分の組成比を 0〜1 の割合で表したもの。1 が 100% に当たる
- **長さの単位**: 三角形の辺の長さを 1 とする

## Boundary Context
- **In scope**:
  - 5 つの部品の見た目を、作成時に指定し、作成後に変更すること（表示・非表示を含む）
  - 各部品が描いた図形オブジェクトの取り出し
  - 部品の配置に使う幾何計算と目盛りの書式適用を、図なしで単独に使えること
  - 新しい引数・変更操作の docstring と CHANGELOG（`TernaryDiagram.__init__` の docstring については、新しい引数の Parameters の項目だけ）
- **Out of scope**:
  - 描画メソッド（`scatter` / `contour` / `plot` / `annotate` など）の見た目と、描画後の処理（レイアウトの自動調整、カラーバーの自動追加）
  - カラーバーの見た目
  - 目盛り線（辺に付く短い刻み線）の描画。現行版も描いていない
  - 目盛りを付ける辺と成分の対応を変えること（現行の配置に固定し、文書化する）
  - 三角形の一部の拡大表示、三角形全体の回転、matplotlib の projection 化
  - rcParams やスタイルオブジェクトによる、ライブラリ全体の既定値の変更
  - 目的別の使い方ページ
  - `TernaryDiagram.__init__` の docstring の使用例（Examples 節）。`user-guide-docs` だけが持つ
  - 描画後のレイアウトの指定（`tight_layout`）の引数とその検証。`plot-side-effects` が持つ
- **Adjacent expectations**:
  - 描画後のレイアウト調整・カラーバーの方針・非推奨警告の仕組みは `plot-side-effects` が持つ。本機能の部品の描画・描き直しは、図全体のレイアウトを変えない
  - 新しい描画（`region-plots`、`heatmaps`）との前後関係は、各描画の重なり順の値で決まる。本機能は土台の重なり順の値を変えない
  - 見た目の変え方の使い方ページは `user-guide-docs` が、本機能の docstring をもとに書く
  - 実装は `plot-side-effects` のマージ後に行う（roadmap の Implementation Order）。作成時の引数は roadmap の「横断の取り決め」で確定した最終形に合わせ、`plot-side-effects` が足したレイアウトの指定の後ろに、本機能の部品ごとの指定を足す
  - 真偽値の検証、テスト用の三角図の作り方、docstring の使用例を実行する共通の仕組み、CHANGELOG の見出しの組は `plot-side-effects` が用意したものを使う

## Requirements

### Requirement 1: 既定の見た目と既存コードの互換性
**Objective:** As a 既存の利用者, I want 何も指定しなければ今と同じ三角図が描かれること, so that 既存のコードと図を書き換えずに新しい版へ更新できる

#### Acceptance Criteria
1. When 利用者が見た目の指定を何も与えずに三角図を作成した, the TernaryDiagram shall 現行版と同じ外枠（黒・線幅 2 の実線 3 本）、グリッド（灰色・線幅 0.5 の線を 3 方向に 9 本ずつ、10% 刻み）、目盛りラベル（各辺に 10〜90 の 9 個）、頂点ラベル（フォントサイズ 16）を、現行版と同じ位置・向き・文字揃え・色・大きさ・重なり順の値で描く
2. When 利用者が見た目の指定を何も与えずに三角図を作成した, the TernaryDiagram shall 軸タイトルを描かない
3. The TernaryDiagram shall 現行版の作成時の引数（`materials`、`ax`、`auto_latex_notation`）を、同じ並び順・同じ意味で受け付ける
4. While 化学式の自動整形（`auto_latex_notation`）が有効, the TernaryDiagram shall 頂点ラベルの文字列を現行版と同じ規則で化学式表記に整形し、無効のときは与えられた文字列をそのまま表示する

### Requirement 2: 作成時の指定と作成後の変更
**Objective:** As a 論文用の図を作る研究者, I want 部品ごとの見た目を作成時にも作成後にも指定できること, so that 図を作り直さずに雑誌の規定に合わせて仕上げられる

#### Acceptance Criteria
1. The TernaryDiagram shall 5 つの部品のそれぞれについて、作成時に見た目を指定する手段と、作成後に見た目を変更する手段を提供する
2. The TernaryDiagram shall 作成時の指定と作成後の変更で同じ項目を同じ名前・同じ意味で受け付け、同じ指定からは同じ見た目を描く
3. When 利用者が作成後に部品の見た目を変更した, the TernaryDiagram shall その部品が変更前に描いた図形をすべて取り除き、新しい設定で描き直す
4. When 利用者が作成後に部品の一部の項目だけを指定して変更した, the TernaryDiagram shall 指定されなかった項目について直前の設定を引き継ぐ
5. When 利用者が部品の見た目を変更した, the TernaryDiagram shall 他の部品と、利用者が描いた図形（散布図・等高線・線・注釈など）を取り除かず、変更もしない
6. When 利用者が非表示にした部品を再び表示にした, the TernaryDiagram shall 非表示にする直前の設定でその部品を描き直す
7. Where 部品の見た目の指定に matplotlib の線や文字のプロパティ（色・線幅・線種・フォントサイズなど）が含まれる, the TernaryDiagram shall そのプロパティをその部品のすべての図形に適用し、ライブラリ側の既定値より優先する
8. The TernaryDiagram shall 部品を描く・描き直す際に、図全体のレイアウト（Axes の位置や大きさ）を変更しない

### Requirement 3: 描いた図形の取り出し
**Objective:** As a 細部を調整したい利用者, I want 各部品が描いた図形オブジェクトを取り出せること, so that 1 つのラベルだけ色を変えるといった個別の調整を、図全体の図形の一覧を探さずに行える

#### Acceptance Criteria
1. The TernaryDiagram shall 各部品が現在描いている図形オブジェクトを、部品ごとに取り出せるようにする
2. When 利用者が作成後に部品の見た目を変更した, the TernaryDiagram shall 新しく描いた図形オブジェクトを返す
3. While 部品が非表示, the TernaryDiagram shall その部品から取り出せる図形を空にする
4. When 部品が描き直された, the TernaryDiagram shall 取り出せる図形を描き直した後のものに置き換える
5. If 利用者が図形の取り出し口へ値を代入しようとした, the TernaryDiagram shall 読み取り専用であることを示すエラーを送出する

### Requirement 4: 外枠
**Objective:** As a 研究者, I want 三角形の外枠の線の見た目を変えられること, so that 図全体の線の太さや色を雑誌の規定にそろえられる

#### Acceptance Criteria
1. When 利用者が外枠の線種・色・線幅を指定した, the TernaryDiagram shall 3 辺すべての外枠をその見た目で描く
2. When 利用者が外枠を非表示にした, the TernaryDiagram shall 外枠を描かない

### Requirement 5: グリッド
**Objective:** As a 研究者, I want グリッドの間隔と見た目を変えられること, so that 「5% 刻み」などデータに合った細かさの図を描ける

#### Acceptance Criteria
1. When 利用者がグリッドの間隔を指定した, the TernaryDiagram shall 0 と 1 を除くその間隔の倍数の値に、3 つの成分それぞれの等組成線を描く（例: 0.05 なら 3 方向に 19 本ずつ）
2. When 利用者がグリッドの線種・色・線幅を指定した, the TernaryDiagram shall すべてのグリッド線をその見た目で描く
3. When 利用者がグリッドを非表示にした, the TernaryDiagram shall グリッド線を描かない
4. The TernaryDiagram shall グリッドの間隔を目盛りラベルの間隔と独立に扱う

### Requirement 6: 目盛りラベル
**Objective:** As a 研究者, I want 目盛りの間隔・書式・両端の値・文字の大きさを変えられること, so that 組成を読み取りやすくし、雑誌の書式要件を満たせる

#### Acceptance Criteria
1. The TernaryDiagram shall 1 番目の成分の目盛りラベルを右辺に、2 番目の成分を左辺に、3 番目の成分を底辺に置き、各辺の値が反時計回りに 0 から 1 へ増える現行の配置を保つ
2. When 利用者が目盛りの間隔を指定した, the TernaryDiagram shall 0 と 1 を除くその間隔の倍数の値に、各辺の目盛りラベルを描く
3. While 目盛りの書式が既定（パーセント）, the TernaryDiagram shall 値を百分率の数値（例: 10、2.5）で、不要な小数点以下の桁を付けずに表示する
4. When 利用者が割合の書式を指定した, the TernaryDiagram shall 値を 0〜1 の割合（例: 0.1）で表示する
5. When 利用者が独自の書式を指定した, the TernaryDiagram shall 各目盛りの値（0〜1 の割合）にその書式を適用した文字列を表示する
6. Where 両端（0 と 100）の表示が有効, the TernaryDiagram shall 各辺の両端（値 0 と 1）にも目盛りラベルを描く
7. When 利用者が目盛りラベルのフォントサイズなどの文字の見た目を指定した, the TernaryDiagram shall すべての目盛りラベルをその見た目で描く
8. When 利用者が目盛りラベルを非表示にした, the TernaryDiagram shall 目盛りラベルを描かない

### Requirement 7: 軸タイトル
**Objective:** As a 研究者, I want 各辺に軸タイトル（例: 「Li2O / mol%」）を付けられること, so that 図だけで各軸の成分と単位が読み取れる

#### Acceptance Criteria
1. When 利用者が 3 つの成分の軸タイトルを指定した, the TernaryDiagram shall 各タイトルを、その成分の目盛りラベルが付く辺の外側中央に、辺と平行で文字が逆さにならない向きで描く
2. When 利用者が一部の成分の軸タイトルだけを指定し、残りを「なし」とした, the TernaryDiagram shall 指定された成分の軸タイトルだけを描く
3. The TernaryDiagram shall 軸タイトルの文字列を化学式に自動整形せず、与えられたとおりに表示する
4. When 利用者が軸タイトルの辺からの距離を指定した, the TernaryDiagram shall 各軸タイトルを、その距離（長さの単位）だけ辺の中点から外側へ離して描く
5. When 利用者が軸タイトルのフォントサイズなどの文字の見た目を指定した, the TernaryDiagram shall すべての軸タイトルをその見た目で描く
6. When 利用者が軸タイトルを非表示にした, the TernaryDiagram shall 軸タイトルを描かない

### Requirement 8: 頂点ラベル
**Objective:** As a 研究者, I want 頂点ラベルの文字・大きさ・位置を変えられること, so that 長い化学式や大きな文字でも外枠や目盛りラベルと重ならないように配置できる

#### Acceptance Criteria
1. When 利用者が頂点ラベルの文字列を変更した, the TernaryDiagram shall 新しい文字列を上・左下・右下の順で各頂点に描き、化学式の自動整形の設定を作成時と同じく適用する
2. When 利用者が頂点ラベルのフォントサイズなどの文字の見た目を指定した, the TernaryDiagram shall 3 つの頂点ラベルをその見た目で描く
3. When 利用者が頂点ラベルの位置を指定した, the TernaryDiagram shall 各ラベルを、対応する頂点から指定されたずらし量（長さの単位の横・縦の組）だけ離して置く
4. When 利用者が頂点ラベルを非表示にした, the TernaryDiagram shall 頂点ラベルを描かない

### Requirement 9: 重なり順と表示範囲
**Objective:** As a 利用者, I want 部品を描き直しても重なり方と表示範囲が変わらないこと, so that 描画の後に見た目を調整してもデータの見え方が崩れない

#### Acceptance Criteria
1. The TernaryDiagram shall 描き直した部品に作成時と同じ重なり順の値を使う（外枠とグリッドは等高線より手前で、線や散布図より奥。文字の部品は現行版の文字と同じ値）
2. The TernaryDiagram shall 部品をどの順で描き直しても、外枠をグリッドより手前に描く
3. Where 利用者が部品の重なり順の値を明示した, the TernaryDiagram shall 利用者の指定を優先する
4. While 外枠やグリッドが非表示, the TernaryDiagram shall 三角形全体が収まる表示範囲を、それらを表示しているときと同じに保つ

### Requirement 10: 入力の検証
**Objective:** As a 利用者, I want 不正な指定がすぐに分かるエラーになること, so that 誤った図に気づかないまま保存してしまうことを防げる

#### Acceptance Criteria
1. If 間隔に 0 以下の値、1 より大きい値、または有限でない値が与えられた, the TernaryDiagram shall 許される範囲を示すメッセージ付きのエラーを送出する
2. If 頂点ラベル、軸タイトル、または頂点ラベルの位置に 3 つ以外の個数が与えられた, the TernaryDiagram shall 3 つ必要であることを示すエラーを送出する
3. If 受け付けない種類の値（数値でない間隔、真偽値でない表示の有無、文字列でないラベル、項目名と値の対応になっていない作成時の指定など）が与えられた, the TernaryDiagram shall 受け付ける種類を示すエラーを送出する
4. If 目盛りの書式として解釈できない指定が与えられた, the TernaryDiagram shall 受け付ける書式の種類を示すエラーを送出する
5. If 作成時に頂点ラベルの文字列が `materials` と頂点ラベルの指定の両方で与えられた, the TernaryDiagram shall どちらを使うか決められないことを示すエラーを送出する
6. If `materials` の要素が 3 つ未満である, the TernaryDiagram shall 3 つ必要であることを示すエラーを送出する
7. If matplotlib が受け付けない見た目の指定が与えられた, the TernaryDiagram shall matplotlib のエラーを利用者に送出する
8. If 部品の変更中にエラーが発生した, the TernaryDiagram shall その部品の図形と設定を変更前の状態のまま保つ

### Requirement 11: 幾何計算の単独利用
**Objective:** As a メンテナ（および独自の注記を同じ配置規則で置きたい利用者）, I want 部品の配置に使う計算を図なしで使えること, so that 配置の正しさを描画と切り離して検証できる

#### Acceptance Criteria
1. The ternary-diagram library shall 部品の配置に使う計算（目盛り・グリッドの値の列、辺上の点、グリッド線の両端、軸タイトルの位置と向き）と目盛りの書式適用を、図や Axes を必要とせず、同じ入力に同じ結果を返す関数として提供する
2. The ternary-diagram library shall 部品の配置をこれらの関数の結果から決め、関数と描画結果の位置を食い違わせない
3. The ternary-diagram library shall これらの関数の docstring に、実行して確かめられる使用例（doctest）を持たせる

### Requirement 12: ドキュメントと変更履歴
**Objective:** As a 利用者, I want 新しい指定方法と目盛りの配置規約が文書化されていること, so that ソースを読まずに見た目の変え方が分かる

#### Acceptance Criteria
1. The ternary-diagram library shall 5 つの部品ごとの作成時の指定について、意味・既定値・対応する作成後の変更操作を `TernaryDiagram.__init__` の docstring の Parameters に、作成後の変更操作のそれぞれについて意味・既定値・使用例をその変更操作の docstring に、英語の NumPy スタイルで記載する。作成時の指定の使用例は、作成時の指定がその変更操作の呼び出しと同じ意味であることとあわせて対応する変更操作の docstring に記載し、`TernaryDiagram.__init__` の docstring の使用例（Examples 節）は変更しない
2. The ternary-diagram library shall どの辺の目盛りがどの成分を表し、値がどちら向きに増えるかを docstring に明記する
3. The ternary-diagram library shall CHANGELOG の Unreleased の、プロジェクトで共通の見出しのうち該当するものに、追加した作成時の引数・変更操作・図形の取り出し口・配置の関数（新機能）と、`materials` の要素が足りないときのエラーの変化（不具合修正）を記載する
4. The ternary-diagram library shall 本機能で追加する docstring の使用例を、プロジェクトの使用例の規約（docstring ごとに必要な import から始めてその docstring だけで実行できるようにする、図を描く例はレイアウトエンジン付きの図と Axes を作って描画先として渡す、ファイルを書き出さない、将来の既定値変更の警告を出さない）に従う doctest として書き、プロジェクト共通の doctest の実行で通るようにする
