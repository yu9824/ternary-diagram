# Research & Design Decisions

## Summary
- **Feature**: `user-guide-docs`
- **Discovery Scope**: Extension（既存のドキュメント基盤 Sphinx + MyST-NB + sphinx-book-theme の上にページと設定を足す。ライブラリの挙動は変えない）
- **Key Findings**:
  - 今の API リファレンスには `TernaryDiagram.__init__` の docstring（`materials`・`ax`・`auto_latex_notation`）が表示されていない。クラスに docstring がなく、autodoc の既定 `autoclass_content = "class"` がクラスの docstring だけを使うため。上流が `tight_layout` と `*_kw` を `__init__` の docstring に足しても、このままでは表示されない
  - MyST-NB は、テキスト形式の MyST Markdown ノートブックだけをビルド時に実行し、チュートリアル（保存済みの出力を持つ `.ipynb`）は実行しない構成にできる。`nb_output_stderr = "warn"` にすると、ページのコード例が FutureWarning を出したときに Sphinx の警告になり、「警告 0 件」の確認で検出できる（実験で確認）
  - 今の v3.2 系では、`layout="constrained"` の図に `z` 付きの描画をすると、描画後の `fig.tight_layout()` が `RuntimeError` になる。`plot-side-effects` の実装後は、レイアウトエンジンのある図では調整しないので解消する。ドキュメントで推奨する書き方（constrained の図）は `plot-side-effects` の実装が前提になる

## Research Log

### 今のドキュメントのビルド結果（基準）
- **Context**: 要件 13.1（警告 0 件）と 13.2（広告スクリプト）の基準を知る
- **Sources Consulted**: `.github/workflows/docs.yml` と同じ手順（`sphinx-apidoc -f -o ./docs_src ./src/ternary_diagram --module-first` → `sphinx-build -b html ./docs_src <tmp>`）を、既存の conda 環境（sphinx 9.1.0、myst-nb 1.4.0、sphinx-book-theme 1.2.0、matplotlib 3.10.8、numpy 2.4.2）でスクラッチパッドへ出力して実行。生成された `docs_src/modules.rst` と `docs_src/ternary_diagram.rst` は削除済み
- **Findings**:
  - 警告 0 件でビルドが完了する。全ページのフッターに `adsbygoogle` のスクリプトがある
  - API リファレンス（`ternary_diagram.html`）はクラスのシグネチャとメソッドだけで、作成時の引数の説明がない
  - 各メソッドの docstring に、`vector : ArrayLike | shape = (n, 3)` の行の重複、`semi-clockwise`（実際は上から反時計回り）、`, by default None` だけの行、`contour` の `z` の説明がない、`fill` の項目がない、などの不備がある
  - `ternary_diagram.utils` の既存関数も API リファレンスに表示されるが、説明は「check ax」「ratio」程度
- **Implications**: `autoclass_content = "both"` を設定する（要件 1.8）。docstring の不備の一覧は design の Docstring Contract に反映する。`utils` の既存関数は当初どの spec も担当していなかったが、cross-spec review で本 spec の担当になった（下の「cross-spec review の反映」、要件 1.10）

