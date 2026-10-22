# Implementation Plan

- [x] 1. 基盤: 共通の警告の入口、入力検証、doctest ランナー
- [x] 1.1 (P) 利用者向けの警告の共通の入口と、非推奨・既定値変更の文面ヘルパーを作る
  - `warn_external(message, category=FutureWarning)` を、パッケージ全体で利用者向けの警告を出す唯一の入口にする。種類は `category` で選べる（既定は FutureWarning、UserWarning なども可）
  - 警告の発生位置を、呼び出し経路の深さにかかわらず、パッケージ外で最初に見つかる呼び出し元（利用者のコードの行）にする
  - 既定値変更の警告文を「今起きたこと → 変更予定のバージョン（4.0.0）と変更後の挙動 → 今の挙動を保つ書き方 → 新しい挙動を先取りする書き方」の順で組み立てる。構成要素が空なら開発者向けに `ValueError` にする
  - 改名した引数の警告文を、旧名・新名・削除予定のバージョン・書き換え方を同じ順序の形式で組み立てる
  - 改名前後の引数を解決する: 旧名の省略 → 警告なしで新しい値、旧名のみ → FutureWarning を出して旧値、両方 → 「同時に指定できない」旨の `ValueError`、新しい名前のみ → 警告なし
  - 省略を `None` と区別する番兵と、変更予定バージョンの定数を用意する。パッケージ内の他のモジュールは import しない。private なモジュールなので docstring に `>>>` の例を書かない
  - 新規モジュールなので先頭に `from __future__ import annotations` を置き、注釈は組み込みジェネリクス（`type[Warning]` など）と `X | None` で書く（`Any`・`Final` だけ `typing` から import する。tech.md「Compatibility」）
  - 完了時: 単体テストで、警告の発生ファイルがテストファイル・発生行が呼び出し行になること（パッケージ内の関数を 2 段経由しても、`category=UserWarning` でも同じ）、`category` 省略時に FutureWarning になること、文面の構成要素と順序、改名解決の 4 通りが確認でき、すべて通る
  - _Boundary: `src/ternary_diagram/_deprecation.py`（新規、全体）、`tests/test_deprecation.py`（新規、全体）_
  - _Requirements: 5.3, 5.4, 6.6, 6.7, 6.9_

- [x] 1.2 (P) 真偽値の入力検証関数を 2 つ追加する
  - `check_optional_bool(value, name)`: `None` はそのまま、`bool` と `numpy.bool_` は `bool` に揃えて返す。それ以外（`1`、`"yes"` など）は、引数名と受け取った値を示すメッセージ付きの `TypeError` にする
  - `check_bool(value, name)`: `check_optional_bool` の隣に置き、`bool` と `numpy.bool_` だけを受けて `bool` を返す。`None`・`0`／`1`・文字列などは `` `{name}` must be True or False, but got ... `` の `TypeError` にする。本 spec では使わず、`diagram-customization` が `visible`・`endpoints` の検証に使う（`region-plots` の `text(auto_latex_notation=None)` と `heatmaps` の `colorbar` は `None` を受け付けるので `check_optional_bool` を使う）
  - どちらも docstring に doctest 形式の Examples（受け付ける値と `TypeError` になる値）を持たせる。各例は `>>> from ternary_diagram.utils import check_optional_bool`（`check_bool`）の import の行から始め、`numpy.bool_` を渡す例では `>>> import numpy as np` も置いて、その docstring だけで実行できるようにする。図を作らず、ファイルも書き出さない。Parameters の `value`・`name` にはそれぞれ意味を書く文を置く（tech.md「Docstring Examples」）
  - `utils.py` は既存ファイルなので、注釈はファイル内の書き方（`typing.Optional`）に合わせる
  - 完了時: 単体テストで、両関数の受け付ける値と `TypeError` になる値（メッセージに引数名が含まれること）が確認でき、通る
  - _Boundary: `src/ternary_diagram/utils.py: check_optional_bool, check_bool`（追加のみ。既存の関数は変えない）、`tests/test_utils.py: check_optional_bool / check_bool のテスト`（追加のみ）_
  - _Requirements: 1.6, 3.7, 9.1, 9.2_

