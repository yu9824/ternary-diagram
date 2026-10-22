# Requirements Document

## Project Description (Input)
三成分の組成と物性値の分布を三角図で見せたい材料・化学系の研究者は、今は補間した等高線（`contour`）か点の色分け（`scatter`）しか選べない。

- **誰が困っているか**: 実験点がまばらなデータを、補間で作った値を混ぜずに見せたい利用者と、理論式や機械学習モデルの予測 f(a, b, c) を三角形全体に描きたい利用者
- **今の状況**: `contour` は `tricontourf` / `tricontour` に 101 段階の levels を与えて補間するので、データがない場所まで値があるように見える。関数を三角形全体に描くには、利用者が自分で格子を作って評価し、座標変換してから matplotlib を呼ぶ必要がある（python-ternary の `heatmapf` に当たる機能がない）。三角形の格子を作る機能もない
- **何を変えるか**: 測定点を三角形分割して補間せずに塗る `tripcolor` と、三角形内の正則な格子で関数を評価して塗るヒートマップを `TernaryDiagram` のメソッドとして追加する。正則な三角格子は `utils` の純粋関数で作る。値の範囲（`z_min` / `z_max`、別名 `vmin` / `vmax`）とカラーバーの扱いは既存の `scatter` / `contour` とそろえ、描画後処理とカラーバーは `plot-side-effects` の方針に従う。戻り値は matplotlib のネイティブオブジェクトで、`TernaryDiagram.colorbar()` にそのまま渡せる。依存は増やさず、`scale` が 100 程度（約 1 万個の三角形）でも実用的な速さで描ける

詳細は同じディレクトリの `brief.md` を参照。

## Introduction

ternary-diagram で物性値の分布を見せる手段は、補間した等高線（`contour`）と点の色分け（`scatter`）の 2 つだけである。実験点がまばらなとき、等高線の滑らかな補間はデータのない場所にも値があるように見せてしまう。また、理論式や機械学習モデルの予測を三角形全体に描きたい利用者は、自分で格子を作り、関数を評価し、座標を変換してから matplotlib を呼ぶ必要がある。

本機能では、測定した組成点を三角形でつないで補間せずに塗る `tripcolor` と、三角形内の正則な格子で関数を評価して塗る `heatmapf` を `TernaryDiagram` に追加し、その格子を図なしで得られる生成関数を提供する。値の範囲・カラーバー・描画後のレイアウトの扱いは既存の `scatter` / `contour` と同じ規則にそろえ、戻り値はそのまま `TernaryDiagram.colorbar()` に渡せる matplotlib のオブジェクトにする。

## Boundary Context

- **In scope**:
  - 組成点と値から三角形単位で塗る描画（`tripcolor`）。塗り方は flat と gouraud の 2 通り
  - 関数 f(a, b, c) を正則な三角格子で評価して塗る描画（`heatmapf`）
  - 正則な三角格子（組成と小三角形の組）を図なしで返す生成関数
  - 値を決められない三角形（欠損値・無限大）の扱い
  - 値の範囲（`z_min` / `z_max`、別名 `vmin` / `vmax`）とカラーバー・レイアウトの扱いを既存の描画とそろえること
  - 既存の描画と重ねたときの既定の重なり順
  - テスト、追加した API の docstring、CHANGELOG
- **Out of scope**:
  - 六角形のヒートマップ（python-ternary の hexagonal スタイル）
  - 組成をキーにした辞書でデータを渡す API（python-ternary の `heatmap`）
  - matplotlib にない補間方法（自然近傍補間、クリギングなど）
  - 細長い三角形を自動で隠す処理と、重複した組成の値の自動集約（利用者がマスクや事前の集約で対応する）
  - 等高線（`contour`）の挙動の変更
  - カラーバーの自動追加・レイアウト自動調整の方針そのもの（`plot-side-effects` が定める）
  - 三角図の土台（外枠・グリッド・目盛り・ラベル）の描き方
  - ヒートマップと等高線の使い分けを説明する使い方ページ
