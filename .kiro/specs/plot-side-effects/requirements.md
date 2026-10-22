# Requirements Document

## Project Description (Input)
`scatter` などの描画メソッドを呼ぶたびに、ternary-diagram が図全体へ副作用を起こしている。論文用の図を既存の matplotlib ワークフロー（`plt.subplots` による複数パネル、`layout="constrained"`、subfigure、手動のレイアウト調整）に組み込みたい材料・化学系の研究者ほど、この副作用に困っている。

- **誰が困っているか**: ternary-diagram で作った三角図を、自分で組んだ matplotlib の図に埋め込みたい利用者
- **今の状況**: `_ScatterPlotter` / `_ContourPlotter` / `_LinePlotter` / `_AnnotatePlotter` は描画の最後に必ず `fig.tight_layout()` を呼び、止める方法がない。`layout="constrained"` の図では、カラーバーを追加しない描画が先なら "The figure layout has changed to tight" という警告とともにレイアウトが tight に切り替わり、`z` を伴う描画でカラーバーを追加した直後に `tight_layout` を呼ぶ場合は `RuntimeError`（"Colorbar layout of new layout engine not compatible with old engine"）で失敗し、constrained のエンジンも外れる（matplotlib 3.10.8 で確認。警告だけで済むわけではない）。`scatter` / `contour` は `flag_cbar=True` が既定で、`z` があれば呼ぶたびにカラーバーを追加するので、contour の上に scatter を重ねるとカラーバーが 2 本になり、そのたびに本体の Axes が縮む。非推奨や FutureWarning を出す仕組みはない
- **何を変えるか**: 自動の `tight_layout` とカラーバーの自動追加を利用者が切り替えられるようにし、図にレイアウトエンジンがすでに設定されていればそれを上書きしない。v4.0.0 で既定値を変える予定の挙動に依存している利用者には、移行方法を書いた FutureWarning を出す（新しい既定を明示した利用者には出さない）。描画後の処理（レイアウト・カラーバー）を `_BasePlotter` の共通の仕組みにまとめ、後続の `region-plots` / `heatmaps` の Plotter もそれを使う。FutureWarning を出す小さな共通ヘルパーを作り、他の spec からも使えるようにする。v3.x の間は、引数を何も変えていない既存ユーザーの図の見た目を変えない

詳細は同じディレクトリの `brief.md` を参照。

## Introduction

ternary-diagram の描画メソッド（`scatter`・`contour`・`plot`・`annotate`）は、描画のたびに図全体のレイアウトを tight に調整し、`z` があればカラーバーを追加する。この副作用は止められず、`layout="constrained"` の図ではレイアウト方式が tight に切り替わるか、カラーバーを追加する `z` を伴う描画（`contour(z)` など）が `RuntimeError` で失敗してエンジンも外れ、subfigure 上の Axes では描画そのものが失敗し（matplotlib 3.10 で `AttributeError`）、重ね描きではカラーバーが重複する。

本機能では、描画後のレイアウト自動調整とカラーバーの自動追加を利用者が切り替えられるようにし、図に設定済みのレイアウト方式を上書きしないようにする。あわせて、v4.0.0 で既定値を変える予定の挙動について、結果が変わる呼び出しにだけ移行方法付きの FutureWarning を出す。v3.x の間は、引数を何も変えていない既存ユーザーの図の見た目を変えない。

## Boundary Context

- **In scope**:
  - 描画後のレイアウト自動調整の切り替えと、図に設定済みのレイアウトエンジンの尊重（subfigure 上での描画と、constrained の図でカラーバーを追加する描画を含む）
  - カラーバーの自動追加の切り替えと、すでにカラーバーがある図での扱い
  - 既存の 4 つの描画メソッド（`scatter`・`contour`・`plot`・`annotate`）への一律の適用
  - 非推奨・既定値変更の警告の出し方（形式・発生位置・頻度）の統一
  - テスト、変更した引数の docstring の Parameters の項目、CHANGELOG（Unreleased の見出しの組を含む）
  - 後続の spec と共有する基盤: 真偽値の検証関数（`utils`）と、公開 API の docstring の使用例を実行する共通のテスト
- **Out of scope**:
  - v4.0.0 での既定値の切り替えそのもの（本機能は予告と切り替え手段の用意まで）
  - カラーバーの見た目のカスタマイズ（既存の `colorbar()` メソッドの範囲を超えるもの）
  - 新しい描画メソッド（`fill`・`text`・ヒートマップなど）の追加
  - 三角図の土台（外枠・グリッド・目盛り・ラベル）の描き方
  - 使い方ページ、README、example ノートブックの書き換え
  - 変更した引数の項目以外の docstring（`TernaryDiagram.colorbar()` メソッドの docstring、`TernaryDiagram.__init__` の Examples 節など。`user-guide-docs` が持つ）
  - 利用者が手動で調整した余白（レイアウトエンジンを使わない調整）の自動検出。レイアウト自動調整を無効にする指定で対応する
