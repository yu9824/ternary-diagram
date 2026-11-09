# Implementation Plan

- [x] 1. 基盤: fill と text の既定の重なり順を定数で固定する
  - 着手条件: roadmap の実装順どおり、plot-side-effects・diagram-customization・annotate-plain-text がこの順にマージ済みである。heatmaps は本 spec の前でも後でもよいが、同時には入れない（1 つずつマージする）。条件を満たさなければ着手しない
  - 既存の zorder 定数の直後に（heatmaps が先にマージされていれば、ヒートマップ用の定数の後ろに）、塗りつぶし用（等高線図とグリッドの間）と文字用（散布図より手前）の 2 つの定数をまとめて追加する。既存の定数の値・名前・並びは変えない
  - 定数どうしの大小関係（等高線図 < 塗りつぶし < グリッド < 線 < 散布図 < 文字）と、文字用の値が matplotlib の文字の既定の重なり順（3）より大きいことを確かめるテストを、fill のテストファイルの最初のテストとして書く
  - 既存の 4 つの定数が 0・1・2・3 のままであることも同じテストで確かめる
  - heatmaps が先にマージされていてヒートマップ用の定数があれば、ヒートマップ < 塗りつぶし（-1 < 0.5）も同じテストで確かめる。定数がなければこの確認だけ理由付きでスキップする（heatmaps が後からマージされる場合は heatmaps 側が確かめる）
  - 完了時: 定数の関係と既存の値を確かめるテストが通り、既存のテスト一式も変更なしで通る
  - _Requirements: 4.1, 4.2, 4.3, 4.6_
  - _Boundary: src/ternary_diagram/_api.py: DEFAULT_ZORDER_FILL, DEFAULT_ZORDER_TEXT; tests/test_fill.py: zorder constants test_

- [x] 2. コア: 組成で指定した多角形を塗る `fill` を Plotter パターンで実装し、単体テストで振る舞いを固定する
  - 着手条件: 1 と同じ（plot-side-effects により、Plotter の基底が三角図ごとの状態を必須のキーワード専用引数で受け取り、描画後処理の入口を持ち、TernaryDiagram がその状態を保持し、共通 fixture の三角図がレイアウト設定を明示し、共通 doctest ランナーがある）
  - 頂点の並びを既存の検証と正規化に通し、頂点が 3 個未満なら、必要な個数と実際の個数を示す `ValueError` を描画の前に送出する
  - 既定値として重なり順だけを入れ（利用者の指定を優先）、色・線・透明度は matplotlib に任せる。追加のキーワード引数をそのまま matplotlib の塗りつぶし関数へ渡し、その戻り値（1 要素のリスト）を返す
  - 描画後処理の入口を、値で色付けしたオブジェクトを渡さずに、初期化の最後でちょうど 1 回呼ぶ。レイアウト調整やカラーバーの追加を直接呼ばない
  - TernaryDiagram に公開メソッドを追加し、三角図ごとの状態を Plotter に渡し、成功したときだけ `fill` の名前で座標を記録する
  - docstring（英語・NumPy スタイル）に、引数、頂点の順序と自動で閉じること（凸包は計算しない）、既定の重なり順・色の順番とその変え方（`zorder`、`alpha`）、戻り値が 1 要素のリストであること、matplotlib の `fill` の URL を書く
  - 使用例は steering の tech.md「Docstring Examples」に従い、doctest 形式で `>>> import matplotlib.pyplot as plt` と `>>> from ternary_diagram import TernaryDiagram` の 2 行から始め（ランナーの名前空間は `_api.py` の globals で、`plt` がないため）、`fig, ax = plt.subplots(layout="constrained")` と `TernaryDiagram(..., ax=ax)` で三相域を半透明で塗り凡例を出す。`savefig` は書かず、FutureWarning を出さない書き方にする。Parameters の各項目には意味を書く文を置く。ランナーは作らない
  - 完了時: fill のテストファイルで、3 頂点の座標と閉じた多角形、比率のままの入力、渡した順序の保持、ラベルの凡例表示、色の順番、既定の重なり順と上書き、kwargs の反映、座標の記録、形の誤りと頂点不足の `ValueError`、失敗時に Axes の多角形と座標の記録が増えないことが確認でき、すべて通る。共通 doctest ランナー（`tests/test_doctests.py`）で `fill` の使用例が通る
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.5, 5.1, 5.3, 6.1, 6.2, 6.4, 7.1, 7.2, 8.1, 8.3_
  - _Boundary: src/ternary_diagram/_api.py: TernaryDiagram.fill, _FillPlotter（と `import matplotlib.patches`（戻り値と `collection_` の型注釈）、`ternary_diagram._post_draw` の `PostDrawContext`（`_FillPlotter.__init__` の型注釈。plot-side-effects が import 済みなら足さない）の import の追加）; tests/test_fill.py_

