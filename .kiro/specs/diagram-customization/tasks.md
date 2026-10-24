# Implementation Plan

- [x] 1. 現行の土台の見た目を特性テストで固定する
  - 着手の前提として、`plot-side-effects` がマージ済みのブランチから始める（roadmap の Implementation Order）。`utils.check_bool`、`tight_layout=True` で作る `td` fixture、共通 doctest ランナー `tests/test_doctests.py`、CHANGELOG の `Unreleased` の見出しの組がそろっていることを確かめる
  - リファクタの前に、何も指定せずに作った三角図の土台を、v3 の描画式から計算した期待値と比べるテストを追加する
  - 線 30 本について、外枠 3 本とグリッド 27 本の線分（向きを区別しない端点の組）、色・線幅・線種・重なり順の値を比べる
  - 文字 30 個について、文字列・位置・回転・文字揃え・フォントサイズ・重なり順の値の組の集合を比べ、軸タイトルがないことを確かめる
  - 部品間の追加順（グリッドの線はすべて外枠より前、頂点ラベルはすべて目盛りラベルより前）、描画後の表示範囲、作成直後に色のサイクルが進んでいないことも確かめる
  - 期待値の計算はテスト用の補助モジュールに置き、後続の部品・集約の単体テストからも同じ期待値を使えるようにする
  - 現行の実装のままで、新しい特性テストと既存のテストがすべて通る
  - _Boundary: `tests/_skeleton_expected.py`（新規: v3 の既定の土台の期待値）, `tests/test_ternary_diagram.py`（既定の土台の特性テストの追加だけ）_
  - _Requirements: 1.1, 1.2_

- [ ] 2. 配置の計算と部品の共通手順を用意する
- [x] 2.1 目盛り・グリッドの値の列と目盛りの書式を作る純粋関数を追加する
  - 間隔の倍数を 0 と 1 を除いて昇順に並べ、小数 12 桁に丸めた値の列を返し、両端（0 と 1）を加える指定も受け付ける
  - 間隔が実数でない（真偽値を含む）ときは種類のエラー、有限でない・0 以下・1 より大きいときは許される範囲を示すエラーにする
  - 書式は「パーセント」（既定、不要な桁を付けない百分率）、「割合」、%-style を先に試して失敗したら {}-style を使う書式文字列、値を受け取る関数を受け付け、それ以外や試しの値で整形できない文字列はエラーにする
  - 各関数の docstring（英語、NumPy スタイル）に、docstring ごとに使う名前を import する行（`>>> from ternary_diagram.utils import get_tick_values` など）から始め、図を作らずに関数を呼ぶ doctest 形式の Examples を、numpy の版で表記が変わらない出力で書く。Parameters の各項目には意味を書く文を置き、既定値は文の後に `, by default X` と添える（design の「Docstring Examples」「Docstring Parameters」）。独自の doctest ランナーは作らず、共通ランナー `tests/test_doctests.py` で通ることを確かめる
  - 間隔 0.1 で 9 個、0.05 で 19 個の値が得られ、既定の書式の文字列が v3 の「10」〜「90」と一致し、不正な間隔と書式がエラーになる単体テストが通り、共通ランナーでこれらの関数の Examples が通る
  - _Boundary: `src/ternary_diagram/utils.py: TickFormat, get_tick_values, get_tick_formatter`, `tests/test_utils.py`（上記 2 関数のテストの追加だけ）_
  - _Requirements: 5.1, 6.2, 6.3, 6.4, 6.5, 6.6, 10.1, 10.3, 10.4, 11.1, 11.3, 12.4_

- [ ] 2.2 辺上の点・グリッド線の両端・軸タイトルの位置を計算する純粋関数を追加する
  - 成分 k の目盛りが成分 (k+1) mod 3 が 0 になる辺に付くという規約で、値に対応する辺上の点を既存の座標変換だけで計算する
  - 等組成線の両端（2 つの辺上の点）と、軸タイトルの位置（辺の中点から外向きの法線方向へ距離だけ離した点）と回転（右辺 300°、左辺 60°、底辺 0°）を計算する
  - 成分の番号が 0〜2 でないとき、距離が有限の実数でないときはエラーにする
  - 各関数の docstring に、docstring ごとに使う名前を import する行（`>>> from ternary_diagram.utils import get_edge_points` など）から始め、図を作らずに関数を呼ぶ doctest 形式の Examples を書く（実行は共通ランナー）。Parameters の各項目は意味を書く文で書く（既定値を持つ引数はないので `, by default` は付けない）
  - 各成分の点が規約どおりの辺上にあり、軸タイトルの位置が法線方向へ指定の距離だけ離れ、回転が 300 / 60 / 0 になる単体テストが通り、共通ランナーでこれらの関数の Examples が通る
  - _Boundary: `src/ternary_diagram/utils.py: get_edge_points, get_grid_segments, get_axis_label_position`, `tests/test_utils.py`（上記 3 関数のテストの追加だけ）_
  - _Requirements: 6.1, 7.1, 7.4, 10.3, 11.1, 11.3, 12.4_

