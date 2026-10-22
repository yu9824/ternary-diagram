# Research & Design Decisions

## Summary
- **Feature**: `plot-side-effects`
- **Discovery Scope**: Extension（既存の `TernaryDiagram` / Plotter パターンの拡張。light discovery を実施）
- **Key Findings**:
  - matplotlib 3.10.8 で、`Figure.tight_layout()` は実行後にレイアウトエンジンを `PlaceHolderLayoutEngine` に置き換える。constrained の図では "The figure layout has changed to tight" の UserWarning を出したうえで constrained が失われる。`layout="tight"` の図でも、利用者の `TightLayoutEngine` が `PlaceHolderLayoutEngine` に置き換わる
  - 警告だけでは済まない場合がある: constrained の図でカラーバーを追加した直後に `fig.tight_layout()` を呼ぶと `RuntimeError`（"Colorbar layout of new layout engine not compatible with old engine, and a colorbar has been created. Engine not changed."）になる。現行コードでは `layout="constrained"` の図への最初の `contour(z)` / `scatter(z)` がこれで失敗し、しかもエンジンは `PlaceHolderLayoutEngine` に置き換わる
  - subfigure 上の Axes では `ax.figure` が `SubFigure` を返し、`SubFigure` には `tight_layout` がない。現行コードは subfigure 上での描画のたびに `AttributeError` で失敗する（既存の不具合）
  - `Colorbar.remove()` は `mappable.colorbar = None` を設定する。「カラーバーがまだ生きているか」は `cb.mappable.colorbar is cb` で判定でき、matplotlib のバージョンに依存しない

## Research Log

### 図のレイアウトエンジンの状態と `tight_layout` の副作用
- **Context**: 要件 2（設定済みのレイアウトを尊重する）を満たすには、「利用者がレイアウトエンジンを設定している」状態と「ライブラリ自身が以前 tight_layout を呼んだ痕跡」を区別する必要がある
- **Sources Consulted**: matplotlib 3.10.8 を `/Users/yu9824/opt/miniforge3/envs/py312/bin/python` で実行して確認（scratchpad の検証スクリプト）。`matplotlib.figure.Figure.tight_layout` / `get_layout_engine` / `set_layout_engine` の実装
- **Findings**:
  - 新しい図の `get_layout_engine()` は `None`
  - `fig.tight_layout()` の後は `PlaceHolderLayoutEngine`（`set_layout_engine("none")` が以前のエンジンの互換情報だけを残す）
  - `layout="constrained"` → `ConstrainedLayoutEngine`、`layout="compressed"` → `ConstrainedLayoutEngine`、`layout="tight"` → `TightLayoutEngine`
  - rcParams `figure.autolayout=True` → `TightLayoutEngine`、`figure.constrained_layout.use=True` → `ConstrainedLayoutEngine`
  - constrained の図で `fig.tight_layout()` を呼ぶと UserWarning "The figure layout has changed to tight" が出て、エンジンが `PlaceHolderLayoutEngine` になる。現行ライブラリではこの警告の発生位置が `_api.py` 内になる
  - ただし、constrained の図にカラーバーがすでにある状態で `fig.tight_layout()` を呼ぶと、`set_layout_engine(TightLayoutEngine)` がカラーバーの配置方式の非互換を理由に `RuntimeError` を送出し、`finally` 節の `set_layout_engine("none")` でエンジンは `PlaceHolderLayoutEngine` になる。現行ライブラリで再現を確認した（2026-10-22、matplotlib 3.10.8、scratchpad の検証スクリプト）: `layout="constrained"` の図に `contour(z)` だけ、`scatter(z)` だけ、`contour(z)` → `scatter(z)` のいずれも 1 回目の描画で `RuntimeError`。`plot` を先に描いた場合はレイアウト変更の警告が出てエンジンが外れ、その後の `contour(z)` は成功する
  - `layout="constrained"` の図で `set_layout_engine("none")` を呼んだ場合も `PlaceHolderLayoutEngine` になる
  - `tight_layout` の実行で `fig.subplotpars`（left / bottom など）が既定値（0.125 / 0.11）から変わる。テストでレイアウト調整の有無を判定する観測点に使える