### MyST-NB によるビルド時の実行
- **Context**: 使い方ページの図を公開する版の結果にし（9.3）、例が壊れたらビルドを止める（9.4）方法を決める
- **Sources Consulted**: myst-nb 1.4.0 の設定定義（`myst_nb/core/config.py`）、スクラッチパッドでの試作ビルド（`docs_src` を複製し、MyST Markdown ノートブックのページを 1 つ追加）
- **Findings**:
  - `nb_execution_mode = "force"` と `nb_execution_excludepatterns = ["tutorials/*"]` で、追加したページだけが実行され、チュートリアルは保存済みの出力のまま表示される
  - `nb_execution_raise_on_error = True` で、セルの例外がビルドの失敗（終了コード 2）になる
  - `nb_output_stderr = "warn"` で、セルが FutureWarning を出すと `WARNING: stderr was found in the cell outputs` になる
  - `nb_execution_in_temp = True` で、実行時の作業ディレクトリが一時ディレクトリになる（`savefig` がリポジトリにファイルを作らない）。`force` モードでは `.jupyter_cache` が出力先に作られない
  - セルのメタデータ `:mystnb:` → `image: alt:` で、出力画像に `alt` 属性が付く
  - 実行用のカーネルは myst-nb の依存（`ipykernel`）に含まれるので、`pip install ".[docs]"` だけで CI でも実行できる。カーネルは親プロセスの環境変数（`PYTHONPATH`）を引き継ぐ
  - `autoclass_content = "both"` で、クラスの docstring の後に `__init__` の docstring（Parameters、Attributes、Examples）が表示される。クラスの Notes は Parameters より前に表示される。`{py:meth}` による使い方ページから API リファレンスへのリンクと、docstring の See Also は警告なしで解決される
  - 今のチュートリアルの `.ipynb` に stderr の保存済み出力はない（`nb_output_stderr = "warn"` を全体に設定しても警告にならない）
- **Implications**: 使い方ページはテキスト形式の MyST Markdown ノートブックにし、ビルド時に実行する。チュートリアルは実行しない

### 推奨する図の作り方と今の版の不具合
- **Context**: ドキュメントのコード例を FutureWarning なしにする書き方を決める（9.2）
- **Findings**:
  - `plot-side-effects` の決定表では、レイアウトエンジンのある図（`layout="constrained"` など）は v3.x でも v4.0.0 でも「調整しない・警告しない」。`tight_layout` を指定しない既定のままでも警告は出ない
  - 試作で、今の実装（`plot-side-effects` 適用前）のまま constrained の図に `scatter(z=...)` を描くと、`RuntimeError: Colorbar layout of new layout engine not compatible with old engine` になった
- **Implications**: 推奨の書き方は `fig, ax = plt.subplots(layout="constrained")` + `TernaryDiagram(..., ax=ax)`。実装は上流 4 spec のマージ後に行う

### 上流 spec の公開 API（ドキュメントに書く名前）
- **Context**: 使い方ページと移行ページの名前を上流の design に一致させる
- **Sources Consulted**: `.kiro/specs/{plot-side-effects,diagram-customization,region-plots,heatmaps}/design.md` と `tasks.md`
- **Findings**:
  - `plot-side-effects`: `TernaryDiagram(..., *, tight_layout=None)`（`None` / `True` / `False`）。`scatter(..., colorbar=None)` と `contour(..., colorbar=None)` は 6 番目の位置引数。`flag_cbar` は `**kwargs` で受け、改名の FutureWarning。両方指定は `ValueError`。v4.0.0 の既定は `tight_layout=False` 相当と「すでにカラーバーがある三角図には自動追加しない」。警告文は `format_default_change`（current → `In ternary-diagram 4.0.0, ...` → `To keep the current behavior, ...` → `To adopt the new behavior now, ...`）。example ノートブックの書き換えは本 spec に委ねられている（research.md 147 行目）
  - `diagram-customization`: キーワード専用の `border_kw` / `grid_kw` / `tick_kw` / `axis_label_kw` / `vertex_label_kw`、メソッド `set_border` / `set_grid` / `set_ticks` / `set_axis_labels` / `set_vertex_labels`、取り出し口 `border_lines_` / `grid_lines_` / `tick_labels_` / `axis_labels_` / `vertex_labels_`。`set_grid(step=)`、`set_ticks(step=, fmt=, endpoints=)`（`fmt` は `"percent"` / `"fraction"` / 書式文字列 / 関数）、`set_axis_labels(labels, pad=)`、`set_vertex_labels(labels, offsets=)`、全部品に `visible`。名前付きの項目の `None` は直前の設定を引き継ぐ。成分 1 番目の目盛りは右辺、2 番目は左辺、3 番目は底辺で、値は反時計回りに増える
  - `region-plots`: `fill(vector, **kwargs) -> List[Polygon]`（長さ 1）、`text(text, vector, *, auto_latex_notation=True, **kwargs) -> Text`。`DEFAULT_ZORDER_FILL = 0.5`、`DEFAULT_ZORDER_TEXT = 4`
  - `heatmaps`: `tripcolor(vector, z, *, z_min=None, z_max=None, shading="flat", colorbar=None, **kwargs)`、`heatmapf(func, *, scale=50, z_min=None, z_max=None, shading="flat", colorbar=None, **kwargs)`、`utils.get_triangular_lattice(scale)`。`flag_cbar` は `TypeError`。`DEFAULT_ZORDER_HEATMAP = -1`
  - 重なり順: heatmap -1 < contour 0 < fill 0.5 < 土台の線 1 < plot 2 < scatter 3（annotate と土台の文字は matplotlib の既定 3）< text 4。上流どうしで矛盾はない
