# Requirements Document

## Project Description (Input)
**誰が困っているか**: `ternary-diagram` で三元系の組成マップを描く材料・化学系の研究者（新しく使い始める人と、v4.0.0 へ移行する既存の利用者）。

**現状**: 使い方を知る手段が少ない。docstring には説明が空の引数（`, by default None` だけのもの）が多く、`contour` の `fill` と `flag_cbar` は説明すらない。ドキュメントサイト（Sphinx + MyST-NB + sphinx-book-theme、ノートブックは実行せず保存済みの出力を表示）は API の自動生成とサンプルノートブック（`docs_src/tutorials/` は `example/` へのシンボリックリンク）だけで、「軸タイトルを付けたい」「相図を描きたい」といった目的から使い方をたどれない。README は同じコードを 2 回載せていて長い。新しい機能（カスタマイズ、相図、ヒートマップ、副作用の制御）が増えるほど、この問題は大きくなる。

**何を変えるか**: すべての公開メソッドと引数に、意味・既定値・例が書かれた docstring をそろえる（新しい API の docstring は、それを追加する spec が書く。本 spec は既存メソッドの不足を埋めて書き方をそろえる）。目的別の使い方ページ（はじめに、見た目の変え方、相図の描き方（`fill` / `text`）、ヒートマップと等高線の使い分け、レイアウトとカラーバー（v4.0.0 への移行方法を含む））を作り、ドキュメントの目次を整理する。README を概要・インストール・最小の例・ドキュメントへのリンクに絞る。ドキュメントが警告なしでビルドでき、フッターの広告スクリプトも残っている状態を保つ。

**範囲外**: mpltern / python-ternary との使い分け表、日本語ドキュメント、ホスティングの変更、テーマやビルドの仕組みの変更。docstring は NumPy スタイルの英語。Upstream は `plot-side-effects`、`diagram-customization`、`region-plots`、`heatmaps`。

詳細は同じディレクトリの `brief.md` を参照。

## Introduction

ternary-diagram の使い方を知る手段は、空欄の多い docstring、API リファレンスの自動生成、サンプルノートブックだけで、目的（軸タイトルを付けたい、相図を描きたい、v4.0.0 に備えたい）から使い方をたどれない。上流の 4 つの spec（`plot-side-effects`、`diagram-customization`、`region-plots`、`heatmaps`）と直接実装の `annotate-plain-text` で API と挙動が増え、v4.0.0 で既定値が変わる予定もあるので、この不足はさらに大きくなる。roadmap の Implementation Order では、本機能はこれらすべてのマージ後に最後に入る。

本機能では、既存の公開 API の docstring の不足を埋めて書き方をそろえ、目的別の使い方ページと v4.0.0 への移行ページを作り、ドキュメントの目次と README を整理する。ドキュメントのコード例は、公開する版のライブラリでそのまま動き、警告を出さず、表示している図と一致する状態にする。ドキュメントのテーマ、公開の仕組み、フッターの広告スクリプトは今のまま保つ。

## Boundary Context

- **In scope**:
  - `TernaryDiagram` の既存の公開 API のうち、上流 spec が担当しない docstring の充実と書き方の統一。対象は、クラスの要約と説明、作成時の引数 `materials`・`ax`・`auto_latex_notation`、`__init__` の Examples 節（本機能だけが持つ）、メソッド `scatter`・`contour`・`plot`・`annotate`・`colorbar()`（カラーバーを追加するメソッド。`scatter` / `contour` の `colorbar` 引数とは別）、プロパティ `ax`・`fig`、属性 `x_`・`y_`
  - `utils` モジュールの既存の公開関数（`check_ax`・`check_2d_vector`・`check_1d_vector`・`three2two`・`get_label`）の docstring の充実
  - `__init__` の Examples 節を書き直して共通の doctest ランナーで通るようにした後、ランナーが今の `__init__` の例に付けている xfail の印を外すこと
  - API リファレンスに `TernaryDiagram` の作成時の引数の説明が表示されること
  - 目的別の使い方ページ（はじめての三角図、見た目の変え方、相図の描き方、ヒートマップと等高線の使い分け、レイアウトとカラーバー）と、v4.0.0 への移行ページ
  - ドキュメントのトップページと目次の整理
  - README の刷新
  - example ノートブック（チュートリアル）の更新: 非推奨の引数の置き換えと、FutureWarning を出さないコードへの書き換え
  - ドキュメントのコード例の実行可能性とビルドの検証、CHANGELOG の該当項目