- **Implications**:
  - 「レイアウトエンジンなし」= `None` または `PlaceHolderLayoutEngine`。それ以外のエンジンは利用者（または rcParams）の設定として尊重する
  - ライブラリ自身の 2 回目以降の描画でも、`PlaceHolderLayoutEngine` を「なし」と扱うので、v3.x の挙動（毎回 tight）が続く（要件 2.3）
  - エンジンのある図で `tight_layout` を呼ばなければ、上の `RuntimeError` も起きない。constrained の図で `contour(z)` → `scatter(z)` が例外なく完了しエンジンが変わらないことを、要件 2.6 と明示的な結合テストで固定する。CHANGELOG では Bug fixes に記載する

### matplotlib のバージョン差異
- **Context**: steering は「matplotlib の古いバージョンでも動かす」「`Figure.get_layout_engine` は 3.6+」と定めている
- **Sources Consulted**: matplotlib の API 変更履歴（3.4 で `SubFigure` 追加、3.6 で `matplotlib.layout_engine` と `Figure.get_layout_engine` / `set_layout_engine` 追加）。3.10.8 で `Figure.get_constrained_layout` / `get_tight_layout` がまだ存在することを確認
- **Findings**:
  - 3.6 未満では `Figure.get_constrained_layout()` と `Figure.get_tight_layout()` でレイアウト設定の有無を判定できる。3.6 未満の `fig.tight_layout()` は一度きりの調整で、`get_tight_layout()` のフラグは立たない
  - `SubFigure` は `Figure` のサブクラスではない（両者とも `FigureBase` のサブクラス）。`isinstance(fig, matplotlib.figure.Figure)` で subfigure を見分けられる。3.4 未満には `SubFigure` 自体がない
- **Implications**: モジュール冒頭で `(3, 6)` 以上かを判定する定数を置き（tech.md の既存パターンに合わせる）、判定関数の中で分岐する。3.6 未満の分岐は、3.10 上で定数を差し替えるテストで検証する

### `SubFigure` 上での描画
- **Context**: brief は subfigure のレイアウトも崩れると述べている
- **Findings**: 3.10.8 では `ax.figure` が `SubFigure` を返し、`SubFigure` は `tight_layout` を持たない。現行コードは `AttributeError: 'SubFigure' object has no attribute 'tight_layout'` で失敗する。`SubFigure.get_layout_engine()` は親の図のエンジンを返す。`SubFigure.colorbar` は使える
- **Implications**: subfigure ではレイアウト調整を常に行わない（`UNSUPPORTED` 状態）。現行は失敗していたので、v4.0.0 でも結果は変わらず、既定値変更の警告も不要

### カラーバーの存否の判定
- **Context**: 要件 4.1 / 4.3（TernaryDiagram を通じて追加したカラーバーのうち、削除されていないもの）
- **Findings**:
  - `fig.colorbar(mappable, ...)` は `mappable.colorbar` に `Colorbar` を設定する。`ContourSet` でも同じ
  - `Colorbar.remove()` は `mappable.colorbar = None` にする（3.10.8 のソースで確認）
  - `ax.collections` を走査する方法は、matplotlib 3.8 未満で `ContourSet` が `ax.collections` に入らないため使えない
- **Implications**: TernaryDiagram ごとに作成した `Colorbar` を登録し、`cb.mappable.colorbar is cb` のものだけを「生きている」と数える

### 警告の発生位置（stacklevel）
- **Context**: 要件 6.7。呼び出し経路は「利用者 → `TernaryDiagram.scatter` → `_ScatterPlotter.__init__` → `_BasePlotter._post_draw` → ヘルパー」と深く、メソッドごとに段数が違う
- **Sources Consulted**: matplotlib の `_api.warn_external`（private API なので依存しない）。Python 3.12 の `warnings.warn(skip_file_prefixes=...)`（3.9 では使えない）
- **Findings**: scratchpad の試作で、`sys._getframe` からフレームを遡り、`__name__` が `ternary_diagram` パッケージに属さない最初のフレームの段数を `stacklevel` に渡すと、利用者のコードの行が報告されることを確認した（試作では 1 段ずれる誤りがあり、修正後に正しい行を報告した）
- **Implications**: 固定の `stacklevel` ではなく、パッケージ外の最初のフレームを探す `warn_external` を共通ヘルパーに置く。テストは `tests/` 配下でパッケージ外なので、警告の `filename` がテストファイルになることを assert できる

