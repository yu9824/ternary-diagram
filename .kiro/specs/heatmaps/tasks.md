# Implementation Plan

> 前提: roadmap の Implementation Order に従い、`plot-side-effects`（描画後処理の共通入口と三角図ごとの状態、`colorbar` の検証関数、利用者のコード位置で警告を出すヘルパー、`tight_layout=True` で三角図を作る `td` fixture、共通 doctest ランナー `tests/test_doctests.py`、CHANGELOG の Unreleased の見出しの組）、`diagram-customization`（`TernaryDiagram.__init__` の最終的なシグネチャと土台の部品）、直接実装の `annotate-plain-text` がマージ済みであること。`region-plots` とは 1 つずつマージし、どちらが先でもよい。2.1 以降はこれらを使う。
>
> docstring の例は steering の tech.md「Docstring Examples」に従い、共通 doctest ランナーで実行する。本 spec は doctest を実行する独自のテストを作らず、ランナーも変更しない。

- [ ] 1. 基盤: 格子生成と、三角形を塗る描画の計算・検証
- [x] 1.1 (P) 正則な三角格子を図なしで返す関数を追加する
  - 分割数が整数でない（真偽値を含む）ときは受け付ける値を示す `TypeError`、1 未満のときは範囲を示す `ValueError` にする。numpy の整数型は受け付ける
  - 格子点 (n+1)(n+2)/2 個（各成分が 1/n の整数倍で合計 1、列は頂点ラベルの順）と小三角形 n² 個を、design に定めた並び順（格子点は上の行から各行は左から、小三角形は上向きのあと下向き）と向き（反時計回り）で返す
  - 格子点や小三角形ごとの Python の繰り返しを使わず、numpy のベクトル演算で作る。`diagram-customization` が追加した配置関数とは別の名前にし、既存の関数は変えない
  - docstring（英語、NumPy スタイル）に戻り値の形・並び順・向きを書き、分割数 1 と 2 の doctest を付ける。純粋関数なので図を作らず、ファイルを書き出さず、出力は `tolist()` や `shape` など numpy の版や OS で表記が変わらない形にする
  - 完了時: 単体テストで、個数、組成の値と全列挙との一致、面積がすべて正で等しく合計が三角図の面積になること、分割数 1 と 2 の配列が規約どおりで 2 回呼んでも同じこと、例外が確認でき、すべて通る。この関数の docstring の例が共通 doctest ランナー（`tests/test_doctests.py`）で通る（独自の doctest 実行は書かない）
  - _Boundary: `src/ternary_diagram/utils.py`: `get_triangular_lattice`（と `from numbers import Integral` の import）、`tests/test_utils.py`: `get_triangular_lattice` のテストの追記_
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 8.1, 9.3, 9.5_

- [ ] 1.2 (P) 塗り方と kwargs の検証、三角形分割、塗れない三角形のマスク、既定の色の範囲を計算する関数群を作る
  - 新しいモジュールなので、先頭に `from __future__ import annotations` を置き、関数の注釈は組み込みジェネリクスと `X | None` で書く（tech.md）。実行時に評価される型別名だけは Python 3.9 で動く `typing` の形で書く。private なモジュールなので docstring に `>>>` の例は書かない
  - 塗り方は flat と gouraud だけを受け付け、それ以外は受け付ける値を示す `ValueError` にする
  - kwargs の検証: 旧名 `flag_cbar` は `colorbar` を案内する `TypeError`、`c` と `facecolors` は塗りの値と同時に使えない旨の `ValueError`、格子が固定の描画では `triangles` と `mask` も「NaN を返せば塗らずに残せる」ことを案内する `ValueError` にする。受け取った辞書は変更しない
  - 三角形分割: 三角形の指定がなければ自動で分割し（凸包の内側だけ）、分割の失敗（3 点未満、異なる点が 3 未満、一直線上）は理由を示す `ValueError` に元の例外をつないで置き換える。マスクの指定を反映し、どの三角形にも使われなかった点の数を返す。三角形が指定されたら matplotlib の検証に任せ、未使用点の数は 0 とする
  - 塗れない三角形: 点の値なら有限でない値を頂点に持つ三角形、三角形の値なら有限でない三角形を、既存のマスクとの論理和として新しい配列で返す。塗れる三角形が 1 つもなければ理由を示す `ValueError` にする
  - 既定の色の範囲は、指定のない側を有限な値の最小・最大で埋める。重複した組成の警告文（使われなかった点の数と、事前に集約する必要）を組み立てる
  - 塗り方・関数・戻り値の型別名と、関数ヒートマップの既定の分割数 50 を定義する。パッケージ内のモジュールは import しない
  - 完了時: 図を使わない単体テストで、各関数の正常系、例外（自動分割の失敗で元の例外がつながっていることを含む）、引数の辞書・配列・三角形分割を変更しないことが確認でき、すべて通る
  - _Boundary: `src/ternary_diagram/_mesh.py`（新規）: `Shading`、`HeatmapFunc`、`MeshCollection`、`SHADINGS`、`DEFAULT_HEATMAPF_SCALE`、`check_shading`、`check_mesh_kwargs`、`triangulate`、`unpaintable_mask`、`default_color_range`、`duplicate_points_message`、`tests/test_mesh.py`（新規）_
  - _Requirements: 1.4, 1.5, 1.7, 1.8, 2.5, 4.1, 4.2, 4.3, 5.4, 5.5, 6.5, 7.5, 7.6, 7.7_