- **Implications**: design の「上流 API の名前の一覧」にまとめ、実装の最初にコードと照合する

### 上流 spec どうしの食い違いと未決事項
- **Context**: 依頼で「設計どうしが食い違う場合は黙って選ばず記録する」とされている
- **Findings**:
  - 名前の食い違いはない
  - 呼び出し方の違い（意図的）: `scatter` / `contour` の `z_min` / `z_max` は位置引数でも渡せるが、`tripcolor` / `heatmapf` ではキーワード専用。`flag_cbar` は `scatter` / `contour` では FutureWarning 付きで受け付け、`tripcolor` / `heatmapf` では `TypeError`。ドキュメントでは違いとして説明する
  - `heatmaps` の Open Question: カラーバー重複の警告文（`plot-side-effects` の所有）は「because `z` was given」と書くが、`heatmapf` には `z` がない。→ 解決済み: `plot-side-effects` が `z` に依存しない文面に一般化した（下の「cross-spec review の反映」）
  - `region-plots` の Open Question: `annotate` の整形の切り替え引数（direct implementation 候補の annotate-plain-text）の名前が未確定。→ 一部解決: roadmap で `text` は `auto_latex_notation=None` で作成時の設定を引き継ぐと確定。`annotate` の規則と引数名は annotate-plain-text が決め、本 spec より先にマージされる
  - `plot-side-effects` の Open Question: v4.0.0 のカラーバーの既定（「まだなければ追加」を選択）と `flag_cbar` の削除時期（4.0.0 予定）
  - `TernaryDiagram.__init__` のキーワード専用引数の並びと docstring の順序は、`plot-side-effects` と `diagram-customization` のうち後から入る側が合わせることになっている（名前の食い違いではない）。→ 解決済み: roadmap の横断の取り決めで最終形が確定した
  - 等高線図の `contour(fill=...)` 引数と `region-plots` の `fill` メソッドは同じ語で意味が違う
- **Implications**: design の Open Questions に記録し、ページ内で違いを明示する（要件 5.6、8.6）