### 共通 doctest ランナーと既存の使用例
- **Context**: roadmap の「横断の取り決め」と tech.md「Docstring Examples」で、本 spec が共通 doctest ランナー `tests/test_doctests.py` を作ることになった。公開 API の使用例を一時ディレクトリで、FutureWarning をエラーにして実行する
- **Findings**:
  - 既存の `>>>` の例は `utils`（`check_1d_vector`、`three2two`、`get_label`）、`TernaryDiagram.__init__` の Examples 節、private なメソッド `_BasePlotter._set_default_params` / `_merge_alias` にある。CI の `pytest -xs .` は今は doctest を実行していない
  - `__init__` の Examples 節は `ax` を渡さず、`td.scatter(...)` などの戻り値の repr（メモリ番地を含む）を期待出力なしで出し、`savefig("figure.png")` で書き出す。doctest としては通らず、本 spec の適用後はレイアウトの FutureWarning もエラーになる
  - private なメソッドの例は `self` を前提にしており、そのままでは実行できない
  - `doctest.DocTestFinder` は名前が `_` で始まるものも収集するので、公開 API に限るには名前で絞る必要がある
- **Implications**:
  - ランナーは `ternary_diagram.__all__` の名前と公開モジュールの公開の関数・クラスだけを収集し、private なモジュールと `_` で始まるメソッド（`__init__` を除く）を除く。後続の spec が足す公開モジュールも自動で対象になる
  - `__init__` の Examples 節は `user-guide-docs` の担当なので本 spec では書き直さない。ランナーはその 1 件だけを `xfail(strict=True)` にし、書き直された時点で XPASS の失敗として一覧からの削除を促す
  - private なメソッドの `>>>` 行は、`_BasePlotter` を変更するタスク（3.2）で本文の説明に書き換える
  - 他の spec の設計には、自前の doctest の実行（`doctest.testmod` など）を足すものがある。共通ランナーに一本化するよう、cross-spec review の結果として各 spec で調整する

### 既存コードと利用箇所
- **Context**: 移行の影響範囲
- **Findings**:
  - 4 つの Plotter がそれぞれ `self.fig.tight_layout()` を呼ぶ（`_api.py`）
  - `flag_cbar` はテスト（`test_scatter.py`、`test_contour.py`、`test_ternary_diagram.py`）と example ノートブック（`example/contour/example_contour.ipynb`）で使われている。README には出てこない
  - `example/mono_scatter/example_mono_scatter.ipynb` は利用者側で `fig.tight_layout()` を呼んでいる
  - `_AnnotatePlotter` は `self.kwargs` ではなくローカルの `kwargs` を `ax.annotate` に渡している。Plotter に新しい引数を足すときは、`**kwargs` に紛れ込ませず明示的に受ける必要がある
  - pytest の設定（`filterwarnings`）はない
- **Implications**: 既存テストの `flag_cbar` を `colorbar` に移し、別名のテストを別に書く。`td` fixture はレイアウト設定を明示して、既存テストに FutureWarning が出ないようにする。ノートブックの書き換えは `user-guide-docs` に委ねる

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| A. `_BasePlotter._post_draw` を各 Plotter の `__init__` の最後で呼ぶ | 今の `self.fig.tight_layout()` の位置を共通メソッドに置き換える | 既存の Plotter パターンをほぼ変えない。brief の「`_BasePlotter` 側の共通の仕組み」に一致 | 呼び忘れの可能性 | 採用。三角図ごとの状態（`PostDrawContext`）を必須のキーワード引数にして、配線漏れを `TypeError` で検出する |
| B. `TernaryDiagram` の各メソッドが Plotter 生成後に後処理を呼ぶ | Plotter は描くだけ | Plotter が三角図の状態を知らずに済む | brief の方針（`_BasePlotter` 側に集約）と違う。新しいメソッドごとに呼び忘れの余地が同じだけある | 不採用 |
| C. テンプレートメソッド（`_BasePlotter.__init__` が `_draw()` → 後処理を呼ぶ） | 後処理の実行を基底クラスが保証する | 呼び忘れが起きない | 4 つの Plotter の構造を大きく変える。サブクラスの引数を `super().__init__` 前に保存する必要があり読みにくい。`diagram-customization` と同時期の大きな差分になる | 不採用 |

