# Technology Stack

## Architecture

matplotlib の薄いラッパーとして作られた純 Python ライブラリ。ファサード（`TernaryDiagram`）が描画種別ごとの Plotter クラスに処理を委譲し、各 Plotter が「3 成分ベクトルの検証・正規化 → 2 次元座標への変換 → matplotlib の呼び出し」を受け持つ。保持する状態は描画先の `Axes`、描画済み座標の記録（`x_` / `y_`）、三角図ごとの描画後処理の状態（`PostDrawContext`: レイアウト設定、この三角図が付けたカラーバー、出した警告）、土台の部品の設定と artist（`_Skeleton`）だけ。描画後の処理は「図を変えない純粋な判定（`_post_draw.py` の決定表）」と「副作用を 1 か所で実行する入口（`_BasePlotter._post_draw`）」に分けている。

## Core Technologies

- **Language**: Python >= 3.9（CI で 3.9〜3.14 を検証）
- **Runtime dependencies**: `numpy >= 1.20`、`matplotlib`（上限なし）
- **Build**: setuptools>=77 + setuptools-scm + `pyproject.toml`（src レイアウト、PEP 639 のライセンス表記）。バージョンは git タグから決まり、ビルド時に `_version.py`（git 管理外）が生成される。未インストールで import した場合の `__version__` は `"unknown"`

## Key Libraries

- **matplotlib**: 描画のすべて。`Axes.scatter` / `tricontourf` / `tricontour` / `plot` / `annotate`、`Figure.colorbar` を直接呼ぶ
- **numpy**: 入力ベクトルの検証、正規化、座標変換
- **pandas**: テストとサンプルでのみ使う（ランタイム依存にはしない）

## Development Standards

### Compatibility

- 既存コードは Python 3.8 時代の名残で `typing.Tuple` / `typing.List` を `# isort: skip` 付きでファイル先頭に置いている。3.9+ になったので組み込みジェネリクスも使えるが、1 ファイルの中ではどちらかに揃える
- 新しく作るモジュールは `from __future__ import annotations` を付け、注釈には組み込みジェネリクス（`list[int]`）と `X | None` を使う
- matplotlib のバージョン差異はモジュール冒頭の分岐で吸収する

```python
if tuple(map(int, matplotlib.__version__.split(".")[:2])) >= (3, 7):
    from matplotlib.tri import Triangulation, TriContourSet
else:
    from matplotlib.tri.triangulation import Triangulation
    from matplotlib.tri.tricontour import TriContourSet
```

### Type Safety

- 公開 API には型ヒントを付ける。配列入力は `numpy.typing.ArrayLike` で受け、内部で `np.ndarray` に変換する
- mypy（`ignore_missing_imports = True`）。解消しきれない箇所は `# FIXME: mypy` や `# type: ignore[...]` で明示する

### Code Quality

- Ruff で lint と format。設定は `ruff.toml`（`line-length = 79`、pydocstyle は numpy 規約）。VS Code の ruff 拡張もこのファイルを参照する
- `F401`（未使用 import）は自動修正の対象外。re-export を誤って消さないため
- docstring は NumPy スタイル（Sphinx の napoleon で整形）で、英語で書く。公開メソッドには `Parameters` / `Returns` / `Examples` と、ラップしている matplotlib 関数のドキュメント URL を書く。URL で長くなる docstring には `# noqa: E501` を付ける

### Docstring Examples

- 公開 API の `Examples` は doctest 形式（`>>>`）で書く。描画する例は `fig, ax = plt.subplots(layout="constrained")` で図を作って `ax=ax` を渡すところから始める。v3.x でも v4.0.0 でも FutureWarning を出さない書き方にするため。図を扱わない純粋関数（`utils` の計算関数など）の例は図を作らない
- 例は docstring ごとに、必要な import の行（`>>> import matplotlib.pyplot as plt`、`>>> from ternary_diagram import TernaryDiagram` など）から始め、その docstring だけで実行できるようにする。ランナーの名前空間は docstring が定義されたモジュールの globals なので、`_api.py` が import していない `plt` などは使えない
- 例はファイルを書き出さない（`savefig` は書かない）
- `Parameters` の各項目には意味を書く文を必ず置き、既定値は文の後に `, by default X` と添える。`, by default None` だけの項目は書かない
- 共通の doctest ランナー（`tests/test_doctests.py`）が、公開 API（`TernaryDiagram` とその公開メソッド、`utils` の公開関数）の例を一時ディレクトリで、FutureWarning をエラーにして実行する。各 spec は自分のランナーを作らず、このランナーで自分の例が通ることを確かめる
- private なメソッドの docstring には `>>>` の例を書かない（ランナーの対象外で、そのままでは実行できないため）

### Error Handling

- 入力検証は `utils.check_*` に集約し、何が悪いかを示すメッセージ付きで `TypeError` / `ValueError` を送出する
- matplotlib のプロパティ名を受け取る API は、描く前に artist クラスの setter と照合し、未知の名前は `Artist.set` と同じ文面の `AttributeError` にする（何も描かない設定のときも受け付けない名前を残さない）。値の不正は matplotlib の例外をそのまま出す
- 検証に `assert` は使わない（`python -O` で消えるため）
- matplotlib の kwargs と内部で渡す引数が衝突する場合は、別名として受ける（`vmin` → `z_min`）か、ユーザー指定を優先する（`contour(levels=...)`）。どちらを使うか決められない組み合わせだけ `ValueError` にする
- 利用者向けの警告は `_deprecation.warn_external` だけから出す（発生位置はパッケージ外で最初の呼び出し元＝利用者の行）。既定値の変更は FutureWarning で予告し、三角図ごと・理由ごとに 1 回に絞る。引数の改名は旧名を非推奨の別名として残し、`resolve_renamed_parameter` で解決する