- [ ] 2.3 (P) 部品の共通の更新手順を作る
  - 新規モジュールなので `from __future__ import annotations` を付け、注釈は組み込みジェネリクスと `X | None` で書く。実行時に評価される型別名（`Spec`）だけは `typing.Union` で書く
  - 線と文字の図形の仕様を値として表し、部品の設定を名前付きの項目と matplotlib のプロパティに分けて保持する
  - 名前付きの項目は未指定（None）なら直前の値を引き継ぎ、プロパティは別名を正式名にそろえてから既定値・直前の値・今回の指定の順に統合する。Artist クラスを渡す別名統合が使えない matplotlib では別名の辞書で代替する
  - 表示の有無は統合した後の値を `utils.check_bool(visible, "visible")` で検証し（独自の判定は書かない）、非表示なら図形を描かない
  - 検証と仕様の計算を先に行い、図形の生成中に失敗したら作りかけの図形を取り除いて元の例外を送出し、成功したときだけ古い図形を取り除いて設定と図形を確定する
  - 取り出せる図形は新しいリストで返し、線の部品は同じ図形のまま Axes の末尾へ積み直せるようにする
  - テスト用の最小の部品で、未指定の項目の引き継ぎ、非表示で図形が空になること、表示の有無に真偽値以外を渡すとエラーになること、失敗時に図形（同一オブジェクト）と設定が変わらないこと、積み直しで末尾へ移ることを確かめる単体テストが通る
  - _Boundary: `src/ternary_diagram/_skeleton.py: _LineSpec, _TextSpec, Spec, _SkeletonPart`（新規モジュールの作成）, `tests/test_skeleton_parts.py`（新規: `_SkeletonPart` の単体テスト）_
  - _Requirements: 2.3, 2.4, 2.5, 2.6, 2.7, 3.3, 3.4, 9.3, 10.3, 10.7, 10.8_

- [ ] 3. 土台の 5 つの部品と集約を作る
- [ ] 3.1 外枠とグリッドの部品を作る
  - 外枠は黒・線幅 2・実線の 3 本（底辺・左辺・右辺の順）を、グリッドは灰色・線幅 0.5 の等組成線を成分ごとに描き、どちらも構築時に受け取った重なり順の値を既定にする
  - グリッドの間隔は値の列の関数で、線の両端は等組成線の関数で決め、目盛りラベルの間隔とは独立に持つ
  - 既定の設定で作った線分とスタイルが特性テストの期待値と一致し、間隔 0.05 でグリッドが 57 本になり、非表示で線がなくなる単体テストが通る
  - _Boundary: `src/ternary_diagram/_skeleton.py: _Border, _Grid` と外枠・グリッドの `DEFAULT_*` 定数, `tests/test_skeleton_parts.py`（`_Border` / `_Grid` のテストの追加だけ）_
  - _Requirements: 1.1, 4.1, 4.2, 5.1, 5.2, 5.3, 5.4, 9.1, 11.2_

- [ ] 3.2 目盛りラベルの部品を作る
  - 値ごとに成分 0, 1, 2 の順で、辺上の点に辺ごとのずらし量を足した位置へ、辺ごとの文字揃えと回転の上に利用者のプロパティを重ねて描く
  - 間隔・書式・両端の表示・フォントサイズなどを受け付け、両端の表示の有無は `utils.check_bool(endpoints, "endpoints")` で検証する。書式の関数が例外を出したときは共通手順の巻き戻しに任せる
  - 既定で 27 個の文字列・位置・回転・文字揃えが特性テストの期待値と一致し、両端の表示で各辺 11 個（計 33 個）、割合の書式で「0.1」になる単体テストが通る
  - _Boundary: `src/ternary_diagram/_skeleton.py: _TickLabels` と目盛りラベルの `DEFAULT_*` 定数, `tests/test_skeleton_parts.py`（`_TickLabels` のテストの追加だけ）_
  - _Requirements: 1.1, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 9.1, 10.3, 11.2_

