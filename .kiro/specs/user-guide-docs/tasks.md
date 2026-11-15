# Implementation Plan

- [x] 1. 基盤: 前提の確認、ビルド設定、使い方ページの骨組み
- [x] 1.1 上流の実装と作業環境を確かめ、ドキュメントに書く名前を照合する
  - 上流（副作用の制御、土台のカスタマイズ、annotate-plain-text、相図、ヒートマップ）がすべてマージ済み（roadmap の Implementation Order で本 spec は最後）で、共通の doctest ランナー `tests/test_doctests.py` を含む既存のテスト一式が通ることを確かめる。未マージなら作業を止めて報告する。上流の docstring の例がランナーで失敗する場合は書き換えず、担当 spec の不具合として記録する
  - ドキュメントのビルド（`docs` extras 一式とカーネル）に使える既存の環境を確かめる。パッケージはインストールせず、使える環境がなければ承認を得る
  - チュートリアルの再実行（Jupyter、pandas、`element_recognition`）に使える既存の環境の有無を確かめて記録する。なくても作業は止めず、7.1 を保留にするかどうかの判断に使う
  - design の「上流 API の名前の一覧」の各項目（作成時の引数の最終形、引数名、既定値、戻り値の型、重なり順の値、`text` の `auto_latex_notation=None`）を公開 API と照合し、推奨の書き方（`layout="constrained"` の図）で各メソッドを 1 回ずつ呼んで、エラーと FutureWarning が出ないことを確かめる
  - annotate-plain-text がマージした整形の規則（化学式とみなす条件、切り替え引数の名前、作成時の設定を引き継ぐかどうか、FutureWarning を出す呼び出し）を確かめて記録する
  - `__init__` の docstring に上流の Examples がなく、`*_kw` の使用例が対応する `set_*` の docstring にあることを確かめる。共通の doctest ランナーが、本 spec が担当する docstring（作成時、散布図、等高線図、線、注釈、カラーバーのメソッド、`utils` の既存 5 関数）を対象に含み、今の `__init__` の例に `xfail(strict=True)` の印が付いていることを確かめる
  - レイアウト、カラーバーの重複、`flag_cbar` の改名の 3 種類の FutureWarning（annotate-plain-text が警告を出す場合はそれも）を実際に出して、文面を確かめる
  - 食い違いがあれば上流のコードや docstring は直さず、担当 spec の課題として記録し、ページはコードに合わせる
  - 完了時: 一覧のすべての名前が公開 API に存在し、各メソッドの呼び出しがエラーと FutureWarning なしに終わることを確認でき、使う環境、チュートリアルの再実行の環境の有無、annotate-plain-text の規則、食い違いの有無が記録されている
  - _Boundary: 変更なし（読み取りと、一時ディレクトリでの試し実行だけ。リポジトリのファイルは変えない）_
  - _Requirements: 1.9, 3.4, 8.3, 9.1_

- [x] 1.2 使い方ページの実行と作成時の引数の表示を有効にするビルド設定を入れる
  - 実行できるページを毎回実行し、チュートリアルは保存済みの出力のまま表示し、セルの例外でビルドを失敗させ、stderr の出力を警告にし、実行時の作業ディレクトリを一時ディレクトリにする設定を入れる。実行結果のキャッシュは使わない
  - クラスの docstring に続けて作成時の docstring を API リファレンスに表示する設定を入れる
  - テーマ、テンプレート（フッターの広告スクリプト）、拡張の構成、ドキュメントのワークフローは変えない
  - API リファレンスの生成物（目次とパッケージのページの元ファイル）を git の追跡対象から外す
  - 完了時: CI と同じ手順（API リファレンスの生成 → ビルド）を一時ディレクトリへ出力すると警告 0 件で終わり、API リファレンスに `materials`・`tight_layout`・`grid_kw` の説明が表示され、チュートリアルが実行されず、生成物が `git status` に現れない
  - _Boundary: `docs_src/conf.py`（`nb_execution_mode`・`nb_execution_excludepatterns`・`nb_execution_raise_on_error`・`nb_execution_in_temp`・`nb_output_stderr`・`autoclass_content` の設定だけ）、`.gitignore`（`docs_src/modules.rst`・`docs_src/ternary_diagram*.rst` の行だけ）_
  - _Requirements: 1.8, 9.3, 9.4, 13.3, 13.4, 13.5_

