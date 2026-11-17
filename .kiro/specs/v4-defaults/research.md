# Research & Design Decisions

## Summary
- **Feature**: `v4-defaults`
- **Discovery Scope**: Extension（既存の描画後処理・非推奨の仕組み・土台の初期化への変更。新しい依存はない）
- **Key Findings**:
  - 既定値の切り替えは `_post_draw.py` の決定表の「未指定」の行と、`_api._resolve_annotation_text` の未指定の分岐だけで済む。v3.2.1 の時点で、この形になるよう作ってある
  - `PostDrawContext.has_colorbar` の今の判定（`cb.mappable.colorbar is cb`）は、同じ mappable に別のカラーバーを足すと偽になる。カラーバーの Axes が図に残っているかで判定すれば、matplotlib 3.10 / 3.11 のどちらでも正しく判定でき、`fig.clf()` の後も正しく「ない」になる
  - 位置引数の予告は、シグネチャを変えずに包むデコレータで実装できる。ドキュメントのシグネチャ、doctest のランナー、docstring の静的テストはどれも元の関数の情報を読むので影響しない

## Research Log

### 既定値の切り替え箇所
- **Context**: 要件 3・4・6.1 の切り替えで、どこを変えれば足りるか
- **Sources Consulted**: `src/ternary_diagram/_post_draw.py`（`decide_layout`、`decide_colorbar`）、`src/ternary_diagram/_api.py`（`_BasePlotter._post_draw`、`_resolve_annotation_text`、`_resolve_colorbar_arg`）
- **Findings**:
  - `decide_layout` は `setting is None` の行だけが v4.0.0 で変わる（`APPLY_AND_WARN` → `SKIP`）とコメントで明示している
  - `decide_colorbar` も `requested is None` の行だけが変わる（`ADD_AND_WARN` → `SKIP`、既存なしは `ADD` のまま）
  - `_resolve_annotation_text` は `auto_latex_notation is None` のとき v3.x の表示（`get_label`）を返し、v4 の規則（`_format_text(text, default)`）と違えば警告する。v4.0.0 では v4 の規則の値をそのまま返せばよい
  - 警告のキー（`LAYOUT_WARNING_KEY`、`COLORBAR_WARNING_KEY`、`LATEX_NOTATION_WARNING_KEY`）と文面の関数は、切り替え後は使われなくなる
- **Implications**: v4.0.0 の段は、決定表の 2 行と注釈の 1 分岐を変え、使われなくなった `*_AND_WARN` の列挙値・キー・文面の関数を消す

### カラーバーが残っているかの判定
- **Context**: 要件 5。登録済みのカラーバーと同じ mappable に利用者が `fig.colorbar` で別のカラーバーを足すと、`mappable.colorbar` が新しいほうを指すため、登録済みのものが「削除済み」と判定される
- **Sources Consulted**: matplotlib の `Colorbar.remove()` の挙動。scratchpad の検証スクリプトで、matplotlib 3.10.8 と 3.11.2、レイアウトエンジンなしと `layout="constrained"`、subfigure で確かめた
- **Findings**:

  | 状況 | 今の判定 `cb.mappable.colorbar is cb` | 新しい判定（Axes が図に残っているか） |
  |---|---|---|
  | 付けた直後 | 真 | 真 |
  | 同じ mappable に別のカラーバーを追加 | **偽（誤り）** | 真 |
  | `cb.remove()` の後 | 偽 | 偽 |
  | `fig.clf()` の後 | **真（誤り）** | 偽 |
  | subfigure に付けた直後 / 外した後 | 真 / 偽 | 真 / 偽 |

  - `Colorbar.remove()` の後の `cb.ax.figure` は、3.10 では `None`、3.11 では元の図のまま。どちらでも `cb.ax.figure is not None and cb.ax in cb.ax.figure.axes` で正しく判定できる
- **Implications**: 判定を「カラーバーの Axes が、まだその図の Axes に含まれているか」に替える。CI の Python 3.9（matplotlib 3.9 系）でも同じ式で判定できる見込みで、テストで確かめる