- [x] 1.3 公開 API の使用例を実行する共通 doctest ランナーを作る
  - 対象を公開 API に限って収集する: `ternary_diagram.__all__` の `TernaryDiagram`（クラスの docstring、`__init__`、名前が `_` で始まらないメソッドとプロパティ）と、公開モジュール（名前が `_` で始まらないサブモジュール。現時点では `utils`、後続の spec が足すものも自動で対象）で定義された公開の関数とクラス。private なモジュールと、`_` で始まるメソッド（`__init__` を除く）は収集しない
  - `>>>` の例を持つ docstring ごとに 1 つのテストにパラメータ化し、作業ディレクトリを一時ディレクトリに移し、FutureWarning をエラーとして扱い、option flags `ELLIPSIS | NORMALIZE_WHITESPACE` で実行する。名前空間はその docstring のモジュールの globals で、名前を足さない。失敗時は失敗した例と差分をメッセージに含める
  - 既存の `TernaryDiagram.__init__` の Examples 節（`user-guide-docs` が書き直す）の 1 件だけを `xfail(strict=True)` にし、理由に「`user-guide-docs` が書き直したら一覧から外す」と書く。Examples 節そのものには手を加えない
  - 完了時: `pytest tests/test_doctests.py` で、`utils` の既存の例と 1.2 の `check_optional_bool`／`check_bool` の例が通り、`__init__` の 1 件が xfail になり、`_BasePlotter._set_default_params`／`_merge_alias` などの private なメソッドと `_deprecation`／`_post_draw` が収集されていないことが確認できる
  - _Depends: 1.2_
  - _Boundary: `tests/test_doctests.py`（新規、全体）_
  - _Requirements: 9.2, 9.3, 9.4_

- [ ] 2. コア: 描画後処理の方針（判定と状態）
- [x] 2.1 図のレイアウト状態を判定する
  - top-level の図でないもの（subfigure）を「対象外」と判定する
  - matplotlib 3.6 以上では、レイアウトエンジンなし、またはライブラリ自身の tight 調整の後に残るプレースホルダーのエンジンを「エンジンなし」、それ以外（constrained・compressed・tight・rcParams 由来）を「エンジンあり」と判定する
  - 3.6 未満では constrained layout と tight layout の有効状態から判定する。バージョンの判定はモジュール冒頭の定数で行う
  - 新規モジュールなので先頭に `from __future__ import annotations` を置き、注釈は組み込みジェネリクスと `X | None` で書く（tech.md「Compatibility」）。古い matplotlib（`FigureBase` の注釈）や Python 3.9（`bool | None`）で注釈が評価されて失敗しないようにする。実行時に評価される型別名は置かない
  - 完了時: 単体テストで、新しい図・`tight_layout()` 実行後の図・各種 `layout=` 指定・rcParams（`figure.autolayout`、`figure.constrained_layout.use`）・subfigure の判定と、バージョン定数を差し替えた 3.6 未満の分岐が確認でき、通る
  - _Boundary: `src/ternary_diagram/_post_draw.py: _HAS_LAYOUT_ENGINE, LayoutState, get_layout_state`（新規ファイルの該当部分）、`tests/test_post_draw.py: get_layout_state のテスト`_
  - _Requirements: 2.1, 2.3, 2.4, 2.5_