- [ ] 3.3 軸タイトルの部品を作る
  - 3 つの成分の軸タイトルを、なし（None または空文字）を除いて、軸タイトルの位置の関数が返す位置と回転で描き、文字列は化学式に整形しない
  - 既定はタイトルなし、辺からの距離 0.15、フォントサイズ 12、中央揃えとし、既定の距離を example の図で目視確認する
  - タイトルの個数が 3 でないとき、要素が文字列でもなしでもないときはエラーにする
  - 3 つ指定で 3 個、1 つだけ指定で 1 個描かれ、位置と回転が関数の結果と一致し、「Li2O / mol%」がそのまま表示される単体テストが通る
  - _Boundary: `src/ternary_diagram/_skeleton.py: _AxisLabels` と軸タイトルの `DEFAULT_*` 定数, `tests/test_skeleton_parts.py`（`_AxisLabels` のテストの追加だけ）_
  - _Requirements: 1.2, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 9.1, 10.2, 10.3, 11.2_

- [ ] 3.4 頂点ラベルの部品を作る
  - 化学式の自動整形の有無を構築時に固定し、ラベルを上・左下・右下の頂点に、頂点ごとの文字揃えとずらし量（既定は上 (0, 0.02)、左下と右下 (0, -0.05)）で描く
  - ラベルを変えたときも同じ自動整形の設定を適用し、自動整形が有効でラベルが文字列でないときは現行と同じエラーにする
  - ラベルやずらし量が 3 つでないとき、ずらし量が有限の実数の組にならないときはエラーにする
  - 既定の位置・文字揃え・フォントサイズが特性テストの期待値と一致し、ラベルの変更で「Li$_{2}$O」に整形され（自動整形が無効なら整形されず）、ずらし量で位置が変わる単体テストが通る
  - _Boundary: `src/ternary_diagram/_skeleton.py: _VertexLabels` と頂点ラベルの `DEFAULT_*` 定数, `tests/test_skeleton_parts.py`（`_VertexLabels` のテストの追加だけ）_
  - _Requirements: 1.1, 1.4, 8.1, 8.2, 8.3, 8.4, 9.1, 10.2, 10.3, 11.2_

- [ ] 3.5 部品を束ねる集約を作る
  - 構築時に三角形の 3 頂点を Axes のデータ範囲へ登録して自動スケールを要求し、グリッド → 外枠 → 頂点ラベル → 目盛りラベル → 軸タイトルの順に、それぞれの初期指定で 1 回ずつ描く
  - 途中の部品の構築が失敗したら、先に描いた部品の図形を取り除いてから例外を送出する
  - 部品の名前（design の「`*_kw` と `set_*` の対応」の `PartName`）で更新と図形の取り出しを行い、グリッドを更新したら外枠を積み直す。図のレイアウトは変更しない
  - 既定で構築した図形の数・部品間の順がタスク 1 の共通の期待値と一致し、グリッド更新後に外枠が線の末尾にあり、外枠とグリッドを非表示で構築しても描画後の表示範囲が既定と同じになり、途中の部品の失敗で先に描いた図形が残らない単体テストが通る
  - _Boundary: `src/ternary_diagram/_skeleton.py: _Skeleton, PartName`, `tests/test_skeleton_parts.py`（`_Skeleton` のテストの追加だけ）_
  - _Requirements: 1.1, 1.2, 2.1, 2.8, 9.2, 9.4, 10.8_

- [ ] 4. 三角図の公開 API へ統合する
- [ ] 4.1 作成時の部品ごとの指定を受け付け、土台の描画を集約へ委譲する
  - `__init__` のシグネチャを roadmap の最終形 `(materials, ax=None, auto_latex_notation=True, *, tight_layout=None, border_kw=None, grid_kw=None, tick_kw=None, axis_label_kw=None, vertex_label_kw=None)` に一致させる。`plot-side-effects` が足した `tight_layout` の後ろに 5 つの部品ごとの指定を足し、キーワード専用マーカーは 1 つだけにする。それぞれを作成後の変更と同じ意味で集約へ渡す
  - 検証は Axes の設定や土台の描画より前に、`ax` → `materials` → `tight_layout` → 部品ごとの指定の順で行う。`materials` の検証は `check_ax` と `tight_layout` の検証の間に入れ（3 要素未満なら 3 つ必要であることを示すエラー。4 要素以上は先頭 3 要素を使う現行の挙動を保つ）、部品ごとの指定の検証（項目名と値の対応でなければ種類のエラー、頂点ラベルの指定にラベルの文字列があれば materials と衝突することを示すエラー）は `tight_layout` の検証の後に入れる。`tight_layout` の検証と扱いには手を入れない
  - 描画メソッド（Plotter）のコードには手を入れない
  - 既存のテストと特性テストが変更なしで通り、作成時の検証エラーのテストと、複数の不正な引数を同時に渡したときに上の順で最初のエラーが出るテストが通る
  - _Boundary: `src/ternary_diagram/_api.py: TernaryDiagram.__init__`（シグネチャへの 5 引数の追加、`materials` と `*_kw` の検証、土台の描画を `_Skeleton` の構築へ置き換え。`tight_layout` の検証と `PostDrawContext` の作成は変更しない）, `tests/test_ternary_diagram.py`（`__init__` の検証と検証の順のテストの追加だけ）_
  - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.2, 10.3, 10.5, 10.6_