- [ ] 1.3 関数を評価点でまとめて 1 回だけ呼び、戻り値を検証する関数を作る
  - 1.2 と同じモジュールに置くので、1.2 の後に行う（並行不可）
  - 呼び出し可能でないものには `TypeError` を出す。評価点の 3 成分をそれぞれ複製した 1 次元配列として関数をちょうど 1 回呼び、関数が出した例外は置き換えずにそのまま伝える
  - 戻り値を浮動小数点に変換し（マスク付き配列のマスクは NaN にする）、形 `(m,)`・`(m, 1)`・`(1, m)` を `(m,)` に揃える。それ以外の形や数値に変換できない戻り値は、期待する個数と `numpy.vectorize` での包み方を示す `ValueError` にする
  - 完了時: 単体テストで、呼び出し回数が 1、3 つの引数の形と値が評価点の各列と一致、関数が引数を書き換えても評価点が変わらないこと、受け付ける形と拒否する形、マスクの NaN 化、`TypeError`、関数の例外が同じオブジェクトのまま伝わることが確認でき、すべて通る
  - _Boundary: `src/ternary_diagram/_mesh.py`: `evaluate_function`、`tests/test_mesh.py`: `evaluate_function` のテストの追記_
  - _Requirements: 2.2, 2.6, 2.7, 2.8, 2.9_

- [ ] 2. 統合: 計算関数を Plotter と公開メソッドに組み込む
  - 2.1 と 2.2 は、共通の描画手順・Plotter・公開メソッド（いずれも design の「描画」層で、同じモジュール）に 1.x の関数と上流の描画後処理をつなぐ統合タスクである