- **Adjacent expectations**:
  - `plot-side-effects` が定めたカラーバー自動追加・レイアウト自動調整・警告の規則を、`tripcolor` / `heatmapf` もそのまま使う。本機能は独自にカラーバーを追加したりレイアウトを調整したりしない
  - `plot-side-effects` が用意する共通の doctest 実行と CHANGELOG の Unreleased の見出しの組（Breaking changes / New features / Deprecations / Bug fixes / Other changes）を使う。本機能は自分の doctest の実行を作らず、見出しも足さない
  - 実装は roadmap の実装順に従い、`plot-side-effects` と `diagram-customization` のマージ後に行う。`region-plots` とは 1 つずつマージし、どちらが先でもよい
  - `region-plots` が追加する塗りつぶし（`fill`）は独自の既定の重なり順を持つ。両方の既定の重なり順は、統合時にヒートマップが最も奥のデータ層になることを確認する
  - `diagram-customization` が土台の部品を描き直しても、ヒートマップはグリッドと外枠より奥に描かれたままである
  - `user-guide-docs` は本機能の docstring をもとに、ヒートマップと等高線の使い分けのページを書く

## Requirements

### Requirement 1: 測定点を補間せずに塗る（tripcolor）
**Objective:** As a まばらな実験データを持つ研究者, I want 測定した組成点を三角形でつないで、補間で作った値を混ぜずに塗りたい, so that データがない場所に値があるように見せずに物性値の分布を示せる

#### Acceptance Criteria
1. The TernaryDiagram shall 組成（shape `(n, 3)`、各行の合計は 1 でなくてよい）と各組成点の値 `z` を受け取り、組成点を頂点とする三角形で三角図の上を塗る描画メソッド `tripcolor` を提供する
2. When 塗り方を指定せずに（既定の flat で）`tripcolor` を呼んだ, the TernaryDiagram shall 各三角形を、その 3 頂点の `z` の平均値に対応する 1 色で塗る
3. When 塗り方に gouraud を指定して `tripcolor` を呼んだ, the TernaryDiagram shall 各三角形の内部を、3 頂点の `z` の間で線形に変化する色で塗る
4. While 三角形の組み合わせを指定していない, the TernaryDiagram shall 組成点から三角形分割を自動で作り、組成点の凸包の内側だけを塗り、凸包の外には色を付けない
5. Where 利用者が三角形の組み合わせ（どの 3 点で三角形を作るか）またはマスク（塗らない三角形）を指定した, the TernaryDiagram shall 自動の三角形分割の代わりに指定された組み合わせを使い、マスクした三角形を塗らない
6. If `z` が `None`、または `z` の要素数が組成点の数と一致しない, then the TernaryDiagram shall 期待する要素数を示すメッセージ付きの `ValueError` を送出する
7. If 自動の三角形分割で、異なる組成が 3 点未満しかない、またはすべての組成点が一直線上にある, then the TernaryDiagram shall 三角形分割できない理由を示すメッセージ付きの `ValueError` を送出する
8. When 自動の三角形分割で、正規化後に同じ組成になる点が複数あった, the TernaryDiagram shall そのうち 1 点の値だけを使って描画し、使わなかった点の数と、描画前に値を集約する必要があることを示す `UserWarning` を、利用者のコード位置を発生位置として出す

### Requirement 2: 関数を三角形全体に塗る（heatmapf）
**Objective:** As a 理論式や機械学習モデルの予測を描きたい研究者, I want 関数 f(a, b, c) を渡すだけで三角形全体を塗りたい, so that 自分で格子を作って評価し、座標を変換する手間がなくなる