- [ ] 4.2 作成後の変更メソッドと図形の取り出し口を追加する
  - 5 つの部品それぞれに、名前付きの項目（未指定は直前の設定を引き継ぐ）と matplotlib のプロパティを受け付ける変更メソッドを追加し、新しく描いた図形のリストを返す
  - 部品ごとに現在の図形を新しいリストで返す読み取り専用の取り出し口を追加し、代入には読み取り専用であることを示すエラーを出す
  - 各変更メソッドの戻り値と取り出し口が同じ図形を指し、描き直し後は古い図形が取り出し口と Axes の両方から消え、取り出し口への代入がエラーになるテストが通る
  - _Boundary: `src/ternary_diagram/_api.py: TernaryDiagram.set_border, set_grid, set_ticks, set_axis_labels, set_vertex_labels` と `border_lines_, grid_lines_, tick_labels_, axis_labels_, vertex_labels_` プロパティ, `tests/test_skeleton.py`（新規: 戻り値と取り出し口のテスト）_
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.4, 3.5_

- [ ] 4.3 公開 API の docstring を仕上げ、変更履歴に記載する
  - `__init__` の docstring には、`tight_layout` の項目の後ろに 5 つの部品ごとの指定の Parameters の項目だけを英語の NumPy スタイルで足す。各項目は、どの部品の設定か、作成直後に対応する変更メソッドを呼ぶのと同じであること、受け付ける項目は対応する変更メソッドを参照すること、None なら既定の見た目であることを書いた文の後に `, by default None` を添える（`, by default None` だけの項目にしない。design の「Docstring Parameters」）。Examples 節は `user-guide-docs` が持つので変更しない
  - 5 つの変更メソッドの Parameters は、名前付きの項目ごとに意味・受け付ける値・None なら直前の設定を引き継ぐこと・作成時の初期値を書いた文の後に `, by default None` を添え、matplotlib のプロパティ（`**kwargs`）には全図形に適用され直前の値を引き継ぐことを書く（`, by default` は付けない）
  - 5 つの変更メソッドと取り出し口の docstring に、意味・戻り値と、tech.md の「Docstring Examples」に従う Examples を書く。Examples は docstring ごとに `>>> import matplotlib.pyplot as plt` と `>>> from ternary_diagram import TernaryDiagram` の行から始めてその docstring だけで実行できるようにし（`_api.py` は `plt` を import していない）、`fig, ax = plt.subplots(layout="constrained")` と `ax=ax` で三角図を作ってから、変更メソッドの呼び出しと、対応する作成時の指定（`border_kw` → `set_border`、`grid_kw` → `set_grid`、`tick_kw` → `set_ticks`、`axis_label_kw` → `set_axis_labels`、`vertex_label_kw` → `set_vertex_labels`）で同じ結果になる例を示し、作成時の指定がその変更メソッドの呼び出しと同じ意味であることを本文に書く。ファイルは書き出さず、artist の repr は出力しない
  - クラスの docstring の Notes と目盛りの変更メソッドの docstring に、どの辺の目盛りがどの成分を表し値がどちら向きに増えるか、未指定の項目を引き継ぐこと、両端の目盛りが左下の頂点で近接しうること、同じ重なり順の値を持つ利用者の図形との前後関係を書く
  - CHANGELOG の `Unreleased` の既存の見出しの組を使い、New features に追加した作成時の引数・変更メソッド・取り出し口・`utils` の配置の関数を、Bug fixes に materials が足りないときのエラーが IndexError から ValueError に変わったことを書く。見出しは新しく作らない
  - 共通ランナー `tests/test_doctests.py` が FutureWarning をエラーにした状態で通り、`pytest tests/test_doctests.py -v` の出力に 5 つの変更メソッドの Examples が含まれ、ruff の lint と format の確認を通り、CHANGELOG の New features と Bug fixes に該当項目がある
  - _Boundary: `src/ternary_diagram/_api.py: TernaryDiagram` のクラスの docstring（Notes）、`TernaryDiagram.__init__` の docstring（5 つの `*_kw` の Parameters の項目だけ）、`set_*` 5 メソッドと取り出し口 5 つの docstring, `CHANGELOG.md`（`Unreleased` の New features と Bug fixes への追記だけ）_
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ] 5. 公開 API を通した検証と回帰確認
- [ ] 5.1 部品ごとの変更を公開 API 経由で検証するテストを追加する
  - 5 つの部品それぞれについて、作成時の指定と作成後の変更で同じ図形の集合になることを、design の「`*_kw` と `set_*` の対応」に沿ってパラメータ化して確かめる
  - 未指定の項目の引き継ぎ（間隔を変えた後に色だけ変える、非表示から表示に戻す）、外枠の線種・線幅、目盛り・軸タイトル・頂点ラベルのフォントサイズが全図形に効くことを確かめる
  - 注釈付きの散布図と利用者が直接描いた線の後に全部品を変更しても、それらの図形が残りプロパティも変わらないことを確かめる。散布図などの描画メソッドを呼ぶテストは `td` fixture で三角図を作るか `tight_layout=True` を明示し、FutureWarning をエラーにしても通るようにする
  - 5 つの部品それぞれで非表示にすると取り出し口が空になり、Axes から図形が消えることを確かめる
  - 追加したテストがすべて通る
  - _Boundary: `tests/test_skeleton.py`（部品ごとの変更の統合テストの追加だけ。ソースは変更しない）_
  - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6, 2.7, 3.3, 4.1, 4.2, 5.2, 5.3, 6.7, 6.8, 7.5, 7.6, 8.2, 8.4_