- **Out of scope**:
  - mpltern / python-ternary との使い分け表
  - 日本語ドキュメント、ホスティング先の変更、テーマの変更
  - 上流が追加・変更する API の docstring: `tight_layout` の Parameters の項目、`scatter` / `contour` の Parameters の `colorbar`・`flag_cbar` の項目（`plot-side-effects`）、`*_kw` 引数の Parameters の項目・`set_*` メソッド（`*_kw` の使用例を含む）・部品の取り出し口・クラスの Notes（`diagram-customization`）、`annotate` / `scatter` に足される整形の切り替え引数の項目（`annotate-plain-text`）、`fill`・`text`（`region-plots`）、`tripcolor`・`heatmapf`（`heatmaps`）
  - 上流が `utils` に追加する公開関数の docstring: `check_optional_bool`・`check_bool`（`plot-side-effects`）、`get_tick_values`・`get_edge_points`・`get_grid_segments`・`get_axis_label_position`・`get_tick_formatter`・型別名 `TickFormat`（`diagram-customization`）、`get_triangular_lattice`（`heatmaps`）
  - 共通の doctest ランナー（`tests/test_doctests.py`）の作成と、`__init__` の xfail の印を外すこと以外の変更（`plot-side-effects`）
  - ライブラリの挙動と既定値（既定のカラーマップを含む）の変更、v4.0.0 での既定値の切り替えそのもの、警告文の文面
- **Adjacent expectations**:
  - 上流の 4 spec と `annotate-plain-text` が実装済みで、それぞれの docstring と CHANGELOG の項目がそろっていること。使い方ページと移行ページは、それらに書かれた名前・既定値・警告文と一致させる
  - 共通の doctest ランナー（steering の tech.md「Docstring Examples」）が、本機能が担当する docstring を含む公開 API の例を、FutureWarning をエラーとして実行すること。本機能は自分の docstring の例の実行に、別のランナーを作らない
  - 上流が書いた docstring に誤りや使い方ページとの食い違いを見つけた場合、および上流の docstring の例が共通の doctest ランナーで失敗する場合、本機能では書き換えず、担当 spec の課題として記録する
  - v4.0.0 のリリース作業は、本機能の移行ページを参照し、既定値の切り替えに合わせて更新する

## Requirements

### Requirement 1: 既存の公開 API の docstring
**Objective:** As a API リファレンスやエディタのヘルプで引数を調べる利用者, I want 既存のメソッドのすべての引数に意味・受け付ける値・既定値が書かれていること, so that ソースを読まずに正しく呼び出せる

