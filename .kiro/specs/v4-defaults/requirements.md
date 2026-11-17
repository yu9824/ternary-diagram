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

## Introduction

v4.0.0 で行う破壊的変更を、利用者が前もって知り、自分のペースで移行できる形で行う。リリースは 2 段に分ける。

- **予告の段（v3.4.0）**: 図の結果は変えず、v4.0.0 で動かなくなる書き方（オプションの位置引数）に FutureWarning を出し、見た目が変わる点（縦横比の固定）を文書で予告する
- **切り替えの段（v4.0.0）**: v3.2.1 から予告している既定値を切り替え、非推奨の `flag_cbar` を削除し、オプションをキーワード専用にし、縦横比の固定を変える。予告の FutureWarning は出さなくなる

本書の「v3.4.0」は予告の段、「v4.0.0」は切り替えの段のリリースを指す。

## Boundary Context

- **In scope**:
  - オプション引数の位置引数での指定の予告（v3.4.0）とキーワード専用化（v4.0.0）
  - v3.2.1 から予告している 3 つの既定値の切り替え（レイアウト調整、カラーバーの自動追加、注釈の化学式の整形）と `flag_cbar` の削除（v4.0.0）
  - 登録済みのカラーバーの有無の判定の修正（v4.0.0）
  - 縦横比の固定方法の変更（v4.0.0）と、その文書での予告（v3.4.0）
  - CHANGELOG、移行ページ、関係する docstring の更新
- **Out of scope**:
  - Python 3.9 のサポート終了（別に決める）
  - 縦横比の固定方法を選ぶ新しい引数（追加しない。利用者は matplotlib の `set_aspect` で選ぶ）
  - 最初からキーワード専用の引数しか持たないメソッド（`tripcolor`・`heatmapf`・`set_*`・`annotate`・`text`・`plot`・`fill`）の引数の並び
  - ここに挙げた以外の既定値の変更と、新しい描画機能
- **Adjacent expectations**:
  - v3.4.0 には、本 spec と別に、`colorbar` の向きを `location` から決める変更（main に入り済み）と docs の Notes 節の並びの修正が入る。本 spec はそれらを持たない
  - 利用者向けの警告は既存の仕組み（発生位置が利用者の行になる、三角図ごと・理由ごとに 1 回）に乗る
  - conda-forge の配布の更新は本 spec の外で行う

## Requirements

### Requirement 1: オプションの位置引数の予告（v3.4.0）
**Objective:** As a 既存のコードで三角図を描いている研究者, I want v4.0.0 で動かなくなる位置引数の使い方を v3.x のうちに警告で知りたい, so that v4.0.0 に上げる前に自分のコードを直せる

#### Acceptance Criteria
1. The TernaryDiagram shall v3.4.0 で、次の引数を「v4.0.0 でキーワード専用にする引数」として扱う: `TernaryDiagram` の `ax`・`auto_latex_notation`、`scatter` の `z_min`・`z_max`・`annotations`・`colorbar`、`contour` の `z_min`・`z_max`・`fill`・`colorbar`、`colorbar` メソッドの `shrink`・`format`・`label`・`orientation`・`location`
2. When v3.4.0 で 1.1 の引数のいずれかを位置引数で渡した, the TernaryDiagram shall 渡された値を v3.3.0 と同じ意味で使い、図の結果を変えずに FutureWarning を出す
3. When 1.2 の FutureWarning を出す, the TernaryDiagram shall 位置引数で渡された引数の名前と、v4.0.0 ではキーワードで渡す必要があることと、キーワードで渡した書き方の例を文面に含める
4. When 1.2 の FutureWarning を出す, the TernaryDiagram shall 警告の発生位置を、そのメソッドを呼んだ利用者のコードの行にする
5. While 同じ三角図の同じメソッドで、位置引数での指定の FutureWarning をすでに出した, the TernaryDiagram shall 同じ理由の FutureWarning を再び出さない
6. When 1.1 の引数をすべてキーワードで渡した、または指定しなかった, the TernaryDiagram shall 位置引数での指定の FutureWarning を出さない
7. When データの引数（`materials`、`vector`、`z`、`text`、`func`、`mappable`、`set_*` の先頭の引数）を位置引数で渡した, the TernaryDiagram shall 位置引数での指定の FutureWarning を出さない

### Requirement 2: オプションのキーワード専用化（v4.0.0）
**Objective:** As a ternary-diagram の利用者, I want オプションはキーワードで渡すという規則がすべてのメソッドで揃っていること, so that 引数の並びを覚えずに読みやすいコードを書け、引数の意味の取り違えが起きない