### 位置引数の予告の実装方法
- **Context**: 要件 1。v3.4.0 で、キーワード専用にする引数を位置引数で渡したら FutureWarning を出し、値の意味は変えない
- **Sources Consulted**: `tests/test_doctests.py`（`DocTestFinder.find(member, name, module=module)` で、名前空間は定義したモジュールの globals）、`tests/test_owned_docstrings.py`（`inspect.getattr_static` で docstring を読む）、Sphinx autodoc（`inspect.signature` は `__wrapped__` をたどる）。matplotlib の `_api.make_keyword_only` は同じ目的の仕組みだが private API
- **Findings**:
  - `functools.wraps` で包めば、`__doc__`・`__wrapped__` が引き継がれる。Sphinx のシグネチャ表示と docstring の静的テストは変わらない。doctest のランナーは `module=` を渡しているので、名前空間も変わらない
  - パッケージ内で、公開メソッドを位置引数のオプション付きで呼んでいる箇所はない（`_BasePlotter._post_draw` が呼ぶのは private な `_BasePlotter.colorbar`）
  - テストのうち、オプションを位置引数で渡しているのは `tests/test_side_effects.py` の 6 番目の位置引数のテスト（`test_sixth_positional_*`、`positional=True` の組み合わせ）だけ。ドキュメント・サンプル・README はすべてキーワードで渡している
- **Implications**: シグネチャを保つデコレータを `_deprecation.py` に置く。v3.4.0 では上のテストに `pytest.warns` を足し、v4.0.0 では `TypeError` を確かめるテストに書き換える

### 縦横比の固定方法
- **Context**: 要件 7。follow-up の調査（2026-11-17、README の例の図、144 dpi）
- **Findings**:
  - 左の余白は、`adjustable="datalim"` ではカラーバー付きの constrained layout で matplotlib 3.10 が 3px、3.11 が 0px（はみ出す）。`adjustable="box"` ではどちらも 8〜9px で、左右が均等になる
  - `set_aspect` を呼ぶのは `TernaryDiagram.__init__` の 1 か所だけで、描画と土台の描き直し（`_skeleton.py` の `autoscale_view`）は縦横比の設定に触れない。利用者が作成後に変えた設定は、v3.x でも元に戻されない
- **Implications**: v4.0.0 では `__init__` の 1 行を変える。v3.4.0 は文書で予告し、作成後に `td.ax.set_aspect("equal", adjustable="box")` で試せることを案内する。その状態が描画と `set_*` で保たれることは、v3.4.0 のテストで固定する

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| シグネチャを保つデコレータ | 元の関数を `functools.wraps` で包み、位置引数の数を数えて警告する | シグネチャ・docstring・doctest が変わらない。v4.0.0 ではデコレータを外して `*` を足すだけ | 包む関数の第 1 引数（`self`）を前提にする | 採用 |
| `*args` を受けるシグネチャ | `def scatter(self, vector, z=None, *args, z_min=None, ...)` にして `args` を手で割り当てる | 実行時の挙動を完全に制御できる | ドキュメントのシグネチャが崩れる。割り当てを手書きするので誤りやすい | 不採用 |
| matplotlib の `_api.make_keyword_only` | matplotlib の非推奨用デコレータ | 実績がある | private API で、版により変わる。警告が MatplotlibDeprecationWarning になる | 不採用 |

## Design Decisions

### Decision: 位置引数の予告は `_deprecation.deprecate_positional` で行う
- **Context**: 要件 1.2〜1.7
- **Alternatives Considered**:
  1. シグネチャを保つデコレータ
  2. `*args` を受けて手で割り当てる
- **Selected Approach**: `deprecate_positional(func_name, n_data, *, once=None)`。包んだメソッドの引数のうち、`self` と先頭の `n_data` 個より後ろが位置引数で渡されたら、その名前を並べた FutureWarning を `warn_external` で出し、元の関数を同じ引数で呼ぶ
- **Rationale**: 値の意味を変えない（1.2）ことが構造上保証され、v4.0.0 への移行が機械的になる
- **Trade-offs**: 呼び出しごとに引数の数を比べるわずかなコストが増える
- **Follow-up**: doctest のランナーと docstring の静的テストが、包んだメソッドを今までどおり集めることをテストで確かめる

### Decision: 1 回化は三角図ごと・メソッドごと
- **Context**: 要件 1.5。steering の「三角図ごと・理由ごとに 1 回」
- **Selected Approach**: キーは `"positional.<メソッド名>"`。メソッドは `PostDrawContext.first_time` で判定する。`TernaryDiagram.__init__` は呼ぶたびに新しい三角図なので、毎回出す（`once=None`）
- **Rationale**: 既存の 1 回化の仕組みをそのまま使え、新しい状態を持たない