#### Acceptance Criteria
1. The TernaryDiagram docstrings shall 本機能が担当する各引数・プロパティ・属性（Boundary Context の対象）について、意味、受け付ける値の型と形、既定値とその既定値のときの挙動を記載する
2. The TernaryDiagram docstrings shall `contour` の `fill` について、真のとき塗りつぶした等高線図を、偽のとき線だけの等高線図を描くことを記載する
3. The TernaryDiagram docstrings shall 組成を受け取る引数について、成分の並びが `materials` の並び（上の頂点から反時計回り）と一致すること、各行の合計が 1 でなくてよいことを記載する
4. The TernaryDiagram docstrings shall 担当する各メソッドについて、戻り値の型と内容、ラップしている matplotlib 関数のドキュメントへのリンク、追加のキーワード引数が matplotlib にそのまま渡ることを記載する
5. The TernaryDiagram docstrings shall 担当する各メソッドと作成時の引数に、そのまま実行できる使用例を少なくとも 1 つ含める
6. The TernaryDiagram docstrings shall 担当するすべての docstring で、節の並び、型の書き方、既定値の書き方を 1 つの規約にそろえる
7. The TernaryDiagram docstrings shall 担当する docstring に、既定値だけで意味のない説明、同じ文の重複、実際の頂点の順序と異なる説明を含めない
8. The TernaryDiagram API reference shall `TernaryDiagram` の作成時のすべての引数（上流 spec が追加した引数を含む）の説明を表示する
9. The TernaryDiagram docstrings shall 上流 spec が担当する docstring の項目を書き換えず、同じ内容を別の項目に重複して記載しない
10. The ternary_diagram.utils docstrings shall 既存の公開関数（`check_ax`・`check_2d_vector`・`check_1d_vector`・`three2two`・`get_label`）について、要約、各引数の意味・受け付ける値・既定値、戻り値、送出する例外、そのまま実行できる doctest 形式の使用例を、1.6 と 1.7 と同じ規約で記載する

### Requirement 2: 目的別の使い方ページの構成
**Objective:** As a やりたいことは決まっているがメソッド名を知らない利用者, I want 目的から使い方のページをたどれること, so that API リファレンスを端から読まずに目的の図を描ける

#### Acceptance Criteria
1. The ternary-diagram docs shall 次の目的ごとに 1 ページずつ使い方ページを提供する: はじめての三角図、見た目の変え方、相図の描き方、ヒートマップと等高線の使い分け、レイアウトとカラーバー
2. The ternary-diagram docs shall 各使い方ページで、扱う目的ごとに、説明、そのまま実行できるコード例、その実行結果の図を示す
3. The ternary-diagram docs shall 各使い方ページから、そのページで使うメソッドの API リファレンスへリンクする
4. The ternary-diagram docs shall 使い方ページの本文とコード例を英語で書く
5. The ternary-diagram docs shall 使い方ページに表示する図に、図の内容を表す代替テキストを付ける

### Requirement 3: はじめての三角図のページ
**Objective:** As a ternary-diagram を初めて使う研究者, I want インストールから最初の図の保存までを 1 ページでたどりたい, so that すぐに自分のデータで三角図を描き始められる

#### Acceptance Criteria
1. The ternary-diagram docs shall インストール方法（pip と conda-forge）と、三角図を 1 つ描いて画像ファイルに保存するまでの最小の手順を示す
2. The ternary-diagram docs shall 組成の渡し方（成分の並びと頂点の対応、合計が 1 でなくてよいこと）を示し、表形式のデータ（pandas の DataFrame など）もそのまま渡せることを説明する
3. The ternary-diagram docs shall 既存の matplotlib の図の Axes に三角図を描く方法と、1 つの図に複数の三角図を並べる方法を示す
4. The ternary-diagram docs shall 頂点ラベルの化学式が自動で下付きの表記に整形されることと、整形を止める方法を示し、作成時の設定が及ぶ範囲（頂点ラベルと、それを引き継ぐ文字の配置。注釈の整形は `annotate-plain-text` の規則に従うこと）を示す
5. The ternary-diagram docs shall 描画メソッドの一覧（散布図・線・注釈・等高線・ヒートマップ・相領域の塗りつぶし・文字）と、それぞれの詳しい説明があるページへの案内を示す

### Requirement 4: 見た目の変え方のページ
**Objective:** As a 雑誌の規定に合わせて図を仕上げる研究者, I want 三角図の土台の見た目の変え方を目的別に知りたい, so that 目盛り・軸タイトル・ラベルを思いどおりに整えられる