#### Acceptance Criteria
1. The TernaryDiagram shall 3 成分の組成から値を返す関数と、格子の細かさ（`scale`: 三角形の各辺の分割数）を受け取り、三角形全体を正則な三角格子の小三角形で塗る描画メソッド `heatmapf` を提供する
2. When `heatmapf` を呼んだ, the TernaryDiagram shall 関数を 1 回だけ呼び、すべての評価点の 3 成分を、頂点ラベルと同じ順の 3 つの引数（成分ごとの 1 次元の数値配列で、各評価点の 3 成分の合計は 1）として渡す
3. When 塗り方を指定せずに（既定の flat で）`heatmapf` を呼んだ, the TernaryDiagram shall 各小三角形の重心で関数を評価し、その値に対応する 1 色で小三角形を塗り、三角形の辺上と頂点では関数を評価しない
4. When 塗り方に gouraud を指定して `heatmapf` を呼んだ, the TernaryDiagram shall 三角形の辺と頂点を含む格子点で関数を評価し、各小三角形の内部を 3 頂点の値の間で線形に変化する色で塗る
5. Where `scale` を省略した, the TernaryDiagram shall docstring に記載した既定の分割数の格子で描画する
6. When 関数が評価点の数と同じ要素数の 1 次元配列、または 1 列か 1 行の 2 次元配列を返した, the TernaryDiagram shall その値を評価点の順に 1 次元に並べて塗りに使う
7. If 呼び出し可能でないものを関数として渡した, then the TernaryDiagram shall 関数を渡す必要があることを示すメッセージ付きの `TypeError` を送出する
8. If 関数の戻り値が 6 の形でない、または数値として解釈できない, then the TernaryDiagram shall 期待する要素数と、1 点ずつしか計算できない関数を配列に対応させる方法を示すメッセージ付きの `ValueError` を送出する
9. If 関数の評価中に例外が発生した, then the TernaryDiagram shall その例外を置き換えずにそのまま利用者へ伝える

### Requirement 3: 正則な三角格子の生成
**Objective:** As a 関数ヒートマップと同じ格子で自分の計算や検証をしたい研究者, I want 図を作らずに三角形内の正則な格子（組成と小三角形の組）を得たい, so that 格子の作り方を自分で実装せずに済み、ヒートマップの評価点を確かめられる
#### Acceptance Criteria
1. The 三角格子生成関数 shall 分割数 n を受け取り、各成分が 0, 1/n, …, 1 のいずれかで 3 成分の合計が 1 になるすべての組成（(n+1)(n+2)/2 個）と、それらを頂点とする n² 個の小三角形（各小三角形は 3 つの組成の番号の組）を返す
2. The 三角格子生成関数 shall 返す小三角形が、三角図の三角形全体を重なりも隙間もなく、すべて同じ大きさで覆うようにする
3. The 三角格子生成関数 shall 同じ n に対して常に同じ並び順の結果を返し、図や Axes を必要とせず、引数以外の状態を読み書きしない
4. If n が整数でない（真偽値を含む）, then the 三角格子生成関数 shall 受け付けられる値を示すメッセージ付きの `TypeError` を送出する
5. If n が 1 未満, then the 三角格子生成関数 shall 受け付けられる範囲を示すメッセージ付きの `ValueError` を送出する
6. If `heatmapf` に不正な `scale` を渡した, then the TernaryDiagram shall 4・5 と同じ例外を送出する

### Requirement 4: 値を決められない三角形の扱い
**Objective:** As a 欠損値を含むデータや、一部の組成で定義されない関数を描く研究者, I want 値のない場所を塗らずに残りを描きたい, so that 欠損やおかしな値が図全体の色を壊さない
#### Acceptance Criteria
1. If `tripcolor` の `z` に欠損値（NaN）または無限大が含まれる, then the TernaryDiagram shall 塗り方にかかわらず、その組成点を頂点に持つ三角形を塗らず、残りの三角形を描画する
2. If `heatmapf` の関数が一部の評価点で NaN または無限大を返した, then the TernaryDiagram shall その評価点の値を色に使う小三角形（flat ではその重心を持つ小三角形、gouraud ではその格子点を頂点に持つ小三角形）を塗らず、残りの小三角形を描画する
3. If 塗れる三角形が 1 つもない（すべての値が有限でない、またはすべての三角形がマスクされている）, then the TernaryDiagram shall 塗れる三角形がない理由を示すメッセージ付きの `ValueError` を送出する