- [ ] 2.1 共通の描画手順と重なり順の定数を用意し、`tripcolor` を TernaryDiagram に追加する
  - 既存の zorder 定数ブロックの末尾（`region-plots` が先にマージされていればその定数の後ろ）に、等高線より奥（-1）のヒートマップ用の定数を追加する。既存の定数の名前・値・並びは変えない
  - 共通の描画手順を Plotter の基底として用意する: `z_min` / `z_max` と別名 `vmin` / `vmax` の統合（既存の別名統合をそのまま使う）→ 塗れない三角形のマスク → 既定の色の範囲（`norm` だけが指定され範囲が未指定なら範囲を渡さない）→ 既定のカラーマップと zorder の注入（利用者の指定が優先）→ マスクの適用 → 値の位置（点 / 三角形）に応じた matplotlib の `tripcolor` 呼び出し。本 spec の例外はすべて matplotlib を呼ぶ前に出し終える
  - `tripcolor` の Plotter: 塗り方・kwargs の検証 → `triangles` / `mask` の取り出し → 基底の初期化 → `z` の欠落と要素数の検証 → 三角形分割 → 重複があれば `warn_external(..., category=UserWarning)` で利用者のコード位置に警告（roadmap の横断の取り決めで `warn_external` はパッケージ全体の利用者向け警告の入口）→ 描画 → `__init__` の最後で描画後処理を 1 回だけ呼ぶ。`tight_layout` やカラーバーを直接呼ばない。種類名は `"tripcolor"`
  - 公開メソッド `tripcolor` はデータ（組成と `z`）だけを位置引数にし、`z_min`・`z_max`・`shading`・`colorbar` をキーワード専用で受ける。`scatter` / `contour` と同じく、Plotter を作る前に `utils.check_optional_bool(colorbar, "colorbar")` で `colorbar` を検証し、検証済みの値を Plotter に渡す（Plotter では検証し直さない）。単なる真偽値の公開引数はない（足す場合は `utils.check_bool`）。Plotter を作り、座標を記録して戻り値を返す。既存のクラス・定数・メソッドは編集しない
  - docstring（英語、NumPy スタイル）に design の共通項目（引数と既定値、戻り値の型、例、matplotlib へのリンク、`colorbar` の 3 通りの意味、既定の色の範囲と別名、NaN の扱い、継ぎ目の消し方、See Also）と `tripcolor` 固有の項目（flat は 3 頂点の平均、凸包の内側だけ、`triangles` / `mask`、重複の集約）を書く
  - docstring の例は tech.md「Docstring Examples」に従う: doctest 形式で `fig, ax = plt.subplots(layout="constrained")` と `TernaryDiagram(..., ax=ax)` から始め、データはその場で作り（組成は重複させない）、既定の `colorbar` での色付きの描画は 1 回だけ、戻り値は変数に代入して環境で変わらない値だけを表示し、`savefig` は書かない
  - スモークテストは `tripcolor` の結合テストのファイルに置き、3.1 で拡充する
  - 完了時: スモークテストで flat なら `PolyCollection`、gouraud なら `TriMesh` が返り、Axes に 1 つずつ追加され、`td.x_["tripcolor"]` に座標が記録されることが確認でき、`tripcolor` の docstring の例が共通 doctest ランナーで FutureWarning なしに通り、既存のテストがすべて通る
  - _Depends: 1.2_
  - _Boundary: `src/ternary_diagram/_api.py`: `DEFAULT_ZORDER_HEATMAP`、`_MeshPlotter`、`_TripcolorPlotter`、`TernaryDiagram.tripcolor`（と `_mesh` の公開名・`check_optional_bool`・`warn_external` の import）、`tests/test_tripcolor.py`（新規: スモークテスト）_
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 4.1, 4.3, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 6.1, 6.2, 6.3, 6.4, 6.6, 6.7, 7.1, 7.2, 7.3, 7.4, 7.8, 7.9, 9.1, 9.5_

- [ ] 2.2 `heatmapf` を TernaryDiagram に追加する
  - 2.1 と同じモジュールを編集するので、2.1 の後に行う（並行不可）
  - `heatmapf` の Plotter: 塗り方・kwargs（格子固定）の検証 → 格子の生成（分割数の例外はそのまま伝える）→ 評価点の選択（flat は小三角形の重心、gouraud は格子点）→ 関数を 1 回だけ評価 → 評価点と関数値で基底を初期化 → 格子点の座標と小三角形から三角形分割を作る → flat は三角形の値、gouraud は点の値として共通の描画手順に渡す → `__init__` の最後で描画後処理を 1 回だけ呼ぶ。種類名は `"heatmapf"`、記録する座標は評価点
  - 公開メソッド `heatmapf` は関数だけを位置引数にし、`scale`（既定 50）・`z_min`・`z_max`・`shading`・`colorbar` をキーワード専用で受ける。2.1 と同じく Plotter を作る前に `utils.check_optional_bool(colorbar, "colorbar")` で検証し、検証済みの値を Plotter に渡す
  - docstring に design の共通項目と `heatmapf` 固有の項目（関数は `func(a, b, c)` の形で 1 回だけ呼ばれ、頂点ラベル順の 1 次元配列を受け取ること、返す値の形、スカラー専用の関数の `numpy.vectorize` での包み方、機械学習モデルの例、NaN を返せば塗らないこと、flat は重心・gouraud は格子点で評価し辺で定義されない関数には flat を勧めること、`scale` の既定値と三角形の数・速度・ファイルサイズの目安）を書く
  - docstring の例は 2.1 と同じ規約（`fig, ax = plt.subplots(layout="constrained")` と `TernaryDiagram(..., ax=ax)` から始める、ファイルを書き出さない、FutureWarning を出さない）に従う。他の描画を重ねる例では後の描画に `colorbar=False` を渡す
  - スモークテストは `heatmapf` の結合テストのファイルに置き、3.2 で拡充する
  - 完了時: スモークテストで既定の呼び出しが多角形 2,500 個の `PolyCollection`、gouraud が `TriMesh` を返し、関数の呼び出し回数が 1 で、`td.x_["heatmapf"]` に評価点が記録されることが確認でき、`heatmapf` の docstring の例が共通 doctest ランナーで FutureWarning なしに通り、既存のテストがすべて通る
  - _Depends: 1.1, 1.3_
  - _Boundary: `src/ternary_diagram/_api.py`: `_HeatmapfPlotter`、`TernaryDiagram.heatmapf`（と `get_triangular_lattice` の import）、`tests/test_heatmapf.py`（新規: スモークテスト）_
  - _Requirements: 2.1, 2.3, 2.4, 2.5, 3.6, 4.2, 6.1, 6.2, 6.3, 6.4, 7.1, 7.7, 7.8, 7.9, 9.1, 9.2, 9.5_