#### Acceptance Criteria
1. The ternary-diagram docs shall 三角図の土台の 5 つの部品（外枠・グリッド・目盛りラベル・軸タイトル・頂点ラベル）それぞれについて、作成時に指定する方法と作成後に変更する方法を示す
2. The ternary-diagram docs shall グリッドと目盛りの間隔、目盛りの書式（百分率・割合・独自の書式）、両端の目盛りの表示を変える方法を示す
3. The ternary-diagram docs shall 軸タイトルの付け方と、どの辺の目盛りがどの成分を表し、値がどちら向きに増えるかを、図とともに示す
4. The ternary-diagram docs shall 部品を非表示にする方法と、matplotlib の線と文字のプロパティ（色・線幅・フォントサイズなど）を指定する方法を示す
5. The ternary-diagram docs shall 作成後の変更で、指定しなかった項目が直前の設定を引き継ぐことを示す
6. The ternary-diagram docs shall 部品の matplotlib のオブジェクトを取り出して直接変更する方法を示す
7. The ternary-diagram docs shall 同じ見た目の指定を複数の三角図で使い回す方法を示す

### Requirement 5: 相図の描き方のページ
**Objective:** As a 三元系の相図を描く研究者, I want 相領域の塗り分けと相の名前の置き方を知りたい, so that 座標変換を自分で書かずに相図を仕上げられる

#### Acceptance Criteria
1. The ternary-diagram docs shall 組成で指定した頂点を結ぶ相領域を塗り、凡例に表示する方法を示す
2. The ternary-diagram docs shall 相領域の頂点は渡した順に結ばれ、並べ替えや凸包の計算は行われないことを示す
3. The ternary-diagram docs shall 相の名前などの文字を組成の位置に置く方法と、化学式の自動整形を止める方法を示す
4. The ternary-diagram docs shall 相領域・グリッド・線・点・文字の既定の重なり順と、透明度や重なり順を変える方法を示す
5. The ternary-diagram docs shall 相図の例で、領域の区別を色だけに頼らず、凡例または文字のラベルでも示す
6. The ternary-diagram docs shall 等高線図の `fill` 引数と、相領域を塗る `fill` メソッドが別のものであることを示す

### Requirement 6: ヒートマップと等高線の使い分けのページ
**Objective:** As a 組成と物性値の分布を示す研究者, I want 値を色で表す描画の違いと選び方を知りたい, so that データの性質に合った図を選べる

#### Acceptance Criteria
1. The ternary-diagram docs shall 値を色で表す描画（色付きの散布図、等高線図、測定点のヒートマップ、関数のヒートマップ）を、入力データの種類、補間の有無、向いている場面で比べて示す
2. The ternary-diagram docs shall 測定点のヒートマップの 2 つの塗り方（三角形ごとに一色、なめらかな塗り）の違いを図で示す
3. The ternary-diagram docs shall 関数のヒートマップで関数がどう呼ばれるか（成分ごとの配列を受け取り、1 回だけ呼ばれること）、格子の細かさの変え方、塗らない領域の作り方を示す
4. The ternary-diagram docs shall 値の範囲（下限と上限）とカラーマップを指定する方法と、複数の描画で同じ範囲とカラーバーを共有する方法を示す
5. The ternary-diagram docs shall 欠損値（NaN）を含むデータを描いたときの結果を示す
6. The ternary-diagram docs shall カラーマップの選び方として、大小を表す値には明るさが単調に変わるカラーマップが、正負を表す値には中央が無彩色の発散型カラーマップが読み取りやすいことを示す

### Requirement 7: レイアウトとカラーバーのページ
**Objective:** As a 三角図を複数パネルや自分のレイアウトの図に組み込む研究者, I want レイアウトの自動調整とカラーバーの自動追加の制御方法を知りたい, so that 余白とカラーバーを意図どおりに保てる

#### Acceptance Criteria
1. The ternary-diagram docs shall 描画のたびのレイアウト自動調整の 3 通りの指定（有効・無効・未指定）と、それぞれの v3.x と v4.0.0 での挙動を示す
2. The ternary-diagram docs shall レイアウトエンジン（constrained など）を設定した図、複数のパネル、subfigure に三角図を描くときの推奨の書き方を示す
3. The ternary-diagram docs shall カラーバーの自動追加の 3 通りの指定と、すでにカラーバーがある三角図での扱いを示す
4. The ternary-diagram docs shall カラーバーを自動で追加せずに後から 1 本だけ追加し、ラベルなどを指定する方法を示す
5. The ternary-diagram docs shall v4.0.0 への移行ページへリンクする