### Requirement 5: 値の範囲とカラーマップ（既存の描画との統一）
**Objective:** As a ヒートマップに散布図や等高線を重ねる研究者, I want 色の範囲を `scatter` / `contour` と同じ引数と同じ規則で決めたい, so that 同じ物性値を描画の種類によらず同じ色で比べられる
#### Acceptance Criteria
1. The TernaryDiagram shall `tripcolor` と `heatmapf` で、色の範囲の下限 `z_min` と上限 `z_max` を `scatter` / `contour` と同じ名前で受け付ける
2. The TernaryDiagram shall `z_min` / `z_max` の別名として `vmin` / `vmax` を受け付け、別名で指定したときも同じ色の範囲で描画する
3. If `z_min` と `vmin`、または `z_max` と `vmax` を同時に指定した, then the TernaryDiagram shall `scatter` / `contour` と同じメッセージの `ValueError` を送出する
4. While `z_min` と `z_max` を指定していない, the TernaryDiagram shall 色の範囲の下限と上限を、塗りに使う値（`tripcolor` では `z`、`heatmapf` では関数の戻り値）のうち有限な値の最小値と最大値にする
5. When `z_min` と `z_max` の一方だけを指定した, the TernaryDiagram shall 指定した側をその値にし、もう一方を 4 と同じ規則で決める
6. Where 利用者が色の正規化方法（matplotlib の norm）を指定し、`z_min` / `z_max` を指定していない, the TernaryDiagram shall 4・5 の自動の範囲を適用せず、指定された正規化方法に従う
7. Where カラーマップを指定しない, the TernaryDiagram shall `scatter` / `contour` と同じ既定のカラーマップで塗る

### Requirement 6: カラーバーと描画後のレイアウト
**Objective:** As a 研究者, I want 新しい描画でもカラーバーとレイアウトの扱いが既存の描画と同じであってほしい, so that 描画の種類ごとに書き方を変えずに済む
#### Acceptance Criteria
1. The TernaryDiagram shall `tripcolor` と `heatmapf` で、カラーバーの自動追加を「追加する」「追加しない」「未指定（既定）」の 3 通りで呼び出しごとに指定する引数 `colorbar` を、`scatter` / `contour` と同じ名前・同じ意味で受け付ける
2. When `colorbar` を指定せずに `tripcolor` または `heatmapf` を呼んだ, the TernaryDiagram shall `plot-side-effects` が `scatter` / `contour` に定めた既定の規則（三角図にまだカラーバーがなければ追加し、すでにあれば v3.x では追加したうえで三角図ごとに 1 回予告の警告を出す）に従う
3. The TernaryDiagram shall `tripcolor` と `heatmapf` の描画後のレイアウト自動調整を、TernaryDiagram の作成時の設定に従い、既存の描画メソッドと同じ規則で行う
4. If `colorbar` に `None` / `True` / `False` 以外の値を渡した, then the TernaryDiagram shall `scatter` / `contour` と同じ `TypeError` を送出する
5. If `tripcolor` または `heatmapf` に旧名 `flag_cbar` を渡した, then the TernaryDiagram shall `flag_cbar` を受け付けず、代わりに `colorbar` を使うよう示すメッセージ付きの `TypeError` を送出する
6. When カラーバーを自動で追加した, the TernaryDiagram shall 追加したカラーバーを、返却した描画オブジェクトから参照できるようにする
7. When `tripcolor` または `heatmapf` の戻り値を `TernaryDiagram.colorbar()` に渡した, the TernaryDiagram shall その描画と同じ色の範囲とカラーマップのカラーバーを作る