- [ ] 3. 検証と変更履歴
- [ ] 3.1 (P) `tripcolor` 固有の挙動を TernaryDiagram 経由で検証する結合テストを書く
  - flat の色の値が各三角形の 3 頂点の `z` の平均、gouraud の色の値が `z` そのものであることを確認する
  - 三角形の 3 頂点と内部の点では塗った面積の合計が三角図全体、内側の小さな三角形の頂点と内部の点ではその小さな三角形の面積に一致すること（凸包の外を塗らない）を確認する
  - kwargs の `triangles` で指定どおりの三角形になり、`mask` で塗る三角形が減ることを確認する
  - `z=None`、要素数の不一致、2 点、一直線上の点で `ValueError` になり、Axes の描画オブジェクトが増えないことを確認する
  - 重複した組成で `UserWarning` が 1 件出て、発生ファイルがテストファイルであることを確認する
  - `z` に NaN / inf を含めると、flat と gouraud の両方でその点を含む三角形が描かれず、全部 NaN なら `ValueError` になることを確認する
  - 2.1 のスモークテストと同じファイルに追記する
  - 完了時: `tripcolor` の結合テストがすべて通る
  - _Boundary: `tests/test_tripcolor.py`_
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 4.1, 4.3, 7.1, 7.8_

- [ ] 3.2 (P) `heatmapf` 固有の挙動を TernaryDiagram 経由で検証する結合テストを書く
  - 記録用の関数で、呼び出し回数が 1、引数が 3 つの 1 次元配列で各評価点の合計が 1 になること、flat では評価点が n² 個で全成分が 0 より大きい（辺上で評価しない）こと、gouraud では (n+1)(n+2)/2 個で三角形の頂点を含むことを確認する。第 1 引数が上の頂点の成分であること（`lambda a, b, c: a` で上ほど値が大きい）も確認する
  - flat の色の値が重心での関数値と一致すること、既定の `scale` で多角形が 2,500 個になることを確認する
  - `(m, 1)` を返す関数で描けること、スカラーを返す関数で `ValueError`（メッセージに `numpy.vectorize`）、呼び出し可能でないもので `TypeError`、例外を出す関数で元の例外になり、いずれも Axes の描画オブジェクトが増えないことを確認する
  - `scale=0` で `ValueError`、`scale=2.5` で `TypeError` になることを確認する
  - 一部の組成で NaN を返す関数では flat と gouraud の両方で該当する小三角形が描かれず、常に NaN なら `ValueError` になることを確認する。kwargs の `triangles` / `mask` で `ValueError` になることを確認する
  - `scale=100` の flat を軽い numpy の関数で描く時間を計測し、図の保存を除いて 1 秒未満であることを確認する
  - 2.2 のスモークテストと同じファイルに追記する
  - 完了時: `heatmapf` の結合テストがすべて通る
  - _Boundary: `tests/test_heatmapf.py`_
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.6, 4.2, 4.3, 7.1, 7.7, 7.8, 8.1_