### cross-spec review の反映（2026-10-22）
- **Context**: 5 つの spec の横断レビューで決まった取り決め（steering の roadmap.md「Implementation Order」「横断の取り決め」、annotate-plain-text の項目、tech.md「Docstring Examples」）に合わせて、承認済みの spec を部分的に直す
- **Sources Consulted**: `.kiro/steering/roadmap.md`、`.kiro/steering/tech.md`、`plot-side-effects` の修正の結果（コーディネーターからの連絡）
- **Findings**:
  - `TernaryDiagram.__init__` の Examples 節は本 spec だけが持つ。上流は `__init__` に Parameters の項目（`tight_layout`、`*_kw`）だけを書き、`*_kw` の使用例は対応する `set_*` の docstring（`border_kw` → `set_border`、`grid_kw` → `set_grid`、`tick_kw` → `set_ticks`、`axis_label_kw` → `set_axis_labels`、`vertex_label_kw` → `set_vertex_labels`）に書く。以前の「上流の例の図の作り方の行だけをそろえる」方針は要件 1.9 と矛盾していたので削除した
  - docstring の例は `plot-side-effects` が作る共通の doctest ランナー `tests/test_doctests.py` が、公開 API について一時ディレクトリで FutureWarning をエラーとして実行する。本 spec の docstring の例の実行テスト（旧 `test_owned_docstring_examples_run`）は廃止し、`tests/test_docs_examples.py` は README とトップページの例だけを扱う。例の有無と不備の静的な確認は `tests/test_owned_docstrings.py` に分けた
  - ランナーは今の `__init__` の例（repr を表示し、`ax=` を渡さず、`savefig` を呼ぶ）を `xfail(strict=True)` にしている。本 spec が Examples 節を書き直して通るようにしたら、その印だけを外す（`tests/test_doctests.py` への唯一の変更）
  - 担当の確定: `TernaryDiagram.colorbar()` メソッドの docstring は本 spec、`scatter` / `contour` の Parameters の `colorbar`・`flag_cbar` の項目は `plot-side-effects`。上流が `utils` に足す公開関数（`check_optional_bool`・`check_bool`、配置の関数と `TickFormat`、`get_triangular_lattice`）は足す spec の担当。`utils` の既存 5 関数（`check_ax`・`check_2d_vector`・`check_1d_vector`・`three2two`・`get_label`）は本 spec が仕上げる（要件 1.10 を追加）。annotate-plain-text が `annotate` / `scatter` / `get_label` に足す切り替え引数の項目は annotate-plain-text の担当
  - annotate-plain-text は本 spec の上流で、先にマージされる。作成時の `auto_latex_notation` は頂点ラベルを決め、`text(auto_latex_notation=None)` が引き継ぐ。`annotate` / `scatter(annotations=...)` は annotate-plain-text の規則に従う。v3.x で表示を変える場合は FutureWarning を出すので、その場合は移行ページの対象になる（要件 8.1 に条件付きで追記）
  - 作成時の引数の最終形は `(materials, ax=None, auto_latex_notation=True, *, tight_layout=None, border_kw=None, grid_kw=None, tick_kw=None, axis_label_kw=None, vertex_label_kw=None)`
  - カラーバー重複の警告文の最終形は ``"`{func}` added another colorbar to this diagram, which already has one, because `colorbar` was not specified."``。移行ページは引き続きビルド時に実際の文面を捕まえて表示する
- **Implications**: design の担当表、DocExamplesTest と DocstringContractTest、Notebook Contract（再実行を独立させ、保留の条件を持たせる）、tasks の `_Boundary:_` をファイルとシンボルの単位で直した

### cross-spec review の反映（round 2、2026-10-22）
- **Context**: 横断レビューの 2 回目の指摘 N1。`tests/test_owned_docstrings.py` が公開 docstring の全体に対して `, by default` だけの行と `semi-clockwise` を確かめる設計で、本 spec が書き換えられない上流の項目まで対象にしていた。tasks 2.5 の完了条件（テストが通る、かつ上流の失敗は記録する）が矛盾していた
- **Sources Consulted**: `.kiro/steering/tech.md`「Docstring Examples」（各 `Parameters` の項目に意味を書く文を置き、既定値は `, by default X` と添える。`, by default None` だけの項目を書かない。例は自分の import の行から始める、というプロジェクト全体の規約が追加された）
- **Findings**:
  - 静的な確認の範囲を、担当表で本 spec のものとした Examples 節（11 か所）と Parameters・Attributes の項目（`OWNED_ENTRIES`）に限る。上流が担当する項目と節（`tight_layout`・`*_kw`、`colorbar`・`flag_cbar`、annotate-plain-text の項目、クラスの Notes 節）は読まないので、テストの結果は上流の内容に左右されない
  - 上流の項目は tech.md の規約に担当 spec が自分で従う。規約違反に気づいた場合は、本 spec では書き換えず、本 spec のテストにも含めず、担当 spec の不具合として記録する
  - Docstring Contract の既定値の書き方を tech.md に合わせ、「意味を書く文 + `, by default X`」にした（以前の「If None (default), ...」の形は tech.md と食い違っていた）。既定値のときの挙動が値だけでわからない場合は説明文に書く（要件 1.1）。例は自分の import の行から始めることも明記した