- [x] 3. コア: 組成点への文字の配置
  - _Boundary: src/ternary_diagram/_api.py: TernaryDiagram.__init__ (`self.__auto_latex_notation` line only, if annotate-plain-text has not added it), TernaryDiagram.text, _TextPlotter, _TEXT_ALIGNMENT_DEFAULTS（と `check_optional_bool`・整形の入口の import の追加（未 import の場合のみ））; tests/test_text.py_

- [x] 3.1 `text` の配置を Plotter パターンで実装し、単体テストで振る舞いを固定する
  - 2 と同じモジュールの TernaryDiagram と Plotter の並びに追加するので、2 と並行しない
  - 1 点の組成を既存の 1 点用の検証に通し（3 成分でなければ `ValueError`）、正規化した位置に文字を 1 つ置き、matplotlib の文字オブジェクトを返す
  - 水平・垂直の配置は、正式名と別名（`ha` / `va`）のどちらもキーワード引数と `fontdict` に指定されていないときだけ中央にする。重なり順の既定値も入れ、文字の大きさは入れない。追加のキーワード引数は matplotlib にそのまま渡す
  - 描画後処理の入口を、値で色付けしたオブジェクトを渡さずに、初期化の最後でちょうど 1 回呼ぶ。TernaryDiagram に公開メソッドを追加し、成功したときだけ `text` の名前で座標を記録する
  - この段階では文字列をそのまま表示し、化学式の整形は 3.2 で足す。3.2 の後も結果が変わらないよう、このタスクのテストでは数字を含まない文字列を使う
  - docstring に、引数、既定の配置と重なり順とその変え方、戻り値、matplotlib の `text` の URL を書く。使用例は tech.md「Docstring Examples」の形式（`>>> import matplotlib.pyplot as plt` と `>>> from ternary_diagram import TernaryDiagram` の 2 行から始め、`plt.subplots(layout="constrained")` と `ax=ax` で図を渡し、`savefig` なし）で領域の中心に相の名前を置く。Parameters の各項目には意味を書く文を置く。表示する文字列の出力は 3.2 で整形の例と一緒に示す
  - 完了時: text のテストファイルで、`(3,)`・`(1, 3)`・比率のままの組成での位置、既定の中央揃え、`ha`・`horizontalalignment`・`va`・`fontdict` による上書き、既定の重なり順と上書き、kwargs の反映、座標の記録、成分数の誤りの `ValueError` と失敗時に Axes の文字と座標の記録が増えないことが確認でき、すべて通る。共通 doctest ランナーで `text` の使用例が通る
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 4.5, 5.1, 5.2, 5.3, 6.3, 6.4, 7.1, 7.2, 8.1, 8.3_
  - _Boundary: src/ternary_diagram/_api.py: TernaryDiagram.text, _TextPlotter, _TEXT_ALIGNMENT_DEFAULTS; tests/test_text.py_