- [x] 1.3 使い方ページの骨組みと 3 区分の目次を作る
  - 6 ページ（はじめての三角図、見た目の変え方、相図の描き方、ヒートマップと等高線の使い分け、レイアウトとカラーバー、v4.0.0 への移行）を、design の URL 一覧どおりの場所に、実行されるノートブック形式のヘッダー、英語の H1、1 段落の導入だけで作る
  - 使い方ページの一覧ページに、6 ページへのリンク、各ページで何ができるかの 1 行の説明、目次を置く
  - トップページの目次を「User guide」「Tutorials」「API Reference」の 3 区分にする。既存のチュートリアルと API リファレンスの目次と URL は変えない
  - 完了時: ビルドが警告 0 件で終わり、サイドバーに 3 区分と使い方ページ 7 つ（一覧を含む）が表示され、既存のチュートリアルと API リファレンスのページが同じ URL で生成される
  - _Boundary: `docs_src/index.md`（toctree だけ）、`docs_src/user_guide/index.md`（新規）、`docs_src/user_guide/{getting_started,customizing,phase_diagrams,heatmaps_and_contours,layout_and_colorbars,migration_v4}.md`（新規。ヘッダー・H1・導入だけ）_
  - _Requirements: 2.1, 8.7, 10.2, 10.3, 10.4_

- [ ] 2. 既存の公開 API の docstring
- [x] 2.1 クラス、作成時の引数、プロパティの docstring を書く
  - クラスの要約と説明、作成時の要約、`materials`・`ax`・`auto_latex_notation` の項目、描いた座標の記録（`x_`・`y_`）の Attributes 節、プロパティ `ax`・`fig` を、design の docstring の規約と担当表に従って書く
  - `__init__` の Examples 節は本 spec だけが持ち、単独で書き直す。担当する引数（`materials`・`ax`・`auto_latex_notation`）を使い、必要な import の行から始めて推奨の図の作り方で `ax=ax` を渡し、単独で実行でき、repr の出力行を書かず、ファイルに保存せず、FutureWarning を出さない例にする。`*_kw` の使用例は対応する `set_*` の docstring にあるので書かない
  - 書き直した例が共通の doctest ランナーで通ったら、ランナーが今の `__init__` の例に付けている `xfail(strict=True)` の印を外す。ランナーの他の部分は変えない
  - 上流の項目（`tight_layout` と `*_kw` の Parameters の項目、クラスの Notes 節）は書き換えない。シグネチャと本体のコードは変えない
  - 完了時: API リファレンスに担当の項目がすべて表示され、`__init__` の xfail の印を外した状態で、共通の doctest ランナーが作成時の例をエラーと FutureWarning なしに通し（XPASS や xfail として扱われない）、`tests/test_doctests.py` の差分がその印の削除だけで、上流の項目と本体のコードに差分がない
  - _Boundary: `src/ternary_diagram/_api.py`: docstring だけ（クラス `TernaryDiagram` の要約と説明、`TernaryDiagram.__init__` の担当表の本 spec の項目と Examples 節、プロパティ `TernaryDiagram.ax`・`TernaryDiagram.fig`）。コードは変えない。`tests/test_doctests.py`: `__init__` の例の xfail の印を外すだけ_
  - _Requirements: 1.1, 1.3, 1.5, 1.6, 1.7, 1.9, 9.1, 9.2_

- [x] 2.2 散布図と等高線図の docstring の担当項目を書く
  - `vector`・`z`・`z_min`・`z_max`・`annotations`（散布図）・`fill`（等高線図）・追加のキーワード引数の項目、戻り値、See Also、Notes の本 spec の段落、使用例を、規約と組成の定型文に従って書く
  - 等高線図について、`fill` が真なら塗りつぶし、偽なら線だけを描くこと、`z` が必須であること、自動の段階と `levels` の関係を書く。散布図の `annotations` の整形は、1.1 で確かめた annotate-plain-text の規則どおりに書く
  - 副作用の制御の spec が書いた Parameters の `colorbar`・`flag_cbar` の項目と、annotate-plain-text が足した切り替え引数の項目は書き換えず、本 spec の項目と段落はその前後に追記する
  - 完了時: 2 つの docstring の担当する項目に、説明文のない `, by default X` だけの項目と誤った頂点の順序の説明がなく、使用例が共通の doctest ランナーでエラーと FutureWarning なしに通り、上流の項目と段落に差分がない
  - _Boundary: `src/ternary_diagram/_api.py`: `TernaryDiagram.scatter`・`TernaryDiagram.contour` の docstring のうち担当表の本 spec の項目と段落だけ（Parameters の `colorbar`・`flag_cbar` の項目と、annotate-plain-text の切り替え引数の項目を除く）。コードは変えない_
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.9, 9.1, 9.2_