- [ ] 3.3 (P) 両メソッドに共通の挙動を TernaryDiagram 経由で検証する結合テストを書く
  - `tripcolor` と `heatmapf` でパラメータ化する
  - 値の範囲: `z_min` / `z_max` と `vmin` / `vmax` で同じ範囲になり、同時指定は `scatter` と同じ文面の `ValueError`。未指定なら有限な値の最小・最大（`tripcolor` の flat では三角形の平均の範囲より広いこと）、片側だけの指定、`norm` の指定で例外が出ず渡した `norm` が使われること、既定のカラーマップが `scatter` / `contour` と同じであることを確認する
  - カラーバー: 既定で 1 本追加されて戻り値から参照できること、同じ三角図での 2 回目の既定の描画で追加かつ FutureWarning が 1 回（文面は `plot-side-effects` の所有物なので、`match=` は `"colorbar"` かメソッド名などの変わりにくい断片だけにする）、`colorbar=False` で増えず `colorbar=True` で増えること、`colorbar=1` で `TypeError` になり描画オブジェクトが増えないこと、`flag_cbar=False` で `TypeError` になること、戻り値を `TernaryDiagram.colorbar()` に渡したカラーバーの範囲とカラーマップが戻り値と一致することを確認する
  - レイアウト: `tight_layout=False` の三角図では余白が変わらず、`layout="constrained"` の図ではレイアウトエンジンが変わらないことを確認する
  - 重なり順: 散布図・等高線・線を先に描いてからヒートマップを描いても、ヒートマップの zorder が土台の線・等高線・線・散布図のどれよりも小さく、`zorder` を渡すとその値になることを確認する
  - kwargs: `alpha` と `edgecolors` が戻り値に反映されること、不正な `shading`、`c`、`facecolors` で `ValueError` になることを確認する
  - 種類名ごとに `x_` / `y_` が 1 組ずつ記録され、ヒートマップを描いても土台の線と文字の数が変わらないことを確認する
  - 完了時: 共通の結合テストがすべて通る
  - _Boundary: `tests/test_heatmaps.py`（新規）_
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.2, 7.3, 7.4, 7.5, 7.6, 7.8, 7.9, 7.10_

- [ ] 3.4 (P) CHANGELOG の Unreleased に追加機能を記載する
  - `plot-side-effects` がそろえた Unreleased の見出しの組（Breaking changes / New features / Deprecations / Bug fixes / Other changes）のうち New features に、`TernaryDiagram.tripcolor`、`TernaryDiagram.heatmapf`、`ternary_diagram.utils.get_triangular_lattice` を、既存の項目の書式（英語、箇条書き）で追記する
  - 見出しは足さず、他の spec が追記した項目は並べ替えない
  - 完了時: CHANGELOG の Unreleased の New features に 3 項目があり、既存の書式に揃っている
  - _Boundary: `CHANGELOG.md`: Unreleased の New features の `tripcolor` / `heatmapf` / `get_triangular_lattice` の項目_
  - _Requirements: 9.4_

- [ ] 3.5 全体の回帰確認を行う
  - テスト全体（`pytest -xs .`。共通 doctest ランナー `tests/test_doctests.py` を含む）、`ruff check .`、`ruff format --check .` を実行する。mypy は環境にあれば実行し、なければインストールせずに確認できなかったことを報告する
  - 既存のテスト（`scatter`・`contour`・`plot`・`annotate`・三角図の土台）を変更せずに通ること、ランタイム依存（`pyproject.toml` の dependencies）が numpy と matplotlib のままであることを確認する
  - `region-plots` が先にマージされている場合は、`DEFAULT_ZORDER_HEATMAP (-1) < DEFAULT_ZORDER_FILL (0.5)` であることを確認する
  - 完了時: テスト全体（共通 doctest ランナーで `tripcolor`・`heatmapf`・`get_triangular_lattice` の例が FutureWarning なしに通ることを含む）と ruff の確認が通り、依存の追加がない
  - _Boundary: 読み取りと実行のみ（ファイルを変更しない）。確認対象: テスト全体、`pyproject.toml`: `[project] dependencies`、`src/ternary_diagram/_api.py`: `DEFAULT_ZORDER_*`_
  - _Requirements: 7.2, 7.10, 8.2, 9.5_

## Implementation Notes
- 上流の状態: plot-side-effects・diagram-customization・annotate-plain-text・region-plots はマージ済み。zorder 定数は `DEFAULT_ZORDER_FILL = 0.5`、`DEFAULT_ZORDER_TEXT = 4` が既にあり、ヒートマップの定数はその後ろに置く。`tests/test_fill.py::test_default_zorder_heatmap_is_behind_fill` は `DEFAULT_ZORDER_HEATMAP` があれば自動で有効になる。`ruff check .` はノートブックの既存の F401 で落ちるので `ruff check src tests` で確かめる。mypy は既存の 7 件が基準
- 1.1: 頂点番号は design の対応表ではなく閉形式 `row*(row+1)//2 + row - j` で求める（scale 1〜79・123・200 で総当たりと一致）。格子の (i, j) は private の `_lattice_indices` に切り出した