### Requirement 8: v4.0.0 への移行ページ
**Objective:** As a v3.x のコードを v4.0.0 へ移行する既存の利用者, I want 何が変わり、自分のコードのどこをどう直せばよいかを 1 ページで確認したい, so that FutureWarning をなくし、v4.0.0 に上げても図が変わらないようにできる

#### Acceptance Criteria
1. The ternary-diagram docs shall v4.0.0 で変わる既定値（描画のたびのレイアウト自動調整、すでにカラーバーがある三角図へのカラーバーの自動追加。`annotate-plain-text` が注釈の整形の変更を FutureWarning で予告する場合はその変更も含む）と削除予定の引数（`flag_cbar`）を、v3.x と v4.0.0 の挙動の対比で一覧にする
2. The ternary-diagram docs shall 各 FutureWarning について、どの呼び出しで出るか、今の挙動を保つ書き方、新しい挙動を先取りする書き方を、警告文が示す方法と同じ内容で示す
3. The ternary-diagram docs shall 移行ページに引用する警告文を、公開する版のライブラリが実際に出す文面と一致させる
4. The ternary-diagram docs shall `flag_cbar` を使ったコードを新しい引数で書き換えた前後の例を示す
5. The ternary-diagram docs shall 影響を受ける呼び出しをすべて見つける方法（FutureWarning をエラーとして扱って実行する方法）を示す
6. The ternary-diagram docs shall 新しく追加された描画メソッドが `flag_cbar` を受け付けないことを示す
7. The ternary-diagram docs shall 移行ページを、トップページとレイアウトとカラーバーのページから 1 回の移動でたどれる位置に置き、リリースノートから参照できる固定の場所（URL）にする

### Requirement 9: ドキュメントのコード例の正しさ
**Objective:** As a ドキュメントのコードをコピーして使う利用者, I want 例がそのまま動き、警告を出さず、表示されている図と同じ結果になること, so that 例を信頼して自分のコードに取り込める

#### Acceptance Criteria
1. The ternary-diagram docs shall 使い方ページ、移行ページ、トップページ、README、本機能が担当する docstring のすべてのコード例を、公開する版のライブラリでエラーなく実行できるものにする
2. The ternary-diagram docs shall それらのコード例を、実行しても FutureWarning を出さないものにする。ただし、移行ページで移行前の書き方として示す例は除く
3. When ドキュメントを公開する, the ternary-diagram docs shall 使い方ページと移行ページに表示する図と出力を、公開する版のライブラリでそのページのコード例を実行した結果にする
4. If 使い方ページまたは移行ページのコード例が公開する版のライブラリで実行に失敗する, the ternary-diagram docs shall ドキュメントのビルドを失敗させ、壊れたページを公開しない
5. The ternary-diagram docs shall 使い方ページと移行ページで実行して結果を示すコード例を、ライブラリのランタイム依存（numpy と matplotlib）だけで、ネットワークや外部のデータファイルなしに実行できるものにする

### Requirement 10: ドキュメントのトップページと目次
**Objective:** As a ドキュメントサイトを訪れた利用者, I want トップページと目次から目的のページへ迷わず進みたい, so that 必要な情報に短い時間でたどり着ける

#### Acceptance Criteria
1. The ternary-diagram docs shall トップページに、ライブラリの概要、インストール方法、最小の例、使い方ページ・チュートリアル・API リファレンス・移行ページへの案内を置く
2. The ternary-diagram docs shall サイドバーの目次を「使い方（User guide）」「チュートリアル（Tutorials）」「API リファレンス（API Reference）」の区分で構成し、すべてのページをいずれかの区分に含める
3. The ternary-diagram docs shall 既存のチュートリアルのページと API リファレンスのページの場所（URL）を変えない
4. The ternary-diagram docs shall 使い方ページの一覧とチュートリアルの一覧のそれぞれに、各ページで何ができるかを示す 1 行の説明を付ける
5. The ternary-diagram docs shall トップページの最小の例を、README の最小の例と同じコードにする