- [x] 2.2 レイアウトとカラーバーの決定表と、既定値変更の警告文を実装する
  - レイアウト: 設定（未指定・真・偽）× 図の状態（エンジンなし・あり・対象外）から「何もしない／調整する／調整して警告」を決める。未指定かつエンジンなしだけが「調整して警告」
  - カラーバー: 指定（未指定・真・偽）× 値で色付けした描画か × 既存のカラーバーの有無から「追加しない／追加する／追加して警告」を決める。未指定かつ既存ありだけが「追加して警告」
  - どちらも図を変更しない純粋な関数にし、v4.0.0 では未指定の行だけを変えれば済む形にする
  - レイアウトの警告文は `tight_layout=True` で今の挙動を保つ方法と、`tight_layout=False` と `fig.tight_layout()`／`layout="constrained"` で先取りする方法を示す。カラーバーの警告文は描画メソッド名と `colorbar=True`／`colorbar=False` を示し、`z` には触れない（`` "`{func}` added another colorbar to this diagram, which already has one, because `colorbar` was not specified." ``。`z` を持たない `heatmapf` も同じ文面を使う）。どちらも 1.1 の形式で組み立てる
  - 完了時: 単体テストで両決定表の全 18 セル、警告文に「4.0.0」と保つ方法・先取りする方法が含まれること、`colorbar_warning_message("heatmapf")` に `` `z` `` が含まれないことが確認でき、通る
  - _Boundary: `src/ternary_diagram/_post_draw.py: LayoutAction, ColorbarAction, decide_layout, decide_colorbar, layout_warning_message, colorbar_warning_message, LAYOUT_WARNING_KEY, COLORBAR_WARNING_KEY`、`tests/test_post_draw.py: 決定表と警告文のテスト`_
  - _Requirements: 1.2, 1.3, 1.4, 3.2, 3.3, 3.4, 4.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 2.3 三角図ごとの描画後処理の状態を実装する
  - 作成時に受け取ったレイアウト設定を保持し、作成後は変えられないようにする
  - この三角図を通じて作成したカラーバーを登録し、「削除されていないものが 1 本以上あるか」を答えられるようにする（削除済みは、カラーバーの元のオブジェクトがそのカラーバーを指していないことで判定する）
  - 理由ごとのキーを初めて受け取ったときだけ真を返し、2 回目以降は偽を返す
  - 完了時: 単体テストで、登録後に既存ありと判定され、カラーバーを削除すると既存なしに戻ること、同じキーの 2 回目が偽になることが確認でき、通る
  - _Boundary: `src/ternary_diagram/_post_draw.py: PostDrawContext`、`tests/test_post_draw.py: PostDrawContext のテスト`_
  - _Requirements: 1.1, 4.1, 4.3, 6.8_

- [ ] 3. 統合: TernaryDiagram と Plotter への組み込み
- [ ] 3.1 TernaryDiagram の作成時にレイアウト設定を受け付け、三角図ごとの状態を用意する
  - キーワード専用の `tight_layout`（未指定・真・偽）を `*` の直後に追加する。最終シグネチャは roadmap「横断の取り決め」の `(materials, ax=None, auto_latex_notation=True, *, tight_layout=None, border_kw=None, grid_kw=None, tick_kw=None, axis_label_kw=None, vertex_label_kw=None)` で、本 spec は `tight_layout` だけを足す（`*_kw` は後からマージする `diagram-customization` が `tight_layout` の後ろに足す）
  - 検証の順 `ax` → `materials` → `tight_layout` → `*_kw` に合わせ、`check_ax(ax)` の直後、Axes に触れる前に 1.2 の `check_optional_bool` で `tight_layout` を検証して三角図ごとの状態を作る（`materials` の検証は `diagram-customization` が `check_ax` との間に入れる）。土台の描画コードには手を加えない
  - 手動の `colorbar()` で作ったカラーバーを三角図ごとの状態に登録する。`colorbar()` の引数・既定値・戻り値・docstring は変えない（メソッドの docstring は `user-guide-docs` の担当）
  - docstring は Parameters の `tight_layout` の項目だけを書く: 1 文目に意味（描画のたびに `Figure.tight_layout()` で図の余白を調整するか）を書き、続けて受け付ける値、v3.x の既定の挙動、v4.0.0 の既定（`tight_layout=False`）、レイアウトエンジンがある図と subfigure では調整しないことを書いて、最後の文の後に `, by default None` を添える（`, by default None` だけの項目にしない。tech.md「Docstring Examples」）。Examples 節（`user-guide-docs` の担当）には手を加えない
  - 完了時: `TernaryDiagram(..., tight_layout="yes")` が `TypeError` になり Axes に土台の線が残らないこと、`colorbar()` の後に三角図が「既存のカラーバーあり」になることが確認でき、既存のテストがすべて通る
  - _Boundary: `src/ternary_diagram/_api.py: TernaryDiagram.__init__`（`tight_layout` 引数、その検証と `PostDrawContext` の作成、docstring の `tight_layout` の Parameters の項目のみ）、`TernaryDiagram.colorbar`（作成したカラーバーの登録のみ）_
  - _Requirements: 1.1, 1.6, 4.1, 6.1, 7.4, 8.2_