- **Implications**: design の DocstringContractTest（`OWNED_EXAMPLES`・`OWNED_ENTRIES`・`test_owned_entries_have_descriptions`）、Docstring Contract、Error Handling、Testing Strategy、Revalidation Triggers、traceability（1.1 に DocstringContractTest を追加）と、tasks 2.1・2.2・2.4・2.5・6.2 を直した。要件は変えていない

### example ノートブックの現状
- **Context**: 要件 11 の対象を決める
- **Findings**:
  - `flag_cbar` を使うのは `example/contour/example_contour.ipynb` の 2 か所だけ
  - 6 つのノートブックはすべて、レイアウトエンジンのない図に描くので、`plot-side-effects` の実装後に再実行するとレイアウトの FutureWarning が出る。`example_mono_scatter.ipynb` は利用者側でも `fig.tight_layout()` を呼んでいる
  - `example_scatter_with_annotations.ipynb` は外部パッケージ `element_recognition` を使う。既存の conda 環境 `conductivity-prediction-py312` などに入っている（インストールは不要）
  - `example_on_readme.ipynb` が README の画像 `example/example_on_readme/figure.png` を、`example_contour.ipynb` が README とトップページの画像 `example/contour/example_contour.png` を作る。README は GitHub の raw URL で参照する
  - テストは `example/*/example_*.csv` をリポジトリ内のパスで読む
- **Implications**: 6 つすべてを推奨の書き方に直して再実行する。データファイルと画像のファイル名は変えない

### jupytext の設定との関係
- **Context**: `jupytext.toml` の `formats = "ipynb,py:percent"` が MyST Markdown のページに影響するか
- **Findings**: jupytext の設定を読み込んで `default_formats("docs_src/user_guide/p.md")` を確かめると `None`（`.md` には対の設定が適用されない）
- **Implications**: `jupytext.toml` は変えない。ページはテキストエディタで編集でき、jupytext の MyST 形式のヘッダーを付ければ Jupyter でも開ける

### 図の見せ方（dataviz スキル）
- **Context**: 使い方ページの図と、カラーマップの選び方の説明（要件 6.6）、代替テキスト（要件 2.5）
- **Sources Consulted**: dataviz スキルの原則（大小の値は 1 色相で明るさが単調に変わる順序、正負の値は 2 色相と無彩色の中央、虹色を避ける、2 系列以上は凡例を付け色だけで区別しない）
- **Findings**: ライブラリの既定のカラーマップは `rainbow`（`DEFAULT_CMAP`）で、変更は本 spec の範囲外
- **Implications**: 使い方ページでは既定値を正直に示したうえで、明るさが単調なカラーマップ（`viridis` など）と、正負の値には中央が無彩色の発散型カラーマップを勧める。相図の例は色に加えて凡例と文字のラベルで領域を示す。図には代替テキストを付ける

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| A. MyST Markdown ノートブックをビルド時に実行 | `.md` に `{code-cell}` を書き、MyST-NB が実行して出力を埋め込む | テキストだけで差分が読める。出力は常に公開する版の結果。例が壊れるとビルドが止まる。FutureWarning を警告として検出できる | ビルドにカーネルが要る（`docs` extras に含まれる）。ビルド時間が数秒延びる | 採用 |
| B. `.ipynb` を jupytext で py:percent と対にし、保存済みの出力を表示 | 今のチュートリアルと同じ形式 | 実行環境が要らない。既存の形式と同じ | 出力が古くなる。JSON の差分が読みにくい。2 ファイルを同期する手間 | 不採用（チュートリアルは現状のまま） |
| C. 実行しない Markdown と画像ファイル | コードは静的なコードブロック、図は手で保存した PNG | 依存が最小 | 図とコードが食い違っても気づけない。画像がリポジトリに増える | 不採用 |

## Design Decisions