- [x] 2.3 線、注釈、カラーバーのメソッドの docstring を書く
  - 3 つのメソッドのすべての引数（annotate-plain-text が足した切り替え引数を除く）、戻り値、ラップしている matplotlib 関数の URL、使用例を規約に従って書く
  - 注釈について、1.1 で確かめた annotate-plain-text の整形の規則と、既定の位置と大きさを書く。annotate-plain-text が FutureWarning を出す場合は、例を警告の出ない書き方にする
  - カラーバーのメソッドについて、各引数の既定値と、このメソッドで作ったカラーバーが自動追加の判定で既存のカラーバーに数えられることを書く。散布図・等高線図の `colorbar` 引数の説明は重複させない
  - 完了時: 3 つの docstring が担当するすべての引数の意味と既定値を持ち、使用例が共通の doctest ランナーでエラーと FutureWarning なしに通り、上流の項目に差分がない
  - _Boundary: `src/ternary_diagram/_api.py`: `TernaryDiagram.plot`・`TernaryDiagram.annotate`・`TernaryDiagram.colorbar` の docstring だけ（`annotate` の annotate-plain-text の切り替え引数の項目を除く）。コードは変えない_
  - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7, 1.9, 9.1, 9.2_

- [x] 2.4 `utils` の既存の公開関数の docstring を書く
  - `check_ax`・`check_2d_vector`・`check_1d_vector`・`three2two`・`get_label` の要約、各引数の意味・受け付ける値・既定値、戻り値、送出する例外、doctest 形式の使用例を、design の `utils` の規約（節の順序、期待出力、例は自分の import の行から始める、図を扱わない関数の例では図を作らない）に従って書く
  - `get_label` の判定の規則は、1.1 で確かめた annotate-plain-text のマージ時点の挙動どおりに書き、annotate-plain-text が足した項目は書き換えない
  - 上流が `utils` に足した関数（`check_optional_bool`・`check_bool`、配置の関数と `TickFormat`、`get_triangular_lattice`）は変えない
  - 完了時: 5 つの関数の docstring に既定値だけで意味のない説明がなく、使用例が共通の doctest ランナーで通り、上流の関数と項目、本体のコードに差分がない
  - _Boundary: `src/ternary_diagram/utils.py`: `check_ax`・`check_2d_vector`・`check_1d_vector`・`three2two`・`get_label` の docstring だけ（annotate-plain-text が `get_label` に足した項目を除く）。コードと上流が足した関数は変えない_
  - _Requirements: 1.6, 1.7, 1.9, 1.10, 9.1, 9.2_

- [ ] 2.5 担当する docstring の例の有無と不備を確かめるテストを追加する
  - 確かめる範囲は design の docstring の担当表で本 spec のものとした項目と節だけにする: 担当する 11 の Examples 節（作成時、散布図、等高線図、線、注釈、カラーバーのメソッド、`utils` の既存 5 関数）に使用例が 1 つ以上あること、担当する Parameters・Attributes の項目（design の `OWNED_ENTRIES`）がそれぞれ存在し、`, by default X` のほかに意味を書く文を持ち、`semi-clockwise` を含まないことを確かめるテストを書く。例は実行しない（共通の doctest ランナーが実行する）
  - 上流が担当する項目と節（`tight_layout`・`*_kw`・`colorbar`・`flag_cbar`・annotate-plain-text の切り替え引数の項目、クラスの Notes 節など）は確認の対象にしない。これらは steering の tech.md「Docstring Examples」の規約に担当 spec が自分で従うもので、違反に気づいた場合は書き換えず、担当 spec の不具合として記録する（本 spec のテストの合否には含めない）
  - 公開名だけを使い、プライベートモジュールを import しない
  - 完了時: 追加したテストが本 spec の担当範囲（担当する Examples 節と `OWNED_ENTRIES` の項目）に対して通り、テストが上流の項目を読まないことをコードで確認でき、既存のテスト一式がネットワークなしで通る
  - _Boundary: `tests/test_owned_docstrings.py`（新規）_
  - _Depends: 2.1, 2.2, 2.3, 2.4_
  - _Requirements: 1.1, 1.5, 1.7, 1.10, 9.1, 9.2_