- **Adjacent expectations**:
  - `region-plots` と `heatmaps` が追加する描画メソッドは、本機能が定めるレイアウト自動調整・カラーバー自動追加・警告の規則に従い、独自にレイアウト調整やカラーバー追加をしない
  - `diagram-customization` は三角図の土台を描くときにレイアウト調整を行わない。本機能も土台の描画には手を加えない
  - `user-guide-docs` は、本機能の警告文と CHANGELOG をもとに v4.0.0 への移行方法を書く
  - 後続の spec は、自分の使用例を本機能の共通のテストで確かめ（独自の実行テストを作らない）、真偽値の検証には本機能の検証関数を使う

## Requirements

### Requirement 1: 描画後のレイアウト自動調整の切り替え
**Objective:** As a 既存の matplotlib ワークフローに三角図を組み込む研究者, I want 描画のたびに行われるレイアウト自動調整を三角図ごとに有効・無効にしたい, so that 自分で決めた余白や複数パネルの配置を崩されず、描画のたびの余計な計算も避けられる

#### Acceptance Criteria
1. The TernaryDiagram shall 描画後のレイアウト自動調整を「有効」「無効」「未指定（既定）」の 3 通りで、TernaryDiagram の作成時に指定する手段を提供する
2. When レイアウト自動調整を無効にした TernaryDiagram で描画メソッドを呼んだ, the TernaryDiagram shall 図の余白とサブプロットの配置を変更しない
3. When レイアウト自動調整を有効にした TernaryDiagram で、レイアウトエンジンが設定されていない図に描画した, the TernaryDiagram shall 描画のたびに図全体の余白を tight レイアウトで調整する
4. When レイアウト自動調整を指定せずに作成した TernaryDiagram で、レイアウトエンジンが設定されていない図に描画した, the TernaryDiagram shall 本機能の導入前と同じく、描画のたびに図全体の余白を tight レイアウトで調整する
5. The TernaryDiagram shall 1 つの TernaryDiagram のすべての描画メソッド（`scatter`・`contour`・`plot`・`annotate`）に、同じレイアウト自動調整の設定を適用する
6. If レイアウト自動調整の指定に「有効」「無効」「未指定」のいずれでもない値が渡された, the TernaryDiagram shall 受け付けられる値を示すメッセージ付きの `TypeError` を送出する

### Requirement 2: 図に設定済みのレイアウトの尊重
**Objective:** As a `layout="constrained"` や subfigure で図を組む利用者, I want ライブラリが図のレイアウト方式を勝手に切り替えないこと, so that 図全体の配置が意図どおりに保たれる

#### Acceptance Criteria
1. While 描画先の図にレイアウトエンジン（constrained・compressed・tight など、利用者または matplotlib の設定ファイル・rcParams が設定したもの）が設定されている, the TernaryDiagram shall レイアウト自動調整の設定にかかわらず、そのレイアウトエンジンを置き換えず、自前のレイアウト調整も行わない
2. While 描画先の図にレイアウトエンジンが設定されている, the TernaryDiagram shall 描画によって matplotlib の「図のレイアウトが tight に変わった」旨の警告を発生させない
3. When ライブラリ自身が以前の描画で tight レイアウト調整を行った図に続けて描画した, the TernaryDiagram shall その図をレイアウトエンジンが設定されていない図として扱い、レイアウト自動調整の設定どおりに振る舞う
4. When subfigure に属する Axes に描画した, the TernaryDiagram shall エラーを送出せずに描画を完了し、レイアウト自動調整を行わない
5. Where 実行環境の matplotlib がレイアウトエンジンを照会する手段を持たない古いバージョンである, the TernaryDiagram shall その版で取得できる設定（constrained layout と tight layout の有効状態）からレイアウト設定の有無を判定し、本要件と同じ規則で振る舞う
6. When `layout="constrained"` で作った図で、カラーバーを追加する `z` を伴う描画をした（例: `contour(z)` の後に `scatter(z)` を重ねる）, the TernaryDiagram shall どの描画も例外を送出せずに完了し、図のレイアウトエンジンを変えない

### Requirement 3: カラーバーの自動追加の切り替え
**Objective:** As a 組成と物性値を等高線や散布図で示す研究者, I want 描画のたびにカラーバーを自動で追加するかを呼び出しごとに選びたい, so that 必要な数だけカラーバーを置き、本体の Axes が意図せず縮まないようにできる