- [ ] 3.2 描画後処理の共通入口を作り、既存の 4 つの Plotter を移行する
  - Plotter の基底に、三角図ごとの状態を必須のキーワード専用引数として受け取る口と、描画後処理を 1 回で実行する入口を追加する。実行順は「カラーバーの判定と追加・登録 → カラーバーの警告 → レイアウトの判定と調整 → レイアウトの警告」で、警告は決定表が求め、かつ三角図ごとに初めての理由のときだけ 1.1 の `warn_external` で出す。追加したカラーバーを返す
  - 4 つの Plotter はそれぞれ状態を明示的に受けて基底へ渡し（`**kwargs` に紛れ込ませない）、個別の `tight_layout` 呼び出しとカラーバー追加を共通入口の 1 回の呼び出しに置き換える。散布図と等高線の Plotter の `flag_cbar` 引数は `colorbar` に改める。散布図は `z` があるときだけ色付けしたオブジェクトを渡し、等高線は常に渡し、線と注釈は渡さない
  - TernaryDiagram の 4 つの描画メソッドから状態を Plotter に渡す。この段階では `scatter`／`contour` の公開引数は `flag_cbar` のままとし、その値を明示的なカラーバー指定として Plotter に渡す（従来どおり、毎回追加する挙動を保つ）
  - 基底の private なメソッド `_set_default_params`／`_merge_alias` の docstring にある `>>> self...` の行を、`>>>` を使わない本文の説明に書き換える（private なメソッドには doctest の例を書かない）。新しい `_post_draw` の docstring にも `>>>` を書かない
  - matplotlib が出す例外や警告は握りつぶさない
  - 完了時: Plotter から直接 `tight_layout` を呼ぶ箇所がなくなり、`_api.py` の private なメソッドの docstring に `>>>` がなく、`layout="constrained"` の図に描画してもエンジンが変わらず matplotlib のレイアウト変更警告が出ないこと、`layout="constrained"` の図で `contour(z)` が `RuntimeError` にならずエンジンが変わらないこと、subfigure 上の Axes への `scatter(z=...)` がエラーなく完了すること、既定のままエンジンのない図では従来どおり tight 調整されて FutureWarning が三角図ごとに 1 回出ることが確認でき、既存のテストがすべて通る
  - _Depends: 2.1, 2.2, 2.3_
  - _Boundary: `src/ternary_diagram/_api.py: _BasePlotter.__init__`（`post_draw_context` 引数のみ）、`_BasePlotter._post_draw`（新規）、`_BasePlotter._set_default_params / _merge_alias`（docstring の `>>>` 行の書き換えのみ）、`_ScatterPlotter / _ContourPlotter / _LinePlotter / _AnnotatePlotter.__init__`（`post_draw_context` の受け渡し、描画後処理の `_post_draw` への置き換え、`flag_cbar` → `colorbar` の改名のみ）、`TernaryDiagram.scatter / contour / plot / annotate`（Plotter への `post_draw_context` の受け渡しのみ）_
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.4, 2.6, 3.5, 3.6, 6.3, 6.8, 7.1, 7.2, 9.4_