### Decision: 使い方ページの形式と実行方式
- **Context**: brief の設計課題「ノートブックか Markdown か、ノートブックを CI で実行するか」。要件 9.3、9.4、13.4
- **Alternatives Considered**: 上の表の A / B / C
- **Selected Approach**: A。全体の `nb_execution_mode` を `"force"` にし、`nb_execution_excludepatterns = ["tutorials/*"]` でチュートリアルを除く。`nb_execution_raise_on_error = True`、`nb_execution_in_temp = True`、`nb_output_stderr = "warn"`
- **Rationale**: 新しいページは自動で実行対象になり、新しいチュートリアルは置き場所だけで除外される。設定が 1 か所にまとまる
- **Trade-offs**: タグでのドキュメントのデプロイが、例の失敗で止まるようになる（壊れたページを公開しないための意図した変更）
- **Follow-up**: ビルド時間と、CI の新しい環境でフォントキャッシュの作成メッセージが stderr に出ないことを確認する（`conf.py` が `ternary_diagram` を import する時点でキャッシュが作られるので、カーネルでは出ない見込み）

### Decision: 使い方ページとチュートリアルの役割分担
- **Context**: brief の設計課題「サンプルノートブック（`example/`）と使い方ページの役割分担」
- **Selected Approach**: 使い方ページは目的別の説明で、合成データ（numpy の乱数や式）だけを使い、ビルド時に実行する。チュートリアルは実データ（`example/` の CSV）を使った通しの例で、保存済みの出力を表示し、README の画像を作る。チュートリアルの一覧と使い方ページの一覧の両方に 1 行の説明を付け、相互にリンクする
- **Rationale**: 使い方ページを pandas や外部パッケージなしで実行でき（要件 9.5、13.4）、チュートリアルの既存の URL とテストのデータパスを保てる（要件 10.3、11.4）

### Decision: 推奨する図の作り方
- **Context**: 要件 9.2（FutureWarning なし）、11.2
- **Alternatives Considered**:
  1. `TernaryDiagram(..., tight_layout=True)` を明示する（今の見た目を保つ）
  2. `fig, ax = plt.subplots(layout="constrained")` に描く（レイアウトエンジンに任せる）
- **Selected Approach**: 2 をすべてのコード例の既定にする。レイアウトのページでは 3 通りの `tight_layout` を説明し、移行ページでは移行前の書き方も示す
- **Rationale**: v3.x と v4.0.0 で同じ結果になり、カラーバー・複数パネル・subfigure でも崩れない。ternary-diagram 固有の引数を覚えなくてよい
- **Trade-offs**: チュートリアルの出力画像（README の画像を含む）の見た目が少し変わる。今の v3.2 系では動かない（実装は上流のマージ後）

### Decision: 作成時の引数を API リファレンスに表示する
- **Context**: 要件 1.8
- **Alternatives Considered**:
  1. `autoclass_content = "both"`
  2. `napoleon_include_init_with_doc = True`（`__init__` を別のメンバーとして表示）
  3. 引数の説明をクラスの docstring に移す
- **Selected Approach**: 1
- **Rationale**: 上流 2 spec が `__init__` の docstring に引数を足す設計なので、docstring の置き場所を変えずに表示できる。`diagram-customization` のクラスの Notes も表示される
- **Trade-offs**: クラスの Notes が Parameters より前に表示される

### Decision: docstring の使用例と README の例を自動で実行する
- **Context**: 要件 1.5、1.10、9.1、9.2、10.5、12.5
- **Selected Approach**（cross-spec review で改訂）: docstring の例は共通の doctest ランナー `tests/test_doctests.py`（`plot-side-effects` の所有）に任せ、本 spec は自分のランナーを作らない。ランナーが `__init__` の例に付けている xfail の印は、本 spec が例を書き直して通るようにした後に外す。`tests/test_docs_examples.py` は README とトップページの最初の Python のコードブロックが同じであることを確かめ、作業ディレクトリを一時ディレクトリにして FutureWarning をエラーとして実行する（docstring は扱わない）。担当 docstring の例の有無と不備は `tests/test_owned_docstrings.py` で静的に確かめる（round 2 で、担当表の本 spec の項目と節だけに範囲を限った）
- **Rationale**: 公開 API の例の実行を 1 つのランナーにまとめ、spec ごとに同じ仕組みを重ねない（tech.md「Docstring Examples」）。README とトップページの例はランナーにも Sphinx にも実行されないので、本 spec が確かめる
- **Trade-offs**: README の変更だけでは CI のテストが走らない（paths-filter に README.md がない）。README を変える PR ではテストを手元で実行する。上流の docstring の例がランナーで失敗した場合、本 spec では直せない（担当 spec の不具合として記録する）