- [ ] 2.6 上流の 4 メソッドの型の行と `**kwargs` の項目名を揃える（1.1 で追加）
  - `fill`・`text`・`tripcolor`・`heatmapf` の Parameters のうち、型の行（`ArrayLike | shape = (n, 3)` → `array-like of shape (n, 3)`、`Number or None` → `float`、`(3,) or (1, 3)` の形など）と `kwargs : parameter of ...` の項目名（→ `**kwargs`）だけを、design の docstring の規約（2.2・2.3 で既存メソッドに適用するもの）に揃える。`None` を受け付けることが説明文に書かれていなければ、その旨の短い文を足す
  - 説明文の内容、See Also・Notes・Examples の節、シグネチャと本体のコードは変えない
  - 完了時: 4 つの docstring の型の行と項目名が既存メソッドと同じ書き方になり、共通の doctest ランナーが通り、型の行と項目名と `None` の文以外に差分がない
  - _Boundary: `src/ternary_diagram/_api.py`: `TernaryDiagram.fill`・`TernaryDiagram.text`・`TernaryDiagram.tripcolor`・`TernaryDiagram.heatmapf` の docstring の Parameters の型の行と項目名だけ。コードは変えない_
  - _Depends: 2.2, 2.3_
  - _Requirements: 1.1, 1.6_

- [ ] 3. 目的別の使い方ページ
- [x] 3.1 (P) はじめての三角図のページを書く
  - design のページの規約（推奨の図の作り方、numpy の合成データ、図の代替テキスト、API へのリンク、英語、1 つの図は 1 つのセル）に従う
  - インストール（静的なコマンド）、最初の図を描いて保存する手順、組成の並びと合計が 1 でなくてよいこと（表形式のデータは文章で説明）、既存の Axes への描画と 2 つの三角図の並べ方、描画メソッドの一覧と各ページへの案内の節を書く
  - 化学式の節では、作成時の `auto_latex_notation` が頂点ラベルの整形を決めることとその止め方、`text` が `auto_latex_notation=None` でその設定を引き継ぐこと、注釈（`annotate`・`scatter(annotations=...)`）の整形は 1.1 で確かめた annotate-plain-text の規則に従うことを書く
  - 完了時: ページがビルド時に実行されて警告 0 件で表示され、図にはすべて代替テキストが付き、描画メソッドの一覧から各ページと API リファレンスへリンクできる
  - _Boundary: `docs_src/user_guide/getting_started.md`_
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 9.1, 9.2, 9.5_

- [ ] 3.2 (P) 見た目の変え方のページを書く
  - ページの規約に従い、5 つの部品と作成時・作成後の指定の対応表（`border_kw` → `set_border`、`grid_kw` → `set_grid`、`tick_kw` → `set_ticks`、`axis_label_kw` → `set_axis_labels`、`vertex_label_kw` → `set_vertex_labels`）、グリッドと目盛りの間隔、目盛りの書式と両端、軸タイトルと目盛りの配置規約（どの辺がどの成分で、値がどちら向きに増えるか）、非表示と matplotlib のプロパティ、直前の設定の引き継ぎ、artist の取り出し、指定の使い回しの節を書く
  - 完了時: ページがビルド時に実行されて警告 0 件で表示され、各節の例の図が代替テキスト付きで表示され、軸タイトルの節の図で 3 辺のタイトルと目盛りの向きが確認できる
  - _Boundary: `docs_src/user_guide/customizing.md`_
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 9.1, 9.2, 9.5_

- [ ] 3.3 (P) 相図の描き方のページを書く
  - ページの規約に従い、架空の例であることを本文に書いたうえで、相領域の塗りと凡例、頂点の順序（並べ替えや凸包の計算をしないこと）、文字の配置と整形（`text` の `auto_latex_notation` は既定の `None` で作成時の設定を引き継ぎ、`False` で止める）、既定の重なり順の表と透明度・重なり順の変え方、色だけに頼らない示し方、等高線図の `fill` 引数と `fill` メソッドの違いの注記の節を書く
  - 完了時: ページがビルド時に実行されて警告 0 件で表示され、相図の例の図で各領域が凡例と文字のラベルの両方で区別でき、図に代替テキストが付いている
  - _Boundary: `docs_src/user_guide/phase_diagrams.md`_
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 9.1, 9.2, 9.5_

- [ ] 3.4 (P) ヒートマップと等高線の使い分けのページを書く
  - ページの規約に従い、4 つの描画（色付きの散布図、等高線図、測定点のヒートマップ、関数のヒートマップ）を比べる表と、同じ合成データを 4 通りで描いた図の節を書く
  - 2 つの塗り方の違い、関数のヒートマップの関数の呼ばれ方・格子の細かさ・塗らない領域の作り方・格子の関数、値の範囲とカラーマップの指定とカラーバーの共有、欠損値を含むデータの結果、カラーマップの選び方（既定は `rainbow`、大小の値には明るさが単調なもの、正負の値には中央が無彩色の発散型）の節を書く
  - 完了時: ページがビルド時に実行されて警告 0 件で表示され、比較の図と各節の図が代替テキスト付きで表示され、欠損値の節の図で塗られない三角形が確認できる
  - _Boundary: `docs_src/user_guide/heatmaps_and_contours.md`_
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 9.1, 9.2, 9.5_