- [ ] 3.3 `scatter`／`contour` に `colorbar` 引数を追加し、`flag_cbar` を非推奨の別名にする
  - `colorbar`（未指定・真・偽）を従来の `flag_cbar` と同じ 6 番目の位置引数として置き、位置引数で書かれた既存の呼び出しを同じ意味で受ける
  - `flag_cbar` はキーワード引数から取り出し、1.1 のヘルパーで解決する。`flag_cbar` が使われた場合は従来どおり真偽で解釈して明示的な指定として扱い（既定値変更の警告の対象にしない）、改名の FutureWarning を出す。`colorbar` と同時に指定されたら `ValueError`
  - `colorbar` は 1.2 の `check_optional_bool` で厳密に検証する。6 番目の位置引数に `0`／`1` を渡していた呼び出しは `TypeError` になる（非互換として受け入れ、4.4 で CHANGELOG の Breaking changes に記載する）
  - docstring は Parameters の `colorbar` と `flag_cbar` の項目だけを書く。どちらも 1 文目に意味を書く文を置く（tech.md「Docstring Examples」）。`colorbar` は「値で色付けした描画にカラーバーを自動で追加するか」から始め、受け付ける値、v3.x の既定の挙動、v4.0.0 の既定（すでにカラーバーがある三角図には自動で追加しない）、「既存のカラーバー」の範囲（この TernaryDiagram を通じて追加し削除されていないもの。matplotlib の関数で直接追加したものは含めない）を書いて、最後の文の後に `, by default None` を添える（`, by default None` だけの項目にしない）。`flag_cbar` は `colorbar` の直後の項目として、`colorbar` の非推奨の別名であることから始め、4.0.0 で削除予定であること、代わりに `colorbar` を使うこと、`colorbar` と同時に指定すると `ValueError` になることを書く。既定値を持たないので `by default` は添えず、省略時は `colorbar` に従うことを文で書く。Notes・Examples などの他の節（`user-guide-docs` の担当）には手を加えない
  - 完了時: `colorbar=False` でカラーバーが増えないこと、`flag_cbar=False` で改名の FutureWarning が出てカラーバーが増えないこと、`flag_cbar` と `colorbar` の同時指定で `ValueError`、`colorbar=1` と 6 番目の位置引数 `1` で `TypeError`、6 番目の位置引数 `False` でカラーバーが増えないことが確認できる
  - _Boundary: `src/ternary_diagram/_api.py: TernaryDiagram.scatter / contour`（`colorbar` 引数、`flag_cbar` の解決、docstring の `colorbar`・`flag_cbar` の Parameters の項目のみ）、`_resolve_colorbar_arg`（新規）_
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.7, 4.2, 4.4, 5.1, 5.2, 5.3, 5.4, 6.2, 6.5, 7.3, 8.2_

- [ ] 4. 検証と変更履歴
- [ ] 4.1 既存のテストを新しい引数へ移行し、FutureWarning が出ない状態にする
  - 共通 fixture の三角図はレイアウト設定（従来と同じ `tight_layout=True`）を明示し、既存テストが同じ処理経路を通りつつ警告を出さないようにする
  - 既存テストの `flag_cbar=False` を `colorbar=False` に置き換え、example の CSV を読むテストもレイアウト設定を明示する
  - 置き換え以外の assert は変えない
  - 完了時: 既存のテスト一式を FutureWarning をエラーとして扱う設定（`-W error::FutureWarning`）で実行しても通る（共通 doctest ランナーの `__init__` の 1 件は xfail のまま）
  - _Boundary: `tests/conftest.py: td fixture`、`tests/test_scatter.py / tests/test_contour.py / tests/test_ternary_diagram.py`（`flag_cbar=False` の置き換えと、example を読むテストのレイアウト設定の明示のみ）_
  - _Requirements: 7.2, 7.4_

- [ ] 4.2 レイアウトの挙動を TernaryDiagram 経由で検証する結合テストを書く
  - `scatter`・`contour`・`plot`・`annotate` でパラメータ化し、既定・エンジンなしでは余白（サブプロットのパラメータ）が変わり FutureWarning が 1 回だけ出ること、2 回目の描画でも調整が続き警告は増えないことを確認する
  - `tight_layout=True` では調整されて警告なし、`tight_layout=False` では余白もエンジンも変わらず警告なしであることを、警告をエラーとして扱う状態で確認する
  - `layout="constrained"` の図ではエンジンが変わらず警告が 1 つも出ないこと、subfigure 上の Axes では `scatter(z=...)` と `plot` がエラーなく完了することを確認する
  - `layout="constrained"` の図で既定のまま `contour(z)` → `scatter(z)` を描き、どちらも例外なく完了すること（現行は 1 回目の `contour(z)` で `RuntimeError`）、エンジンが `ConstrainedLayoutEngine` のままであること、出る警告がカラーバー重複の FutureWarning 1 件だけ（レイアウトの FutureWarning と matplotlib のレイアウト変更警告がない）であることを明示的に確認する
  - FutureWarning の発生ファイルがテストファイルであること、警告文の要点（「4.0.0」と `tight_layout=True`）を `match=` で確認する（全文一致にしない）
  - 完了時: レイアウトの結合テストがすべて通る
  - _Boundary: `tests/test_side_effects.py: レイアウトの結合テスト`（新規ファイルの該当部分）_
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.6, 6.3, 6.4, 6.5, 6.7, 6.8, 7.1_