#### Acceptance Criteria
1. The TernaryDiagram shall `z` を伴う描画メソッド（`scatter`・`contour`）で、カラーバーの自動追加を「追加する」「追加しない」「未指定（既定）」の 3 通りで呼び出しごとに指定する手段を提供する
2. When カラーバーの自動追加に「追加しない」を指定して描画した, the TernaryDiagram shall カラーバーを追加せず、図の Axes の数を変えない
3. When カラーバーの自動追加に「追加する」を指定して `z` を伴う描画をした, the TernaryDiagram shall 図にすでにカラーバーがあるかどうかにかかわらず、その描画のカラーバーを 1 本追加する
4. When カラーバーの自動追加を指定せずに `z` を伴う描画をし、その三角図にまだカラーバーがない, the TernaryDiagram shall 本機能の導入前と同じくカラーバーを 1 本追加する
5. When `z` を渡さずに `scatter` を呼んだ, the TernaryDiagram shall カラーバーの指定にかかわらずカラーバーを追加しない
6. When カラーバーを自動で追加した, the TernaryDiagram shall 追加したカラーバーを、描画メソッドが返した matplotlib のオブジェクトから参照できる状態にする
7. If カラーバーの自動追加の指定に「追加する」「追加しない」「未指定」のいずれでもない値が渡された, the TernaryDiagram shall 受け付けられる値を示すメッセージ付きの `TypeError` を送出する

### Requirement 4: すでにカラーバーがある三角図での扱い
**Objective:** As a contour の上に scatter を重ねる利用者, I want すでにカラーバーがある三角図へ 2 本目が既定で追加されることを知り、止められるようにしたい, so that 意図しないカラーバーの重複を避けられる

#### Acceptance Criteria
1. The TernaryDiagram shall 「三角図にすでにカラーバーがある」を、その TernaryDiagram を通じて追加されたカラーバー（自動追加と `colorbar()` メソッドによるもの）のうち、まだ削除されていないものが 1 本以上ある状態と定める
2. When カラーバーの自動追加を指定せずに `z` を伴う描画をし、その三角図にすでにカラーバーがある, the TernaryDiagram shall 本機能の導入前と同じくカラーバーを追加し、v4.0.0 では追加されなくなることと移行方法を示す FutureWarning を出す
3. When 利用者がカラーバーを削除した後に `z` を伴う描画をした, the TernaryDiagram shall 削除済みのカラーバーを判定に含めない
4. The TernaryDiagram shall 判定に含めるカラーバーの範囲（TernaryDiagram を通じて追加したものに限り、matplotlib の関数で直接追加したものは含めないこと）を、カラーバーの指定を受け付ける引数の docstring に記載する

### Requirement 5: 既存の `flag_cbar` 引数との互換
**Objective:** As a `flag_cbar` を使ってカラーバーを制御している既存ユーザー, I want 既存のコードがそのまま動き、名前が変わる場合は移行先を知りたい, so that 自分のペースで新しい書き方へ移れる

#### Acceptance Criteria
1. The TernaryDiagram shall v3.x の間、`scatter` と `contour` の `flag_cbar` 引数を、従来と同じ意味（真ならカラーバーを追加し、偽なら追加しない）で受け付ける
2. When 利用者が `flag_cbar` を明示的に指定して描画した, the TernaryDiagram shall それを明示的なカラーバーの指定として扱い、既定値の変更に関する警告を出さない
3. Where `flag_cbar` に代わる新しい名前のカラーバー指定が導入される, the TernaryDiagram shall `flag_cbar` が指定されたときに、新しい名前と、`flag_cbar` を削除する予定のバージョンを示す FutureWarning を出す
4. If 同じ呼び出しで `flag_cbar` と、それに代わる新しい名前のカラーバー指定の両方が指定された, the TernaryDiagram shall 両方は同時に指定できない旨のメッセージ付きの `ValueError` を送出する

### Requirement 6: 既定値の変更の予告と警告の出し方
**Objective:** As a 既存のコードを v4.0.0 へ移行する利用者, I want 既定値の変更で結果が変わる呼び出しだけに、移行方法付きの警告を受け取りたい, so that 直す必要がある箇所だけを、迷わず直せる