- [ ] 3.5 (P) レイアウトとカラーバーのページを書く
  - ページの規約に従い、レイアウト自動調整の 3 通りの指定と v3.x・v4.0.0 の挙動の表（未指定のまま FutureWarning を出す例は実行しない）、レイアウトエンジンのある図・複数パネル・subfigure への描き方、カラーバーの自動追加の 3 通りと既存のカラーバーの範囲、カラーバーを後から 1 本だけ付ける方法、移行ページへのリンクの節を書く
  - 完了時: ページがビルド時に実行されて警告 0 件で表示され、subfigure の例と後から付けたカラーバーの例の図が代替テキスト付きで表示され、移行ページへのリンクが機能する
  - _Boundary: `docs_src/user_guide/layout_and_colorbars.md`_
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 7.1, 7.2, 7.3, 7.4, 7.5, 9.1, 9.2, 9.5_

- [ ] 3.6 (P) v4.0.0 への移行ページを書く
  - ページの規約に従い、v4.0.0 で変わる既定値と削除予定の引数を、v3.x と v4.0.0 の挙動、保つ書き方、先取りする書き方で対比する表を書く
  - レイアウト、カラーバーの重複、`flag_cbar` の改名のそれぞれについて、出る条件、移行前のコード（静的なコードブロック）、同じコードを警告を捕まえて実行し文面を標準出力に表示するセル（入力は折りたたむ）、保つ書き方と先取りする書き方の実行される例を書く。新しい描画メソッドが `flag_cbar` を受け付けないことも書く
  - 1.1 で annotate-plain-text が注釈の整形の変更を FutureWarning で予告すると確かめた場合だけ、その警告についても同じ形の節と表の行を置く
  - 影響を受ける呼び出しをすべて見つける方法（FutureWarning をエラーとして扱う実行方法）と、CHANGELOG とレイアウトのページへのリンクを書く
  - 完了時: ページがビルド時に実行されて警告 0 件で表示され、捕捉セルの出力に 3 種類（annotate-plain-text が警告を出す場合は 4 種類）の警告文が公開する版の文面のまま表示され、移行前のコードと捕捉セルのコードが一致し、図があればすべてに代替テキストが付いている
  - _Boundary: `docs_src/user_guide/migration_v4.md`_
  - _Requirements: 2.3, 2.4, 2.5, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.1, 9.2, 9.5_

- [ ] 4. チュートリアルのコードの更新
- [ ] 4.1 (P) 6 つのノートブックのコードを推奨の書き方に直す
  - 等高線図のノートブックの `flag_cbar=False` を `colorbar=False` に置き換える
  - すべてのノートブックで図を `layout="constrained"` で作って三角図に Axes を渡し、利用者側の `fig.tight_layout()` の呼び出しを削除し、複数の図のノートブックの説明文を constrained layout の説明に直す
  - README のノートブックのコードを、README とトップページで共有する新しい最小の例にする
  - 先頭のセルの見出しと、データファイルの読み込みパスは変えない。保存済みの出力の更新は 7.1 で行う
  - 完了時: どのノートブックにも `flag_cbar` と利用者側の `tight_layout` の呼び出しが残っておらず、最小の例のコードが README のノートブックの中で確定している
  - _Boundary: `example/**/*.ipynb`（コードと説明文のセルだけ。保存済みの出力、PNG、CSV は変えない）_
  - _Requirements: 11.1, 11.5, 12.5_

- [ ] 5. 統合: トップページ、README、変更履歴
- [ ] 5.1 (P) トップページとチュートリアルの一覧を仕上げる
  - トップページに、1 段落の概要（ランタイム依存が numpy と matplotlib だけであること）、既存の画像、インストール方法、4.1 で確定した最小の例、使い方ページ 6 つ（移行ページを含む）・チュートリアル・API リファレンスへの案内の節を置く
  - チュートリアルの一覧に、既存の目次の並びと URL を保ったまま各ノートブックの 1 行の説明と、目的別の説明は使い方ページにある旨の案内を足す
  - 完了時: ビルドが警告 0 件で終わり、トップページから移行ページを含むすべての使い方ページへ 1 回の移動でたどれ、チュートリアルの一覧の各項目に説明がある
  - _Boundary: `docs_src/index.md`（本文。1.3 で作った toctree は保つ）、`docs_src/tutorials/index.md`（各項目の説明と案内だけ。toctree の並びと名前は変えない）_
  - _Requirements: 8.7, 10.1, 10.4, 10.5_