- [x] 3.2 `text` に化学式の整形の切り替えと、三角図単位の設定の引き継ぎを足す
  - 着手条件: annotate-plain-text がマージ済みであることを確かめ、`annotate` が使っている整形の入口、`annotate` に整形の切り替え引数があればその名前、annotate-plain-text が `TernaryDiagram.__init__` に三角図単位の設定の private な bool 属性 `__auto_latex_notation` の 1 行を足しているか、`annotate` が互換のための警告の経路を持つかを確認する。切り替え引数の名前が違えば `text` の引数名をそろえる。互換の警告の経路があれば `text` はそれを通らずに規則の最終形を使い、design の想定と合わなければ着手前に要件 3.2 を見直す
  - roadmap「横断の取り決め」に従い、三角図単位の設定は private な bool 属性 `TernaryDiagram.__auto_latex_notation` から読む。annotate-plain-text がすでに足していれば何も足さずにそれを使い、まだなければ初期化の本体に `self.__auto_latex_notation = bool(auto_latex_notation)` を 1 行だけ足す（最初に必要になった側が足す）。別名の属性は作らない。シグネチャ・検証・土台の構築は変えない
  - キーワード専用の切り替え引数（既定は `None`）を公開メソッドに足し、Plotter を作る前に plot-side-effects の `None` を受け付ける真偽値の検証関数（`check_optional_bool`）に通す。`None`・真偽値以外は、受け付けられる値と受け取った値を示す `TypeError` になり、何も描かない
  - `None` なら三角図単位の設定を、`True` / `False` ならその値を使い、解決した真偽値だけを Plotter に渡す。三角図単位の設定は書き換えない。Plotter には独自の型検査を置かない
  - 整形する設定で文字列が渡されたときだけ `annotate` と同じ入口で整形し、文字列以外や整形しない設定ではそのまま matplotlib に渡す。例外を握りつぶして分岐しない
  - docstring に、切り替え引数の意味と既定値（`None` は三角図作成時の設定を引き継ぐ）、`True` / `False` はその呼び出しの文字列だけに効き三角図単位の設定・頂点ラベル・他の呼び出しに影響しないこと、`annotate` と同じ規則で整形すること、数式などを含む文字列では整形を切れることを書く。使用例は tech.md「Docstring Examples」の形式で 2 つのブロックに分け、どちらも `>>> import matplotlib.pyplot as plt` と `>>> from ternary_diagram import TernaryDiagram` の 2 行から始める。1 つ目で既定の整形（化学式の出力を示す）と `auto_latex_notation=False` の呼び出し、2 つ目で三角図単位で整形しない設定と `auto_latex_notation=True` の呼び出しを示す。整形する設定での普通の名前の出力は示さない
  - 完了時: text のテストファイルで、既定の三角図での化学式の整形、整形しない設定でのそのままの表示と、その後の指定なしの呼び出しが整形されること、三角図単位で整形しない設定での指定なし・`None` の明示・`True` の上書き、`numpy.bool_` の受け付け、複数の文字列（化学式・数字を含む普通の文字列・数字を含まない文字列）で整形する設定の `annotate` と表示が一致すること、文字列以外の表示、不正値（`1`・`0`・`"yes"`）の `TypeError` と失敗時に Axes の文字と座標の記録が増えないことが確認でき、すべて通る。共通 doctest ランナーで `text` の使用例が FutureWarning なしで通る
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 6.4, 8.1, 8.3_
  - _Boundary: src/ternary_diagram/_api.py: TernaryDiagram.__init__ (`self.__auto_latex_notation` line only, if annotate-plain-text has not added it), TernaryDiagram.text, _TextPlotter（と `check_optional_bool`・整形の入口の import の追加（未 import の場合のみ））; tests/test_text.py_

- [x] 4. 統合と検証
  - _Boundary: tests/test_fill.py, tests/test_text.py, CHANGELOG.md: New features entries for fill/text_

- [x] 4.1 既存の描画と並べたときの重なり順を検証する結合テストを書く
  - 等高線図（カラーバーなし）・タイライン・散布図・注釈・土台の線と、`fill`・`text` を同じ三角図に描き、各 artist の重なり順が「等高線図 < fill < 土台の線 < タイライン < 散布図・注釈 < text」になることを確かめる
  - 描画の順序を逆にしても同じ関係になることを確かめる
  - diagram-customization の `set_grid`（マージ済み）で土台を描き直した後の線とも、同じ関係になることを確かめる
  - 完了時: fill と text のテストファイルの重なり順の結合テストがすべて通る
  - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - _Boundary: tests/test_fill.py, tests/test_text.py: zorder integration tests_

- [x] 4.2 描画後処理との整合を TernaryDiagram 経由で検証する結合テストを書く
  - `fill` と `text` のそれぞれで、描画の前後で図の Axes の数が変わらない（カラーバーが増えない）ことを確かめる
  - `tight_layout=False` で作った三角図では描画の前後で図の余白のパラメータが変わらず、`tight_layout=True` では変わることを確かめる
  - レイアウト設定を指定しない三角図をレイアウトエンジンのない図に作り、`fill` → `text` と続けて描くとレイアウトの FutureWarning が全体で 1 回だけ出ること、`text` だけを描いた別の三角図でも 1 回出ることを、警告文の要点だけを照合して確かめる
  - 完了時: 描画後処理の結合テストがすべて通る
  - _Requirements: 7.1, 7.2, 7.3_
  - _Boundary: tests/test_fill.py, tests/test_text.py: post-draw integration tests_

- [x] 4.3 (P) CHANGELOG の Unreleased に `fill` と `text` を追記する
  - plot-side-effects がそろえた Unreleased の見出しの組（Breaking changes / New features / Deprecations / Bug fixes / Other changes）のうち「New features」に、組成で指定した多角形を塗る `fill` と、組成点に文字を置く `text`（化学式の整形を三角図の設定から引き継ぎ、呼び出しごとに切り替えられる）を 1 項目ずつ、既存の書式（英語の箇条書き）で書く。見出しは足さず、並べ替えない
  - 完了時: CHANGELOG の Unreleased の New features に 2 項目があり、見出しの組と既存の項目は変わっていない
  - _Requirements: 8.2_
  - _Boundary: CHANGELOG.md: New features entries for fill/text_