### Decision: v4.0.0 では決定表の未指定の行だけを変え、使われなくなる警告を消す
- **Context**: 要件 3・4・6.1
- **Selected Approach**: `decide_layout(None, NO_ENGINE)` → `SKIP`、`decide_colorbar(None, has_existing=True)` → `SKIP`。`LayoutAction.APPLY_AND_WARN`・`ColorbarAction.ADD_AND_WARN`・警告のキー・文面の関数を消す。`tight_layout` の型は `bool | None = None` のままにし、None は「調整しない」と同じ意味にする
- **Rationale**: 公開の引数の型を変えずに済み（None を明示しているコードを壊さない）、到達しないコードを残さない
- **Trade-offs**: `tight_layout=None` と `False` が同じ意味になる。docstring に明記する

### Decision: 汎用の非推奨ヘルパーは v4.0.0 でも残す
- **Context**: v4.0.0 では `flag_cbar` の改名の解決（`resolve_renamed_parameter`）と位置引数の予告（`deprecate_positional`）が使われなくなる
- **Selected Approach**: 両方を `_deprecation.py` に残し、単体テストも残す。`TernaryDiagram` からの利用（デコレータの適用と、1 回化のための private なメソッド）は外す
- **Rationale**: steering が改名と非推奨の標準の手順として定めており、v4.x 以降の非推奨でも同じ仕組みを使うため

### Decision: カラーバーが残っているかは、その Axes が図に残っているかで判定する
- **Context**: 要件 5
- **Selected Approach**: `has_colorbar` を「登録したカラーバーのうち、`cb.ax.figure` があり、その `axes` に `cb.ax` が含まれるものが 1 本でもあるか」にする。v4.0.0 の段で入れる（以前の決定どおり。v3.4.0 で直すと重複の警告が出る条件が変わる）
- **Rationale**: matplotlib の版によらず同じ式で判定でき、利用者が足したカラーバーに左右されない

### Decision: `flag_cbar` は理由付きの `TypeError` にする
- **Context**: 要件 6.3。利用者の回答で、わかりやすい `TypeError` を選んだ
- **Selected Approach**: `_resolve_colorbar_arg` で `flag_cbar` が渡されていたら、描く前に `_deprecation.format_removed_parameter` の文面で `TypeError` を送出する
- **Rationale**: matplotlib に素通しすると「Unknown property flag_cbar」の `AttributeError` になり、何を直せばよいかわからない

### Decision: リリースは 2 段に分け、v4.0.0 の段は v3.4.0 のタグの後に main に入れる
- **Context**: 要件 8。v3.4.0 では図の結果を変えない
- **Selected Approach**: 予告の段（v3.4.0）のタスクを main にマージしてタグを打った後に、切り替えの段（v4.0.0）のタスクを main に入れる。v3.4.x の修正が要るときは、タグ `v3.4.0` から保守用のブランチを切る
- **Rationale**: 1 本の main で、どの時点でも「出せる状態」を保てる

## Risks & Mitigations
- 包んだメソッドを doctest のランナーや docstring の静的テストが拾わなくなる — 予告の段の最初のタスクで、両方のテストが今までどおり通ることを確かめる
- v4.0.0 で図の見た目が変わり、README の画像とチュートリアルの保存済みの出力が古くなる — 切り替えの段で、README のノートブックとチュートリアルを再実行して保存し直す
- `adjustable="box"` で、利用者の凡例の位置とカラーバーの長さが変わる — 移行ページに影響と、`set_aspect(..., adjustable="datalim")` で戻す方法を書く
- 古い matplotlib で `Colorbar.remove()` の後の `cb.ax.figure` の扱いが違う — `None` と「元の図のまま」の両方を正しく扱う式にし、CI の全 Python 版でテストする

## References
- `.kiro/steering/roadmap.md` の「Deferred to v4.0.0」 — 本 spec の出典
- `CHANGELOG.md` の v3.2.1 / v3.3.0 の Deprecations — 予告済みの既定値の変更
- `docs_src/user_guide/migration_v4.md` — 移行ページ
- [matplotlib.axes.Axes.set_aspect](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.set_aspect.html) — `adjustable` の意味