## Design Decisions

### Decision: レイアウト設定の置き場所と名前
- **Context**: 要件 1.1、1.5。brief の「`TernaryDiagram(..., tight_layout=...)` かメソッドごとか」
- **Alternatives Considered**:
  1. `TernaryDiagram(..., tight_layout=None)` のみ（三角図単位）
  2. 各描画メソッドにも `tight_layout=` を足す
- **Selected Approach**: 1。`TernaryDiagram.__init__` のキーワード専用引数 `tight_layout: Optional[bool] = None`
- **Rationale**: レイアウトは図全体の性質で、描画ごとに変える理由が乏しい。メソッドごとにすると既存 4 つと後続 spec の全メソッドに引数が増える。呼び出しごとに制御したい利用者は `tight_layout=False` にして自分で `fig.tight_layout()` を呼べる。名前は matplotlib の `Figure.tight_layout` と同じで、何が起きるかがそのまま分かる
- **Trade-offs**: 描画途中で切り替える手段はない（作成後の setter は作らない）
- **Follow-up**（解決済み）: roadmap の「横断の取り決め」で `__init__` の最終形を `(materials, ax=None, auto_latex_notation=True, *, tight_layout=None, border_kw=None, grid_kw=None, tick_kw=None, axis_label_kw=None, vertex_label_kw=None)`、検証の順を `ax` → `materials` → `tight_layout` → `*_kw` と確定した。本 spec が先にマージし、`diagram-customization` が `*_kw` を `tight_layout` の後ろに足す

### Decision: v4.0.0 でのレイアウトの既定値
- **Context**: 要件 6.1
- **Alternatives Considered**:
  1. `tight_layout=False`（ライブラリはレイアウトに触れない）
  2. 「レイアウトエンジンがなければ tight」を v4.0.0 でも既定のまま残す
  3. 作成時に図へ `TightLayoutEngine` を設定する
- **Selected Approach**: 1
- **Rationale**: matplotlib の描画関数はレイアウトを変えないのが通例で、手動の余白調整や複数パネルを崩さない。2 は手動調整の問題と描画ごとの計算が残る。3 は利用者の図の設定を書き換える副作用で、`subplots_adjust` と衝突する
- **Trade-offs**: v4.0.0 以降、何もしない利用者は余白が広い図になる。警告文と CHANGELOG で `fig.tight_layout()` / `layout="constrained"` を案内する

### Decision: カラーバー引数の名前（`flag_cbar` → `colorbar`）
- **Context**: 要件 3.1、5.x。brief の「matplotlib らしい名前にするか」
- **Alternatives Considered**:
  1. `flag_cbar` のまま既定値を `None` に変える
  2. `colorbar: Optional[bool] = None` を新設し、`flag_cbar` を非推奨の別名にする