- [x] 4.4 全体の回帰確認を行う
  - 既存のテストファイルを変更せずに、テスト一式（`pytest -xs .`、未インストールなら `PYTHONPATH=src`）が通ることを確かめる。共通 doctest ランナー（`tests/test_doctests.py`）が `fill` と `text` の使用例を収集して実行し、通っていることを結果で確かめる
  - パッケージ本体（`_api.py`）の差分が追加行だけ（import、定数 2 つ、公開メソッド 2 つ、初期化の本体の `__auto_latex_notation` の 1 行（annotate-plain-text が足しておらず 3.2 で足した場合）、Plotter 2 つと配置の既定値の組）で、既存の定数・メソッド・Plotter の行を書き換えていないことを差分で確かめる
  - `ruff check .` と `ruff format --check .` を通す
  - 不具合が見つかったら、このタスクでは直さず、該当するタスクに戻って直す
  - 完了時: テスト一式（doctest ランナーを含む）と ruff の確認がすべて通り、`_api.py` の差分に削除行がない
  - _Requirements: 4.6, 5.4, 8.3_
  - _Boundary: verification only (no edits): src/ternary_diagram/_api.py diff, tests/ (full suite incl. tests/test_doctests.py), ruff_

## Implementation Notes
- 1: ヒートマップ < 塗りつぶしの確認は、それだけを理由付きでスキップできるよう別のテスト `test_default_zorder_heatmap_is_behind_fill` に分けた（`DEFAULT_ZORDER_HEATMAP` がなければ skip）
- annotate-plain-text はマージ済み: 整形の入口は `utils.to_latex_notation`、`annotate` の切り替え引数は `auto_latex_notation`（キーワード専用、`None` は v3 の表示＋FutureWarning）。`TernaryDiagram.__auto_latex_notation` は `__init__` に追加済み。`ruff check .` は既存のノートブックの F401 で落ちるので `ruff check src tests` で確かめる
- 2: `_FillPlotter` は既存の `_LinePlotter` にそろえて `super().__init__` に `z=None, z_min=None, z_max=None` を明示する（利用者の `z=` は TypeError になる）。3.1 で `text` を足したら、`fill` の docstring の Notes にも text より奥に描かれることを追記するとよい（レビューの提案）
- 3.1: matplotlib 3.10 では正式名と別名（`horizontalalignment` と `ha`）を同時に渡すと別名が後から効くため、別名の判定を外しても今の版ではテストが落ちない。判定は版の差に備えたものとして残す（レビューの所見）
- 3.2: `text` の整形は `_format_text`（annotate に `auto_latex_notation` を明示したときと同じ入口）を使い、v3 互換の警告経路は通らない。`Axes.text` のスタブが文字列しか受けないため、文字列以外を渡す箇所に理由付きの `# type: ignore[arg-type]` を置いた。3.1 の使用例は design の 3 ブロック構成に合わせて 3.2 の 2 ブロックに置き換えた
- 4.1: 層の zorder を比べる補助関数 `_assert_layers_are_stacked` は test_fill.py と test_text.py に重複している（conftest.py は境界外）。共通化するなら conftest に移す
- 4.2: 描画後処理の補助（`SUBPLOT_PARAMS`、`LAYOUT_WARNING_MATCH`、`_subplotpars` など）は test_side_effects.py・test_fill.py・test_text.py の 3 か所に重複している。4.1 の補助と合わせて、conftest に寄せる候補
- 4.3: CHANGELOG の 2 行だけなので、親が実装し、kiro-review の観点（見出しの組を変えない、New features への追記だけ、要件 8.2）で親がその場でレビューした
- 4.4: テスト一式 1630 passed, 1 skipped, 1 xfailed（-W error::FutureWarning）。共通 doctest ランナーで `TernaryDiagram.fill` / `text` が PASSED。`_api.py` の docs/add-roadmap からの差分は追加 309 行・削除 0 行。`ruff check src tests` / `ruff format --check src tests` は通過。`ruff check .` の 4 件はノートブック（example/、docs_src/tutorials/）の既存の F401 で、本 spec では変えていない。mypy は既存の 7 件
- 最終検証（`/kiro-validate-impl`）: GO。受入基準 43/43。指摘のうち `text` の docstring（`$` を含む文字列は設定にかかわらずそのまま表示される）と `fill` の Notes（`text` より奥）を直し、user-guide-docs の design の整形の判定の記述を `utils.to_latex_notation` に直した。steering の zorder の説明に fill 0.5 / text 4 を足すのはマージ後の steering 同期で行う