- [ ] 5.2 (P) README を書き直す
  - design の README の構成（バッジ、概要と画像、主な機能、インストール、最小の例とその出力画像、ドキュメントへのリンク、変更履歴とライセンス）に絞り、同じ内容のコード例を重複させない
  - 主な機能に上流 4 spec の機能（土台の見た目の変更、相図、ヒートマップ、レイアウトとカラーバーの制御）を含め、使い分け表は載せない
  - 最小の例は 4.1 で確定したコードと同じにし、画像は既存のファイル名（`example/example_on_readme/figure.png`）の raw URL を参照する（画像の中身は 7.1 で更新される）。画像とリンクはすべて `https://` の絶対 URL にし、既存のバッジを残す
  - 完了時: README が構成の節だけを持ち、相対パスのリンクと画像がなく、最小の例のコードが README のノートブックのコードと一致している
  - _Boundary: `README.md`_
  - _Requirements: 9.1, 9.2, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [ ] 5.3 (P) CHANGELOG の Unreleased にドキュメントの変更を書く
  - その他の変更として、使い方ページと移行ページの追加、README の刷新、チュートリアルの更新を英語の箇条書きで書き、移行ページの絶対 URL を含める。上流の項目は変えない
  - 完了時: CHANGELOG の Unreleased に該当の項目と移行ページへのリンクがあり、既存の項目の書式に揃っている
  - _Boundary: `CHANGELOG.md`（Unreleased の Other changes にある本 spec の項目だけ）_
  - _Requirements: 14.1_

- [ ] 5.4 README とトップページの最小の例を確かめるテストを追加する
  - README とトップページの最初の Python のコードブロックが同じであることと、そのコードが一時ディレクトリで FutureWarning をエラーとして扱ってもエラーなく実行できることを確かめるテストを、新しいファイルに書く。docstring の例は扱わない（共通の doctest ランナーが実行する）
  - 完了時: 追加したテストと既存のテスト一式がネットワークなしで通る
  - _Boundary: `tests/test_docs_examples.py`（新規）_
  - _Depends: 5.1, 5.2_
  - _Requirements: 9.1, 9.2, 10.5, 12.5_

- [ ] 6. 検証
- [ ] 6.1 CI と同じ手順でドキュメント全体をビルドして検証する
  - API リファレンスを生成してから一時ディレクトリへビルドし、終了コード 0 と出力の警告 0 件を確かめる
  - 生成されたすべての HTML に広告スクリプトがあること、使い方ページ 5 つと移行ページに空でない代替テキスト付きの図があること、API リファレンスに作成時のすべての引数の説明があること、既存のチュートリアルと API リファレンスの URL が残っていること、出力先に実行結果のキャッシュがなく、ドキュメントのソースに実行による新しいファイルがないことを確かめる
  - 使い方ページの 1 セルに一時的に例外を入れるとビルドが失敗し、FutureWarning を出すコードを入れると警告になることを確かめてから元に戻す
  - 移行ページの捕捉セルの出力に 3 種類（annotate-plain-text が警告を出す場合は 4 種類）の警告文が表示されることを確かめ、確認後に API リファレンスの生成物を削除する
  - 完了時: 上記の確認がすべて通り、作業ツリーに生成物や一時的な変更が残っていない
  - _Boundary: 変更なし（ビルドの出力は一時ディレクトリ。生成される `docs_src/modules.rst`・`docs_src/ternary_diagram*.rst` と、否定の確認で一時的に変える `docs_src/user_guide/*.md` の 1 セルは、確認後に元に戻す）_
  - _Requirements: 1.8, 2.5, 8.3, 9.3, 9.4, 10.2, 10.3, 13.1, 13.2, 13.4, 13.5_