- **Selected Approach**: 2。`colorbar` は `flag_cbar` と同じ位置引数の位置に置き、`flag_cbar` は `**kwargs` から取り出す。`flag_cbar` の値は従来どおり真偽値として解釈し（`bool()`）、`colorbar` は `None` / 真偽値だけを受け付ける
- **Rationale**: pandas の `DataFrame.plot.scatter(colorbar=...)` と同じ名前で、`TernaryDiagram.colorbar()` とも対応が取れる。既定値の意味（未指定 = `None`）が変わるので、名前を変える機会として自然。`heatmaps` の新メソッドは最初から `colorbar` だけを持てる
- **Trade-offs**: `flag_cbar=False` と書いている利用者（すでに望ましい書き方をしている人）にも改名の FutureWarning が出る。また、6 番目の位置引数に `0` / `1` を渡していた呼び出しは `colorbar` の厳密な検証で `TypeError` になる。example・テスト・README に該当する呼び出しはなく影響は小さいので受け入れ、cross-spec review（round 2）の結果として CHANGELOG の Breaking changes に記載する（要件 7.3・8.1、タスク 4.4）。キーワードの `flag_cbar` は従来どおり `bool()` で解釈するので対象外
- **Follow-up**: `flag_cbar` の削除予定を 4.0.0 とするかは人間のレビューで確認する（Open Questions に記載）

### Decision: v4.0.0 でのカラーバーの既定値
- **Context**: 要件 6.2（すでにカラーバーがある三角図には自動で追加しない）
- **Alternatives Considered**:
  1. 自動追加しない（`colorbar=False` が既定）
  2. 三角図にまだカラーバーがないときだけ自動追加する
- **Selected Approach**: 2
- **Rationale**: 1 本目を自動で付ける便利さ（「最短で論文品質」）を残したまま、重複の問題を解消できる。v3.x で FutureWarning が出るのは重複が起きる呼び出しだけになり、`contour` を 1 回描くだけの大多数の利用者には警告が出ない
- **Trade-offs**: 「三角図の状態によって結果が変わる」暗黙の状態を持つ。判定の範囲（TernaryDiagram を通じて追加したものだけ）を docstring に書く

### Decision: FutureWarning を出す条件と頻度
- **Context**: 要件 6.3〜6.8
- **Selected Approach**:
  - 既定のままの呼び出しのうち、v4.0.0 の既定値で結果が変わるものだけで出す（レイアウト: エンジンなしの図で tight を実行したとき。カラーバー: すでにカラーバーがある三角図に自動追加したとき）
  - 既定値変更の警告は、三角図ごと・理由ごとに 1 回だけ出す（`PostDrawContext.first_time(key)`）。それ以外は Python の警告フィルタ（FutureWarning は既定で呼び出し位置ごとに 1 回）に任せる
  - 改名の警告は呼び出しごとに出し、重複の抑制は Python の警告フィルタに任せる
- **Rationale**: 必要な箇所だけを示し、ループ内の描画で同じ警告が並ぶのを避ける。三角図ごとに 1 回なので、ノートブックのセルごとに図を作る使い方でも、図ごとに 1 回は目に入る

### Decision: 共通ヘルパーを `_deprecation.py` に分ける
- **Context**: `region-plots` / `heatmaps` などの後続 spec が再利用する。`_api.py` は後続 spec も編集する
- **Selected Approach**: 依存のない葉モジュール `_deprecation.py` に、`warn_external`（パッケージ全体で利用者向けの警告を出す入口。種類は `category` で選び、既定は FutureWarning。UserWarning なども渡せる）、既定値変更と改名の文面の組み立て（`format_default_change` / `format_renamed_parameter`）、改名引数の解決（`resolve_renamed_parameter`）、`UNSET` 番兵、`FUTURE_VERSION` を置く。文面の組み立てと発生を 1 つにまとめた関数は作らない（呼び出し側が `warn_external(format_default_change(...))` と書く）。描画後処理の方針（状態判定・決定表・状態保持）は `_post_draw.py` に置く
- **Rationale**: 純粋関数として単体テストでき、`_api.py` の差分を小さくして後続 spec との衝突を減らす。発生位置の規則（利用者のコードの行）は FutureWarning に限らず利用者向けの警告すべてに必要なので、`warn_external` を FutureWarning 専用にせず、パッケージ全体の入口にした（roadmap の「横断の取り決め」）
- **Build vs Adopt**: matplotlib の `_api.warn_external` / `_api.rename_parameter` は private API で、互換性の保証がない。Python 3.12 の `skip_file_prefixes` は 3.9 で使えない。いずれも採らず、30 行程度の自前実装にする