- [ ] 4.3 カラーバーと `flag_cbar` の挙動を TernaryDiagram 経由で検証する結合テストを書く
  - `contour(z)` だけならカラーバー 1 本・警告なしで、戻り値からそのカラーバーを参照できることを確認する
  - 既定のまま `contour(z)` → `scatter(z)` でカラーバーが 2 本になり FutureWarning が 1 回出ること、3 回目の描画でも警告が増えないこと、`colorbar=True` なら 2 本・警告なし、`colorbar=False` なら増えないことを確認する
  - 手動の `colorbar()` の後は警告が出ること、`fig.colorbar` で直接作ったカラーバーは数えないこと、カラーバーを削除した後は警告が出ないこと、`z` なしの `scatter` は `colorbar=True` でも追加しないことを確認する
  - `flag_cbar=True` を既存カラーバーのある三角図で使うと追加され、警告は改名の 1 件だけであること、不正値の `TypeError`、同時指定の `ValueError`、6 番目の位置引数での指定（`False` で追加しない、`1` で `TypeError`）を確認する
  - 既定のまま（エンジンなし）では、`z` を伴う描画ごとにカラーバーが 1 本増える従来の結果になることを確認する
  - 改名の FutureWarning と重複の FutureWarning の発生ファイルがテストファイル（描画メソッドを呼んだ行）であることを確認する
  - 完了時: カラーバーの結合テストと共通 doctest ランナーを含むテスト一式（`pytest -xs .`）、`ruff check .`、`ruff format --check .` がすべて通る（mypy は CI と開発用 extras に含まれず、開発環境にもないため完了条件にしない）
  - _Boundary: `tests/test_side_effects.py: カラーバーと flag_cbar の結合テスト`（新規ファイルの該当部分）_
  - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4, 6.5, 6.7, 6.8, 7.1, 7.3_

- [ ] 4.4 (P) CHANGELOG の Unreleased の見出しをそろえ、変更点を追記する
  - Unreleased の見出しを Breaking changes / New features / Deprecations / Bug fixes / Other changes（英語、この順）の組にそろえる。今ある Breaking changes / Bug fixes / Other changes とその項目はそのまま残し、New features と Deprecations を足す。後続の spec は該当する見出しに追記する
  - Breaking changes（既存の項目の後に追記）: `scatter`／`contour` の 6 番目の位置引数（旧 `flag_cbar`、新 `colorbar`）に `0`／`1` など真偽値以外を渡すと `TypeError` になったこと。`None`／`True`／`False` を渡すか、キーワードの `flag_cbar`（従来どおり真偽で解釈、非推奨）を使うよう案内する
  - New features: `TernaryDiagram(tight_layout=...)` と `scatter`／`contour` の `colorbar=...`
  - Deprecations: `flag_cbar`（4.0.0 で削除予定、`colorbar` を使う）、v4.0.0 で予定する既定値（`tight_layout=False`、すでにカラーバーがある三角図には自動で追加しない）と、既定のまま結果が変わる呼び出しで FutureWarning が出ること
  - Bug fixes: 設定済みのレイアウトエンジン（constrained など）を置き換えなくなったこと、`layout="constrained"` の図でカラーバーを追加する描画（`contour(z)` など）が `RuntimeError` にならなくなったこと、subfigure 上の Axes で描画が `AttributeError` にならなくなったこと
  - Other changes: 公開 API の docstring の使用例をテストで実行するようになったこと
  - 完了時: CHANGELOG の Unreleased に 5 つの見出しがこの順で並び、本 spec の項目が上記の見出しにあり、既存の項目の書式（英語、箇条書き）に揃っている
  - _Boundary: `CHANGELOG.md: Unreleased の見出しの組と本 spec の項目`（既存の項目と過去のバージョンの節は変えない）_
  - _Requirements: 6.1, 6.2, 7.3, 8.1_

## Implementation Notes

- 検証コマンドは `PYTHONPATH=src` 付きで実行する（パッケージは未インストール）。lint は `ruff check src tests`（`ruff check .` は example ノートブックの既存の F401 で落ちる。範囲外）
- 共通 doctest ランナー（`tests/test_doctests.py`）は公開 API を規則で自動収集する。`TernaryDiagram` に公開メソッドを足すとその Examples も実行されるので、例は import の行から始め、FutureWarning を出さない書き方にする。private なメソッドに `>>>` を書いても収集はされないが、tech.md に従って書かない