- [ ] 6.2 回帰確認とレビューを行う
  - 共通の doctest ランナーを含むテスト一式と、ruff の lint と format の確認を実行する。ruff が使える既存の環境がなければ、インストールせずに確認できなかったことを報告する。上流の docstring の例による失敗は、担当 spec の不具合として記録したうえで本 spec の判定から除く
  - 差分で、上流が担当する docstring の項目（`__init__` の上流の Parameters の項目、`scatter` / `contour` の `colorbar`・`flag_cbar` の項目、annotate-plain-text の項目、上流が `utils` に足した関数を含む）、ライブラリのコード、テーマ・テンプレート・ドキュメントのワークフローが変わっておらず、`tests/test_doctests.py` の差分が `__init__` の xfail の印の削除だけであることを確かめる
  - 各使い方ページが design のページの節をすべて持ち、担当する docstring が規約どおり（例が自分の import の行から始まることを含む）で、`__init__` の Examples 節に `*_kw` の例がないことをレビューする。上流が担当する項目の tech.md の規約違反に気づいた場合は、書き換えずに担当 spec の不具合として記録する
  - 7.1 を保留にした場合は、保留にしたノートブック、理由、未達の要件を報告に含める
  - 完了時: テスト一式と ruff の確認が通り（または未確認の理由が報告され）、境界外のファイルに差分がなく、レビューで見つかった不足が解消されている
  - _Boundary: 変更なし（確認とレビューだけ。見つかった不足は、該当するタスクの Boundary の中で直す）_
  - _Requirements: 1.6, 1.9, 2.1, 12.4, 13.3_

- [ ] 7. チュートリアルの再実行（独立した作業。前提がそろわなければ保留にし、1〜6 を止めない）
- [ ] 7.1 (P) ノートブックを再実行して保存済みの出力と画像を更新する
  - 前提: 4.1 が完了し、1.1 でチュートリアルの再実行に使える既存の環境が確認できていること
  - 保留の条件: 使える既存の環境がない、またはパッケージのインストールの承認が得られない場合は、このタスクを保留（blocked）として記録して終える。`element_recognition` だけがない場合は、注釈付きの散布図のノートブックだけを保留にし、残りの 5 つは再実行する。1〜6 のタスクはこのタスクを待たずに完了にしてよい
  - 既存の環境で、開発中のライブラリを読み込む設定にして、各ノートブックのディレクトリを作業ディレクトリにし、先頭から実行して出力を保存する。`element_recognition` を使うノートブックは、それが入った既存の環境で実行する
  - 出力画像は同じファイル名で上書きし、データファイルは変えない
  - 完了時: 再実行したノートブックの保存済みの出力に stderr とエラーの出力がなく、出力画像（README の `figure.png` を含む）が更新され、データファイルに差分がなく、example のデータを読む既存のテストが通る。保留にした場合は、保留にしたノートブック、理由、未達の要件（11.2、11.3、12.5 の画像）が記録されている
  - _Boundary: `example/**/*.ipynb`（保存済みの出力だけ）、`example/**/*.png`（同じファイル名での上書きだけ）。コードのセルと CSV は変えない_
  - _Depends: 4.1_
  - _Requirements: 11.2, 11.3, 11.4, 12.5_

## Implementation Notes

- 1.1 の結果（2026-11-15）:
  - 上流 4 spec と annotate-plain-text はすべて統合ブランチにマージ済み。テスト一式は 1967 passed, 1 xfailed（xfail は共通の doctest ランナーの `__init__` の印。`reason` は「既存の Examples が repr を出力し、`ax=` を渡さず、`savefig` を呼ぶ」）
  - design の「上流 API の名前の一覧」は、シグネチャ、既定値、戻り値の型（`fill` → `List[Polygon]`、`text` → `Text`、`tripcolor` / `heatmapf` → `PolyCollection` か `TriMesh`）、重なり順（heatmap -1 < contour 0 < fill 0.5 < 外枠・グリッド 1 < plot 2 < scatter・annotate・頂点ラベル 3 < text 4）、`text` の中央揃えと `auto_latex_notation=None` まで、すべてコードと一致した。`layout="constrained"` の図で全メソッドと `set_*` を 1 回ずつ呼んで、エラーも警告も出なかった
  - 食い違い（軽微、上流は直さない）: `scatter` の型注釈は `annotations: Optional[List[str]]` だが、実際は str 以外（数値など）も受け付けて `str()` で表示する。ページと docstring はコードの挙動に合わせる
  - annotate-plain-text の規則: `utils.to_latex_notation` が空白で区切った語のうち `utils.is_chemical_formula` が化学式とみなすもの（大文字で始まる元素記号と数字・括弧の並び。例 `Li2O`、`(LiLa)0.5TiO3`）だけを `get_label` で整形し、`$` を含む文字列はそのまま返す。`"Li2O-La2O3"` のように空白以外で区切った語は整形しない。切り替え引数は `annotate(..., *, auto_latex_notation=None)` と `scatter(..., *, auto_latex_notation=None)`。`None` は v3.x の表示（`get_label` ですべての数字を下付き）を保ち、4.0.0 で表示が変わる文字列（`"Sample 1"` など）にだけ FutureWarning を三角図ごとに 1 回出す。`$` を含む文字列は警告なしでそのまま表示（v3 の出力は描けない mathtext だったためバグ修正扱い）。4.0.0 では作成時の `auto_latex_notation` を引き継ぐ
  - FutureWarning は 4 種類（レイアウト、カラーバーの重複、`flag_cbar` の改名、annotate の整形）。3.6 の移行ページは annotate の節と表の行も置く。重複の警告は `heatmapf` / `tripcolor` でも同じ形で出る
  - `__init__` の Examples は上流が足したものではなく v3 からある例（本 spec が書き直す）。`*_kw` の使用例は 5 つの `set_*` の Examples にある。共通の doctest ランナーは本 spec が担当する docstring をすべて対象に含む
  - ドキュメントのビルドの環境: `fairchem312`（sphinx 9.1.0、myst-nb 1.4.0、sphinx-book-theme 1.2.0、jupyter-sphinx あり）。カーネル `python3` は `py312` の python で動く。`PYTHONPATH=$PWD/src` を付けて、CI と同じくリポジトリの中で `sphinx-apidoc -o ./docs_src` → `sphinx-build ./docs_src <一時ディレクトリ>` を実行する（`docs_src` をコピーするとチュートリアルのシンボリックリンクが切れる）。今のビルドは警告 0 件。生成物 `docs_src/modules.rst`・`docs_src/ternary_diagram.rst` は確認後に消す（1.2 で `.gitignore` に足すまで）
  - チュートリアルの再実行の環境: `conductivity-prediction-py312`（pandas、`element_recognition`、ipykernel、matplotlib 3.11.2）がある。7.1 は保留にせず実行できる見込み
  - 上流の docstring の書き方の混在（heatmaps からの申し送り）は、揃える方針に決めた。上流の 4 メソッドの型の行と `**kwargs` の項目名だけを揃えるタスク 2.6 を足した（文面は変えない）