### Requirement 11: example ノートブック（チュートリアル）の更新
**Objective:** As a チュートリアルのノートブックを手元で実行する利用者, I want ノートブックが非推奨の書き方を使わず、警告なしに同じ図を描くこと, so that チュートリアルをそのまま自分の作業の出発点にできる

#### Acceptance Criteria
1. The example notebooks shall 非推奨の引数（`flag_cbar`）を使わず、置き換え先の引数で同じ意味の図を描く
2. When ノートブックが使うパッケージがそろった環境で、example ノートブックを公開する版のライブラリで先頭から順に実行した, the example notebooks shall エラーと FutureWarning を出さない
3. The example notebooks shall 保存済みの出力と出力画像を、更新後のコードを実行した結果にする
4. The example notebooks shall 既存のデータファイルと出力画像の場所とファイル名を変えない
5. The example notebooks shall 先頭のセルを、ページのタイトルとなる見出しのままにする

### Requirement 12: README の刷新
**Objective:** As a GitHub や PyPI で初めてこのライブラリを見る人, I want 何ができるか、どう入れるか、最小の使い方を短く知りたい, so that 使うかどうかをすぐに判断し、詳しい情報へ進める

#### Acceptance Criteria
1. The README shall 内容を、概要（何ができるか、ランタイム依存が numpy と matplotlib だけであること）、主な機能の一覧、インストール方法、最小の例 1 つとその出力画像、ドキュメント（使い方ページ・API リファレンス・移行ページ）へのリンク、変更履歴とライセンスへのリンクに絞る
2. The README shall 同じ内容のコード例を重複して載せない
3. The README shall 主な機能の一覧に、上流の 4 spec が追加した機能（土台の見た目の変更、相図、ヒートマップ、レイアウトとカラーバーの制御）を含める
4. The README shall 画像とリンクを、GitHub と PyPI のどちらで表示しても有効な絶対 URL で書く
5. The README shall 最小の例を、掲載している出力画像と同じ図を描くコードにする
6. The README shall 既存のバッジ（Python のバージョン、ライセンス、PyPI、ダウンロード数、CI、docs、Ruff、conda-forge）を残す

### Requirement 13: ドキュメントのビルドと公開
**Objective:** As a ライブラリのメンテナ, I want ページを足してもドキュメントが今の手順で警告なくビルドされ、今の仕組みで公開されること, so that リリースのたびに手を入れずに正しいドキュメントを届けられる

#### Acceptance Criteria
1. When CI と同じ手順（API リファレンスの生成とビルド）でドキュメントをビルドした, the ternary-diagram docs shall 警告とエラーを 1 件も出さずにビルドを完了する
2. The ternary-diagram docs shall すべてのページのフッターに、今と同じ広告スクリプトを含める
3. The ternary-diagram docs shall 正式版のタグで GitHub Pages に公開する今の仕組み、テーマ、ホスティング先を変えない
4. The ternary-diagram docs shall ドキュメントのビルドに、ライブラリ自身とドキュメント用の追加依存（`docs` extras）以外のパッケージを必要としない
5. The ternary-diagram docs shall API リファレンスを今と同じくビルド時に docstring から生成し、生成物をリポジトリに含めない

### Requirement 14: 変更履歴
**Objective:** As a ternary-diagram を更新する利用者, I want ドキュメントの追加と移行ページの場所を変更履歴で知りたい, so that 更新時に移行ページへすぐ進める

#### Acceptance Criteria
1. The ternary-diagram shall CHANGELOG の Unreleased に、使い方ページと移行ページの追加、README の刷新を記載し、移行ページへのリンクを含める