#### Acceptance Criteria
1. If v4.0.0 で 1.1 の引数のいずれかを位置引数で渡した, the TernaryDiagram shall 何も描かずに `TypeError` を送出する
2. When v4.0.0 で 1.1 の引数をキーワードで渡した, the TernaryDiagram shall v3.x と同じ意味でその値を使う
3. The TernaryDiagram shall v4.0.0 でも、データの引数（`materials`、`vector`、`z`、`text`、`func`、`mappable`、`set_*` の先頭の引数）を位置引数でもキーワードでも受け付ける
4. The TernaryDiagram shall v4.0.0 で、位置引数での指定の FutureWarning を出さない

### Requirement 3: レイアウト調整の既定値の切り替え（v4.0.0）
**Objective:** As a 自分で図のレイアウトを決める研究者, I want 指定しない限りライブラリが図の余白を変えないこと, so that 自分の配置が描画のたびに崩されない

#### Acceptance Criteria
1. When v4.0.0 でレイアウト調整を指定せずに作った TernaryDiagram で、レイアウトエンジンのない図に描画した, the TernaryDiagram shall 図の余白と配置を変えず、FutureWarning を出さない
2. When v4.0.0 で `tight_layout=True` を指定した TernaryDiagram で、レイアウトエンジンのない図に描画した, the TernaryDiagram shall v3.x と同じく、描画のたびに図の余白を tight レイアウトで調整する
3. When v4.0.0 で `tight_layout=False` を指定した TernaryDiagram で描画した, the TernaryDiagram shall 図の余白と配置を変えない
4. While 描画先の図にレイアウトエンジンがある、または描画先が subfigure である, the TernaryDiagram shall v4.0.0 でも、レイアウト調整の指定にかかわらず図のレイアウトを変えない

### Requirement 4: カラーバーの自動追加の既定値の切り替え（v4.0.0）
**Objective:** As a 1 つの三角図に値で色付けした描画を重ねる研究者, I want 指定しない限りカラーバーが重複して付かないこと, so that 同じ値のカラーバーが何本も並ばない

#### Acceptance Criteria
1. When v4.0.0 で、三角図が付けたカラーバーがまだない状態で、カラーバーの指定をせずに値で色付けした描画（`scatter`・`contour`・`tripcolor`・`heatmapf`）をした, the TernaryDiagram shall カラーバーを 1 本追加する
2. When v4.0.0 で、三角図が付けたカラーバーがすでにある状態で、カラーバーの指定をせずに値で色付けした描画をした, the TernaryDiagram shall カラーバーを追加せず、FutureWarning を出さない
3. When v4.0.0 で `colorbar=True` を指定して値で色付けした描画をした, the TernaryDiagram shall すでにあるカラーバーの有無にかかわらず、カラーバーを追加する
4. When v4.0.0 で `colorbar=False` を指定して描画した, the TernaryDiagram shall カラーバーを追加しない
5. The TernaryDiagram shall v4.0.0 でも、利用者が matplotlib で直接付けたカラーバー（`TernaryDiagram.colorbar` や自動追加を通さないもの）を「三角図が付けたカラーバー」に数えない

### Requirement 5: 登録済みのカラーバーの有無の判定（v4.0.0）
**Objective:** As a 三角図のカラーバーに加えて自分でもカラーバーを付ける研究者, I want 三角図が付けたカラーバーが残っているかを正しく判定してほしい, so that v4.0.0 の既定で余分なカラーバーが付かない

#### Acceptance Criteria
1. When v4.0.0 で、三角図が付けたカラーバーと同じ描画に対して、利用者が matplotlib で別のカラーバーを付けた, the TernaryDiagram shall 三角図が付けたカラーバーをまだあるものとして扱い、続けてカラーバーの指定をせずに値で色付けした描画をしてもカラーバーを追加しない
2. When v4.0.0 で、三角図が付けたカラーバーを利用者が matplotlib の `remove()` で外した, the TernaryDiagram shall そのカラーバーをないものとして扱う
3. While 三角図が付けたカラーバーが複数ある, the TernaryDiagram shall 1 本でも外されずに残っていれば、三角図が付けたカラーバーがあるものとして扱う

### Requirement 6: 注釈の化学式の整形の既定値の切り替えと `flag_cbar` の削除（v4.0.0）
**Objective:** As a 試料名や mathtext を注釈に書く研究者, I want 予告どおりの既定の整形になり、廃止された引数を渡したら何を直せばよいかがわかること, so that v4.0.0 への移行で迷わない