- 上流からの申し送り（heatmaps の最終検証、2026-11-10）:
  - 上流が所有する docstring（`fill` / `text` / `tripcolor` / `heatmapf`）は、kwargs の項目名が `kwargs : parameter of ...`、型の行が `ArrayLike | shape = (n, 3)` や `Number or None` のままである。本 spec が既存メソッドを `**kwargs`・`array-like of shape (n, 3)`・`float` に揃えると書き方が混在するので、混在を許すか、上流の docstring も揃えるか（担当表の見直し）を 1.1 で決める
  - HeatmapsPage の「Choosing a colormap」で `norm` を使う例には、`z_min` / `z_max`（`vmin` / `vmax`）と同時に渡すと matplotlib が ValueError を出すことを添える（`tripcolor` / `heatmapf` の docstring には書いてある）
  - `tripcolor` の `z` にマスク付き配列を渡すと、マスクした点は NaN と同じく塗られない（heatmaps の最終検証で揃えた）

- 1.2: `nb_execution_in_temp` を有効にすると、ビルドしたディレクトリの直下に `jupyter_execute/` ができる（`.gitignore` 済み）。ビルドの確認で `-D autoclass_content=class` にすると `materials` などの説明が消えることで、`autoclass_content="both"` の効果を確かめた
- 2.1: `fig` の型注釈は `Figure` だが、subfigure の Axes では `SubFigure` を返す（docstring の Returns は両方を書いた。注釈の修正は typing-cleanup の候補）。`__init__` の例の期待出力に str のリストの repr（頂点ラベルの文字列）があるが、版によらず安定しているので許す。2.5 で repr の行を機械的に調べるなら、この形を許す判定にする
- 2.2: `contour` は既定で `cmap="rainbow"` を入れるので、`colors` を渡すときは `cmap=None` も要る（`**kwargs` の項目に書いた）。`scatter` / `contour` は ValueError を送出するが、担当表に Raises 節がないので各項目の本文に書いた。上流の `tripcolor` / `heatmapf` は Raises 節を持つので、揃えるかどうかを 6.2 のレビューで判断する
- 2.3: `TernaryDiagram.colorbar` は既定で `orientation="vertical"` を渡すので、`location="bottom"` / `"top"` だけを渡すと matplotlib が TypeError を出す（横向きは `orientation="horizontal"` も要る。docstring に書いた）。`location` から向きを決める改善は本 spec の範囲外（コードを変えない）なので、今後の課題として残す
- 3.1: `myst_heading_anchors` が無効（`conf.py` は変えない）なので、ページ内の見出しへのリンクには明示のターゲット（`(getting-started-first-diagram)=` のように、ページ名を接頭辞にした名前）を置く。他のページも同じ方法にする