### Decision: 判定を純粋関数に分ける
- **Context**: user の CLAUDE.md（関数型アプローチ、副作用の最小化）と、決定表を v4.0.0 で切り替えやすくするため
- **Selected Approach**: `get_layout_state(fig)`（図の読み取りのみ）、`decide_layout(setting, state)`、`decide_colorbar(requested, has_mappable, has_existing)` を純粋関数にし、副作用（カラーバー追加、`tight_layout`、警告）は `_BasePlotter._post_draw` だけで実行する
- **Rationale**: 9 通りの組み合わせを matplotlib なしで網羅テストできる。v4.0.0 の切り替えは決定表の 2 か所の変更で済む

### Decision: カラーバー重複の警告文を `z` に依存させない
- **Context**: cross-spec review。`heatmaps` の `heatmapf` は `z` 引数を持たないが、値で色付けした描画として同じ決定表と警告文を使う
- **Selected Approach**: `colorbar_warning_message(func)` の current を `` "`{func}` added another colorbar to this diagram, which already has one, because `colorbar` was not specified." `` にする
- **Rationale**: 「`z` が渡されたので」という説明は `heatmapf` では誤りになる。重複の原因（既存のカラーバーがあり、`colorbar` を指定していない）だけを述べれば、どの描画メソッドにも当てはまる
- **Follow-up**: 文面を変えたら `heatmaps` と `user-guide-docs`（移行ページが文面を示す）を見直す（design の Revalidation Triggers）

### Decision: 真偽値の検証 `utils.check_bool` を本 spec で足す
- **Context**: cross-spec review。`diagram-customization` が `None` を受け付けない真偽値の引数（`visible`、`endpoints`）を検証する。各 spec が自前で書くと文面がばらつく。なお `region-plots` の `text(auto_latex_notation=None)` と `heatmaps` の `colorbar` は `None` を受け付けるので、`check_bool` ではなく `check_optional_bool` を使う
- **Selected Approach**: `check_optional_bool` の隣に `check_bool(value, name)` を置き、`bool` / `numpy.bool_` 以外を `` `{name}` must be True or False, but got ... `` の `TypeError` にする。doctest 形式の Examples を持たせる
- **Rationale**: `check_optional_bool` と同じ受け付ける型と同じ形の文面にそろえ、後続の spec は呼ぶだけで済む

### Decision: 共通 doctest ランナーを本 spec で作る
- **Context**: roadmap の実装順で本 spec が最初にマージされる。後続の spec が使用例を書く前にランナーがあれば、各 spec が自分の例を同じ条件で確かめられる
- **Selected Approach**: `tests/test_doctests.py` に、公開 API だけを収集して docstring ごとにパラメータ化し、一時ディレクトリで FutureWarning をエラーにして実行するランナーを置く。option flags は `ELLIPSIS | NORMALIZE_WHITESPACE`。既知の失敗は `__init__` の 1 件だけを `xfail(strict=True)` にする
- **Rationale**: 例の書き方（`plt.subplots(layout="constrained")` から始める、`savefig` しない）が守られていれば v3.x でも v4.0.0 でも警告なしで通るので、FutureWarning をエラーにすることで規約違反と使用例の陳腐化を検出できる。strict な xfail なら、担当の spec が書き直した時点で外し忘れが失敗として表に出る
- **Trade-offs**: `__init__` の Examples 節は `user-guide-docs` のマージまで検証されない

### Decision: 型注釈の書き方（新規モジュールと既存モジュール）
- **Context**: cross-spec review（round 2）。tech.md「Compatibility」は、新しいモジュールに `from __future__ import annotations` を付け、注釈を組み込みジェネリクスと `X | None` で書くと定めている。既存のファイルは 1 ファイルの中で書き方を揃える
- **Selected Approach**: 新規の `_deprecation.py` / `_post_draw.py` は `from __future__ import annotations` と `X | None`（`PostDrawContext.tight_layout`、`decide_layout`、`decide_colorbar` など）、組み込みジェネリクス（`list[...]`、`set[...]`、`type[...]`）で書く。既存の `_api.py` / `utils.py` に足す部分（`TernaryDiagram` の引数、`_BasePlotter`、`check_optional_bool`）は、ファイル内の書き方に合わせて `typing.Optional` のままにする
- **Rationale**: 注釈は文字列のまま保持されるので、Python 3.9 でも `X | None` を評価しない（`dataclass` もフィールドの注釈を評価しない）。新規モジュールには実行時に評価される型別名がない。足す場合は 3.9 で評価できるよう、その別名だけ `typing.Optional` / `Union` で書く
- **Follow-up**: 他の spec（`diagram-customization` の `_skeleton.py`、`heatmaps` の `_mesh.py`）も同じ規則で書いている