#### Acceptance Criteria
1. The TernaryDiagram shall v4.0.0 で予定する既定値として「描画のたびのレイアウト自動調整を行わない」ことを、該当する引数の docstring と CHANGELOG に示す
2. The TernaryDiagram shall v4.0.0 で予定する既定値として「すでにカラーバーがある三角図にはカラーバーを自動で追加しない」ことを、該当する引数の docstring と CHANGELOG に示す
3. If 未指定（既定）のまま行われた描画の結果が、v4.0.0 で予定する既定値のもとでは変わる, the TernaryDiagram shall FutureWarning を出す
4. If 未指定（既定）のまま行われた描画の結果が、v4.0.0 で予定する既定値のもとでも変わらない（例: 図にレイアウトエンジンが設定されていてレイアウト自動調整を行わない場合）, the TernaryDiagram shall 既定値の変更に関する警告を出さない
5. When 利用者がレイアウト自動調整またはカラーバーの自動追加を明示的に指定した, the TernaryDiagram shall 明示した項目について既定値の変更に関する警告を出さない
6. The TernaryDiagram shall 既定値の変更に関する FutureWarning の本文に、変わる挙動、変更予定のバージョン（4.0.0）、今の挙動を保つための指定方法、新しい挙動を今から使うための指定方法を含める
7. The TernaryDiagram shall 非推奨と既定値の変更に関する警告を、ライブラリ内部の行ではなく、利用者のコードで描画メソッドや TernaryDiagram を呼び出した行を発生位置として報告する
8. While 同じ TernaryDiagram で同じ理由の既定値の変更に関する警告をすでに出している, the TernaryDiagram shall その警告を描画のたびに繰り返さない
9. The ternary-diagram shall 非推奨に関する警告と既定値の変更に関する警告を、どちらも FutureWarning として、同じ形式の本文（何が変わるか、いつ変わるか、どう書けばよいか）で出す

### Requirement 7: v3.x での後方互換
**Objective:** As a 引数を何も変えていない既存ユーザー, I want v3.x の新しいリリースへ更新しても図の見た目とコードの動作が変わらないこと, so that 安心して更新できる

#### Acceptance Criteria
1. While 利用者がレイアウト自動調整とカラーバーの自動追加のどちらも指定しておらず、図にレイアウトエンジンが設定されていない, the TernaryDiagram shall 描画後の図の余白とカラーバーの本数を、本機能の導入前と同じにする
2. The TernaryDiagram shall 既存の描画メソッドの戻り値の型と、matplotlib へそのまま渡す追加のキーワード引数の扱いを変えない
3. The TernaryDiagram shall `scatter` と `contour` の既存の位置引数の並びで書かれた呼び出しを、本機能の導入前と同じ意味で受け付ける。ただし、6 番目の位置引数（カラーバーの指定）に真偽値以外（`0`・`1` など）を渡す呼び出しは 3.7 により `TypeError` になり、この非互換を CHANGELOG の Breaking changes に記載する
4. The TernaryDiagram shall `colorbar()` メソッドの既存の引数、既定値、戻り値を変えない

### Requirement 8: ドキュメントと変更履歴
**Objective:** As a ternary-diagram を更新する利用者, I want 何が変わり、何が今後変わるのかを docstring と CHANGELOG で確認したい, so that 警告を見る前に移行の準備ができる

#### Acceptance Criteria
1. The ternary-diagram shall CHANGELOG の Unreleased の見出しを Breaking changes / New features / Deprecations / Bug fixes / Other changes の組にそろえ、Breaking changes に `scatter`・`contour` のカラーバーの指定を位置引数で真偽値以外（`0`・`1` など）として渡す呼び出しが `TypeError` になったことを、New features に新しく追加した指定手段を、Bug fixes にレイアウトエンジンの尊重（constrained の図でカラーバーを追加する描画が `RuntimeError` になる不具合を含む）と subfigure 上での描画の不具合修正を、Deprecations に v4.0.0 で予定する既定値の変更と非推奨にした引数を記載する
2. The ternary-diagram shall 新しく追加した引数と意味が変わった引数の docstring の Parameters の項目（英語・NumPy スタイル）に、受け付ける値、v3.x での既定の挙動、v4.0.0 での変更予定を記載する

### Requirement 9: 後続の spec と共有する検証と使用例の基盤
**Objective:** As a ternary-diagram の開発者（後続の spec の実装者を含む）, I want 真偽値の検証と docstring の使用例の実行を共通の仕組みで行いたい, so that 機能ごとに検証のメッセージや使用例の確かめ方がばらつかず、使用例が古くなったことに気づける

#### Acceptance Criteria
1. The ternary-diagram shall `utils` に、真偽値（`bool` と `numpy.bool_`）だけを受け付けて `bool` を返す公開の検証関数を提供し、それ以外の値（`None`・`0`・`1`・文字列を含む）には引数名と受け取った値を示すメッセージ付きの `TypeError` を送出する
2. The ternary-diagram shall 本機能が `utils` に追加する検証関数（9.1 の関数と、1.6・3.7 で使う「未指定・真・偽」の検証関数）の docstring に、実行して確かめられる使用例（doctest）を持たせる
3. The ternary-diagram shall 公開 API（`TernaryDiagram` とその公開メソッド、`utils` の公開関数、今後追加される公開モジュールの公開関数）の docstring にある doctest 形式の使用例を、一時ディレクトリを作業ディレクトリとし、FutureWarning をエラーとして扱って実行する共通のテストを持つ
4. The ternary-diagram shall private なメソッドの docstring に doctest 形式（`>>>`）の使用例を持たせない