- [ ] 5.2 重なり順・表示範囲・レイアウト・エラー時の巻き戻しを検証するテストを追加する
  - 描き直した後も線の重なり順の値が 1、文字が 3 のままで、利用者が指定した重なり順の値が優先されることを確かめる
  - 外枠とグリッドを非表示にして作成しても描画後の表示範囲が既定と同じで、全部品の変更の前後で Axes の位置が変わらないことを確かめる
  - 不正な間隔、解釈できない書式、未知のプロパティ、例外を出す書式の関数のそれぞれで例外が出て、取り出し口の図形（同一オブジェクト）と Axes の図形の数が呼び出し前と同じであること、作成時の不正な指定では土台の図形が Axes に残らないことを確かめる
  - 描画メソッドを呼ぶ場合は `td` fixture か `tight_layout=True` を使う
  - 追加したテストがすべて通る
  - _Boundary: `tests/test_skeleton.py`（重なり順・表示範囲・レイアウト・巻き戻しのテストの追加だけ。ソースは変更しない）_
  - _Requirements: 2.8, 9.1, 9.2, 9.3, 9.4, 10.1, 10.4, 10.7, 10.8_

- [ ] 5.3 全体の回帰確認を行う
  - テスト全体（共通ランナー `tests/test_doctests.py` を含み、FutureWarning をエラーにする設定のまま）、ruff の lint と format の確認、mypy を実行する。ruff や mypy が環境にない場合は、勝手にインストールせず承認を得るか、確認できなかったことを報告する
  - 既定の図を変更前と変更後で画像に保存して見比べ、見た目の差がないことを手元で確認する（テストスイートには画像比較を入れない。画像はリポジトリの外に書き出す）
  - テスト全体が通り、ruff と mypy が新しい警告やエラーを出さない
  - _Boundary: 確認のみ（リポジトリのファイルを変更しない。失敗したら原因のタスクの Boundary の中で直す）_
  - _Requirements: 1.1, 1.3, 12.4_

## Implementation Notes

- 検証コマンドは `PYTHONPATH=src` 付きで実行する（パッケージは未インストール）。lint は `ruff check src tests`（`ruff check .` は example ノートブックの既存の F401 で落ちる。範囲外）。テスト一式は `-W error::FutureWarning` でも通る状態を保つ
- 既定の土台の期待値は `tests/_skeleton_expected.py`（v3 の描画式から独立に計算。`LineKey` / `TextKey`、`line_key` / `text_key`、`expected_*`、`expected_view_limits`）。部品と集約の単体テスト（3.x）はこれを使い回す。`TextKey` には文字の色も含めた（1 のレビューでの提案）
- `_skeleton_expected` は pytest 既定の prepend import モードで `from _skeleton_expected import ...` として読み込む（`tests/__init__.py` はない）
- グリッド内・目盛りラベル内の描画順は固定していない（design の `_Grid` は成分ごとの順で描き、v3 の順と違うため）。部品間の順（グリッド → 外枠、頂点ラベル → 目盛りラベル）は固定している