## Synthesis Outcomes
- **Generalization**: レイアウトとカラーバーは「既定値のまま → v3.x の挙動を実行し、v4.0.0 で変わるなら 1 回だけ警告」という同じ形の問題。`Action` 列挙（実行するか、警告するか）と `first_time(key)` で両方を同じ枠組みで扱い、後続 spec が自分の既定値変更にも使えるようにした（実装は今の 2 つだけ）
- **Build vs Adopt**: 上記のとおり、matplotlib の private API と Python 3.12 専用の機能は採らない。レイアウト判定は matplotlib の公開 API（`get_layout_engine`、`PlaceHolderLayoutEngine`、`get_constrained_layout`、`get_tight_layout`）だけを使う
- **Simplification**:
  - メソッドごとのレイアウト引数、作成後の setter、「v4.0.0 の既定をまとめて先取りする」一括オプションは作らない
  - `Colorbar` を返す新しい戻り値は作らない。自動追加したカラーバーは matplotlib が設定する `mappable.colorbar` で参照できる（要件 3.6）
  - ポリシーオブジェクトの継承階層は作らず、列挙と関数だけにする

## Risks & Mitigations
- 既存テストと example の `TernaryDiagram(...)` が FutureWarning を出し、テスト出力が警告で埋まる — `td` fixture と example テストでレイアウト設定を明示する。警告を扱うテストは `pytest.warns` と `warnings.simplefilter("error")` で個別に検証する
- `_api.py` と `TernaryDiagram.__init__` を `diagram-customization` も編集する — roadmap の実装順で本 spec が先にマージし、最終シグネチャと検証の順は roadmap の「横断の取り決め」に従う。新しい処理は別モジュールに置き、`__init__` への変更はキーワード専用引数 1 つと `check_ax` 直後の 2 行（検証と状態の作成）に限る。土台の描画コードには触れない
- 共通 doctest ランナーが既存の `__init__` の Examples 節で失敗する — 1 件だけ `xfail(strict=True)` にし、`user-guide-docs` の書き直しで外す
- 後続 spec の Plotter が `_post_draw` を呼び忘れる — `post_draw_context` を `_BasePlotter` の必須キーワード引数にして配線漏れを `TypeError` で検出し、design.md に呼び出し規約を書く
- 3.6 未満の分岐を CI で実行できない — 3.10 上でバージョン定数を差し替える単体テストで判定ロジックを検証する
- steering（`structure.md` の Plotter パターン、`tech.md` の「描画ごとの `fig.tight_layout()`」）が実装後に古くなる — 実装完了後に `/kiro-steering` で同期する（本 spec の範囲外）
- example ノートブックが `flag_cbar` を使い続け、再実行すると FutureWarning が出る — `user-guide-docs` で書き換える

## References
- [matplotlib.figure.Figure.tight_layout](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.tight_layout.html) — 実行後にレイアウトエンジンを外す挙動
- [matplotlib.layout_engine](https://matplotlib.org/stable/api/layout_engine_api.html) — `PlaceHolderLayoutEngine` / `ConstrainedLayoutEngine` / `TightLayoutEngine`（3.6+）
- [matplotlib.figure.SubFigure](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.SubFigure.html) — 3.4+。`tight_layout` を持たない
- [Python warnings — FutureWarning と既定のフィルタ](https://docs.python.org/3/library/warnings.html#default-warning-filter) — FutureWarning は既定で表示され、位置ごとに 1 回