### Testing

- pytest。ネットワークに依存させない。`example/` 配下の CSV はリポジトリ内のパスから読む
- 画像比較はせず、生成された artist の状態（座標、色、zorder、colorbar の有無、levels など）を assert する。OS やフォントの差で壊れないようにするため
- 共通 fixture は `tests/conftest.py`（Agg バックエンド、テストごとの `plt.close("all")`、`ax` / `td`、サンプル CSV）
- デフォルト値を持つ引数は「デフォルト」と「上書き」の両方をテストする
- `utils.py` の関数は docstring に doctest 形式の Examples を持つ（実行は上の共通ランナー）
- テスト一式は `-W error::FutureWarning` でも通る状態を保つ。共通 fixture `td` は `tight_layout=True` を明示している。既定値そのものを確かめるテストは fixture を使わず、その場で引数を省略して作り、出る警告は `pytest.warns` で捕まえる
- 警告の文面は全文一致ではなく `match=` で要点を確かめ、発生位置（`filename`）がテストファイルであることも確かめる

## Development Environment

### Required Tools

- Python 3.9+
- pip extras: `test`（pytest, pandas）、`dev`（build, jupyter, pandas）、`docs`（sphinx 一式）

### Common Commands

```bash
# Test:  pytest -xs .            # 未インストールなら PYTHONPATH=src を付ける
# Lint:  ruff check . && ruff format --check .
# Type:  mypy src
# Build: python -m build
# Docs:  sphinx-apidoc -f -o ./docs_src ./src/ternary_diagram --module-first \
#          && sphinx-build -b html ./docs_src ./docs
```

## CI / Release

- **CI**: main への push と PR で、Python 3.9〜3.14 のマトリクスで `pip install ".[test]"` → `pytest -xs .`。paths-filter でコード・テスト・`example/` に変更がないときはジョブ単位でスキップする（required check を Pending にしないため）
- **リリース**: `vX.Y.Z` または `vX.Y.Z-rc.N` タグの push を起点に、PyPI（Trusted Publishing）、TestPyPI、GitHub Release（Sigstore 署名付き）へ自動で公開する。タグに `-` を含むものはプレリリース扱い
- **バージョン更新**: タグを打つだけ（setuptools-scm）。`__version__` を書き換えるコミットは作らない。手順は `HOW_TO_RELEASE.md`、利用者向けの変更点は `CHANGELOG.md`
- **Trusted Publishing**: PyPI / TestPyPI の設定はワークフローのファイル名 `release-pypi.yml` に紐づくので、改名するときは PyPI 側の設定も変える
- **ドキュメント**: Sphinx + MyST-NB + sphinx-book-theme。正式版タグで sphinx-apidoc が API リファレンスを生成し、GitHub Pages にデプロイする。生成された `.rst` はコミットしない。ノートブックは実行せず保存済みの出力を表示する（`nb_execution_mode = "off"`）
- **リリースノート**: GitHub の自動生成。PR ラベル `enhancement` / `bug` で分類される

## Key Technical Decisions

- **pymatgen 非依存**: 三角図に必要な座標変換と化学式の LaTeX 整形を自前で実装し、依存を最小限に保つ
- **kwargs の透過とデフォルト注入**: ライブラリ側のデフォルトは `_set_default_params` で「ユーザーが指定していなければ設定」する。ユーザー指定が常に優先される
- **zorder による描画レイヤーの固定**: 等高線 (0) < グリッド (1) < 線 (2) < 散布図 (3) をモジュール定数 `DEFAULT_ZORDER_*` で管理し、呼び出し順に関係なく重なり順を保つ
- **入力の自動正規化**: 各行を合計 1 に正規化してから座標変換するので、ユーザーは比率をそのまま渡せる
- **土台は部品ごとの差し替えで変える**: 外枠・グリッドなど 5 つの部品は、設定（名前付きの項目と matplotlib のプロパティ）を保持し、変更のたびに「検証 → 図形の仕様を純粋に計算 → 新しい artist を作る → 古い artist を消す → 確定」の順で描き直す。途中で失敗したら作りかけを消して元の設定と artist を保つ（全部か無し）。未指定の設定は前回の値を引き継ぎ、非表示の間も設定を保つ。グリッドを描き直したら外枠を `ax.lines` の末尾へ移し、外枠が上に描かれる状態を保つ。利用者が `remove()` / `cla()` で外した artist は飛ばす。描き直しはレイアウト調整もカラーバーの判定もしない（`_post_draw` を呼ばない）
- **描画後処理の一元化と既存レイアウトの尊重**: 描画後のレイアウト調整とカラーバーの追加は `_BasePlotter._post_draw` だけが行う。図にレイアウトエンジン（constrained など）があれば調整しない、subfigure では調整しない。v3.x の既定（エンジンのない図では `tight_layout()`、`z` 付きの描画ごとにカラーバー追加）は保ち、v4.0.0 で変える既定には FutureWarning で予告する。決定表は未指定の行だけを変えれば v4.0.0 に移れる形にしてある

---
_Document standards and patterns, not every dependency_

_updated_at: 2026-10-20 — Python 3.9+, setuptools-scm, offline test suite, MyST-NB docs への移行を反映_
_updated_at: 2026-10-24 — plot-side-effects（描画後処理の共通化、`_post_draw.py` / `_deprecation.py`、共通 doctest ランナー）を反映_
_updated_at: 2026-11-08 — diagram-customization（土台の部品化 `_skeleton.py`、`set_*` / `*_kw` / 取り出し口）を反映_