#### Acceptance Criteria
1. When v4.0.0 で、`auto_latex_notation` を指定せずに `annotate` または `scatter` の注釈で文字を描いた, the TernaryDiagram shall 三角図の `auto_latex_notation` が真のときだけ、空白で区切った語のうち化学式の形をしたものを整形し、FutureWarning を出さない
2. When v4.0.0 で `annotate` または `scatter` に `auto_latex_notation` を明示した, the TernaryDiagram shall v3.x と同じく、その指定に従って整形する
3. If v4.0.0 で `scatter` または `contour` に `flag_cbar` を渡した, the TernaryDiagram shall 何も描かずに、`flag_cbar` は 4.0.0 で削除されたことと `colorbar` を使うことを文面に含む `TypeError` を送出する
4. The TernaryDiagram shall v3.4.0 では、`flag_cbar` を v3.3.0 と同じく非推奨の別名として受け付け、FutureWarning を出す

### Requirement 7: 縦横比の固定方法の変更（v4.0.0）と予告（v3.4.0）
**Objective:** As a constrained layout とカラーバーで論文用の図を作る研究者, I want 頂点ラベルが図の端からはみ出さないこと, so that matplotlib の版によらず図が欠けない

#### Acceptance Criteria
1. When v4.0.0 で TernaryDiagram を作った, the TernaryDiagram shall Axes の縦横比を 1:1 に固定し、データの範囲ではなく Axes の枠を三角図に合わせて縮める方法（matplotlib の `adjustable="box"`）で固定する
2. When v4.0.0 で `layout="constrained"` の図に、カラーバーの付く描画をした, the TernaryDiagram shall matplotlib 3.10 と 3.11 のどちらでも、3 つの頂点ラベルを図の範囲の内側に収める
3. When v4.0.0 で、利用者が TernaryDiagram の作成後に Axes の縦横比の固定方法を matplotlib で変えた, the TernaryDiagram shall 以後の描画と土台の描き直し（`set_*`）で、その設定を元に戻さない
4. The TernaryDiagram shall v3.4.0 では、縦横比の固定方法を v3.3.0 と同じ（データの範囲を広げる方法）に保ち、そのための FutureWarning は出さない
5. When v3.4.0 で、利用者が TernaryDiagram の作成後に Axes の縦横比の固定方法を matplotlib で変えた, the TernaryDiagram shall 以後の描画と土台の描き直しで、その設定を元に戻さない

### Requirement 8: 予告の段の互換性（v3.4.0）
**Objective:** As a v3.x を使い続ける利用者, I want v3.4.0 に上げても図が変わらないこと, so that 警告に対応するまで今の図をそのまま作れる

#### Acceptance Criteria
1. The TernaryDiagram shall v3.4.0 で、本 spec の変更によって描画の結果（artist の座標・色・zorder、カラーバーの有無、図のレイアウト）を v3.3.0 から変えない
2. The TernaryDiagram shall v3.4.0 で、v3.2.1 から出している既定値の変更の FutureWarning（レイアウト調整、カラーバーの重複、注釈の整形）を v3.3.0 と同じ条件で出す
3. The TernaryDiagram shall v3.4.0 と v4.0.0 のどちらでも、テスト一式とドキュメントの使い方ページを FutureWarning を出さずに実行できる状態を保つ

### Requirement 9: 利用者向けの文書
**Objective:** As a v4.0.0 への移行を準備する利用者, I want 何が変わり、どう書き換えれば今の挙動を保てるかを 1 か所で読みたい, so that 自分のコードへの影響を調べて直せる

#### Acceptance Criteria
1. When v3.4.0 を出す, the ternary-diagram の文書 shall CHANGELOG の Deprecations に、オプションの位置引数の非推奨（対象の引数の一覧）と、v4.0.0 での縦横比の固定方法の変更（影響: 凡例の `loc` の位置、自動で付くカラーバーの長さ）を載せる
2. When v3.4.0 を出す, the 移行ページ shall オプションの位置引数と縦横比の固定方法の節を持ち、それぞれ影響のある書き方、新しい書き方、v3.x のうちに新しい挙動を試す方法（縦横比は作成後に `set_aspect` で `adjustable="box"` にする）を示す
3. When v4.0.0 を出す, the ternary-diagram の文書 shall CHANGELOG に破壊的変更の節を設け、本 spec のすべての変更（既定値 3 つ、`flag_cbar` の削除、キーワード専用化、縦横比の固定方法、カラーバーの判定の修正）を載せる
4. When v4.0.0 を出す, the 移行ページ shall 各変更を「v4.0.0 で変わった」こととして書き直し、それぞれ v3.x の挙動に戻す書き方（`tight_layout=True`、`colorbar=True`、`auto_latex_notation` の明示、作成後に `set_aspect` で `adjustable="datalim"` にする）を示す
5. The ternary-diagram の文書 shall v3.4.0 と v4.0.0 のどちらでも、変更に関わる引数の docstring に、その版での既定と（v3.4.0 では）v4.0.0 での変更を書く