### Decision: docstring の担当範囲
- **Context**: 上流 spec との二重管理を避ける（要件 1.9）
- **Selected Approach**（cross-spec review で改訂）: 項目（引数）と節の単位で担当を決める（design の担当表）。同じ節（Notes）に複数の spec が書く場合は段落単位で追記し、他の spec の段落は書き換えない。`__init__` の Examples 節は本 spec だけが持ち、上流は `__init__` に Parameters の項目だけを書く。`*_kw` の使用例は対応する `set_*` の docstring にあるので、`__init__` の Examples には書かない
- **Rationale**: brief の「全体の書き方をそろえる」と、依頼の「上流が書く docstring を二重に持たない」（要件 1.9）を両立する

## Synthesis Outcomes
- **Generalization**: 5 つの使い方ページと移行ページは、同じ「ページの規約」（ヘッダー、推奨の図の作り方、合成データ、代替テキスト、API へのリンク）に従う 1 種類の部品として扱う。docstring も 1 つの「docstring の規約」に従う
- **Build vs. Adopt**: 実行と埋め込みは MyST-NB の機能をそのまま使う（独自のスクリプトで図を作らない）。警告の検出も MyST-NB の `nb_output_stderr` を使う。docstring の例の実行は `plot-side-effects` の共通の doctest ランナーを使う（本 spec は作らない）
- **Simplification**: 使い方ページ専用の補助モジュールや共通の設定セルは作らない（各ページが自分のセルで完結する）。CI のワークフローは変えない。テーマとテンプレートは変えない

## Risks & Mitigations
- 上流の API 名が design と実装で違う — 実装の最初にコードと照合し、食い違いは担当 spec の課題として記録する。ページはビルド時に実行されるので、名前の誤りはビルドの失敗で見つかる
- 例の失敗でタグのドキュメントのデプロイが止まる — 実装時とリリース前に手元で CI と同じ手順のビルドを行う。PR でのドキュメントのビルド（CI の変更）は本 spec の範囲外とし、必要なら別に検討する
- README から新しいページへのリンクは、次の正式版のタグでドキュメントがデプロイされるまで 404 になる — CHANGELOG と同じく次のリリースと同時に有効になることを受け入れる。リンク先のパスは design で固定する
- チュートリアルの再実行に外部パッケージ（`element_recognition`、pandas、Jupyter）が要る — 既存の conda 環境を使い、パッケージはインストールしない。使える環境がなければ再実行を独立したタスク（tasks の 7.1）として保留にし、他のタスクを止めない
- 上流の docstring の使用例が共通の doctest ランナーで FutureWarning を出す、または実行できない — 本 spec では書き換えず、担当 spec の不具合として記録する

## References
- [MyST-NB: Configuration](https://myst-nb.readthedocs.io/en/latest/configuration.html) — `nb_execution_mode`、`nb_execution_excludepatterns`、`nb_output_stderr`、`nb_execution_in_temp`、`nb_execution_raise_on_error`
- [MyST-NB: Text-based notebooks](https://myst-nb.readthedocs.io/en/latest/authoring/text-notebooks.html) — MyST Markdown ノートブックのヘッダーと `{code-cell}`
- [Sphinx autodoc: autoclass_content](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autoclass_content) — クラスと `__init__` の docstring の結合
- [numpydoc docstring guide](https://numpydoc.readthedocs.io/en/latest/format.html) — 節の順序と引数の書き方
- 上流の design: `.kiro/specs/plot-side-effects/design.md`、`.kiro/specs/diagram-customization/design.md`、`.kiro/specs/region-plots/design.md`、`.kiro/specs/heatmaps/design.md`