### Requirement 7: 戻り値と既存の描画との共存
**Objective:** As a ヒートマップに散布図・等高線・タイラインを重ねる研究者, I want 呼び出し順に関係なくヒートマップが他の要素を隠さず、matplotlib の機能もそのまま使えること, so that 重ね描きの順番を気にせずに論文用の図を仕上げられる
#### Acceptance Criteria
1. When `tripcolor` または `heatmapf` の描画が完了した, the TernaryDiagram shall 塗った三角形を表す matplotlib の描画オブジェクト（flat では多角形の集合、gouraud では三角形メッシュ）を返す
2. While 重なり順を指定していない, the TernaryDiagram shall `tripcolor` と `heatmapf` の塗りを、呼び出し順にかかわらず、三角図のグリッドと外枠、`plot` の線、`scatter` の点、`contour` の等高線より奥に描く
3. Where 利用者が重なり順を指定した, the TernaryDiagram shall 利用者の指定を優先する
4. The TernaryDiagram shall `tripcolor` と `heatmapf` に渡されたその他のキーワード引数を、値を変えずに matplotlib の描画関数へ渡す
5. If 塗り方に flat と gouraud 以外を指定した, then the TernaryDiagram shall 受け付けられる値を示すメッセージ付きの `ValueError` を送出する
6. If 塗りの値と衝突するキーワード引数（色の直接指定 `c`、三角形ごとの色 `facecolors`）を渡した, then the TernaryDiagram shall `z`（`heatmapf` では関数の値）と同時に使えないことを示す `ValueError` を送出する
7. If `heatmapf` に三角形の組み合わせまたはマスクを指定した, then the TernaryDiagram shall 格子は変えられないことと、塗らない領域は関数が NaN を返すことで指定できることを示す `ValueError` を送出する
8. If 入力の検証で例外を送出した、または関数の評価中に例外が発生した, then the TernaryDiagram shall 三角図に何も追加しない
9. When `tripcolor` または `heatmapf` で描画した, the TernaryDiagram shall 描画に使った 2 次元座標（`tripcolor` では組成点、`heatmapf` では関数の評価点）を、既存の描画と同じく描画の種類名（`"tripcolor"` / `"heatmapf"`）ごとに `x_` / `y_` に記録する
10. The TernaryDiagram shall 三角図の土台（外枠・グリッド・目盛り・ラベル）と、既存の描画メソッド（`scatter`・`contour`・`plot`・`annotate`・`colorbar`）の挙動を変えない

### Requirement 8: 実用的な速さと依存
**Objective:** As a 細かい格子で関数を描きたい研究者, I want 1 万個程度の三角形でも待たされずに描けること, so that 格子の細かさを気にせず試行錯誤できる
#### Acceptance Criteria
1. When `scale=100`（1 万個の小三角形）で `heatmapf` を呼んだ, the TernaryDiagram shall 関数の評価時間と図の保存を除き、一般的な開発用 PC で 1 秒以内に描画オブジェクトを返す
2. The ternary-diagram shall 本機能のために、numpy と matplotlib 以外のインストール時の依存パッケージを要求しない

### Requirement 9: ドキュメント
**Objective:** As a 新しい描画を使い始める研究者, I want 引数の意味と使い分けを docstring と変更履歴で確認したい, so that ソースコードを読まずに正しく使える
#### Acceptance Criteria
1. The TernaryDiagram shall `tripcolor` と `heatmapf` の docstring（英語、NumPy スタイル）に、各引数の意味と既定値、戻り値、使用例、ラップしている matplotlib 関数のドキュメントへのリンク、flat と gouraud の違い（`heatmapf` では評価点の違いを含む）を書く
2. The TernaryDiagram shall `heatmapf` の docstring に、関数が受け取る引数の形と順序、返す値の形、1 点ずつしか計算できない関数を配列に対応させる方法、塗らない領域を NaN で指定する方法を書く
3. The 三角格子生成関数 shall 戻り値の形と並び順を説明し、実行可能な使用例を含む docstring を持つ
4. The ternary-diagram shall CHANGELOG の Unreleased の New features に、追加した描画メソッド（`tripcolor`・`heatmapf`）と三角格子生成関数を記載する
5. The ternary-diagram shall `tripcolor`・`heatmapf`・三角格子生成関数の docstring の使用例を、プロジェクト共通の docstring 例の規約（描画の例はレイアウトエンジン付きの図を作って三角図に渡すところから始め、図を使わない関数の例は図を作らない。ファイルを書き出さない）に従って書き、共通の doctest 実行で FutureWarning を出さずに通るようにする
