# Technology Stack

## Architecture

matplotlib の薄いラッパーとして作られた純 Python ライブラリ。ファサード（`TernaryDiagram`）が描画種別ごとの Plotter クラスに処理を委譲し、各 Plotter が「3 成分ベクトルの検証・正規化 → 2 次元座標への変換 → matplotlib の呼び出し」を受け持つ。保持する状態は描画先の `Axes` と、描画済み座標の記録（`x_` / `y_`）だけ。

## Core Technologies

- **Language**: Python >= 3.8（CI で 3.8〜3.13 を検証）
- **Runtime dependencies**: `numpy >= 1.20`、`matplotlib`（上限なし）
- **Build**: setuptools + `pyproject.toml`（src レイアウト）。バージョンは `ternary_diagram.__version__` を動的に参照する単一ソース

## Key Libraries

- **matplotlib**: 描画のすべて。`Axes.scatter` / `tricontourf` / `tricontour` / `plot` / `annotate`、`Figure.colorbar` を直接呼ぶ
- **numpy**: 入力ベクトルの検証、正規化、座標変換
- **pandas**: テストとサンプルでのみ使う（ランタイム依存にはしない）

## Development Standards

### Compatibility

- Python 3.8 をサポートするため `typing.Tuple` / `typing.List` を使い、`tuple[...]` のような組み込みジェネリクスは使わない。該当 import は `# isort: skip` を付けてファイル先頭に固定する
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

- Ruff で lint と format。`line-length = 79`
- `F401`（未使用 import）は自動修正の対象外。re-export を誤って消さないため
- docstring は NumPy スタイル（Sphinx の napoleon で整形）で、英語で書く。公開メソッドには `Parameters` / `Returns` / `Examples` と、ラップしている matplotlib 関数のドキュメント URL を書く。URL で長くなる docstring には `# noqa: E501` を付ける

### Error Handling

- 入力検証は `utils.check_*` に集約し、何が悪いかを示すメッセージ付きで `TypeError` / `ValueError` を送出する

### Testing

- pytest。`example/` 配下の CSV を GitHub raw URL から読み込み、主要な描画処理が例外なく通るかを確かめるスモークテストが中心（画像比較はしない）
- `utils.py` の関数は docstring に doctest 形式の Examples を持つ

## Development Environment

### Required Tools

- Python 3.8+
- pip extras: `test`（pytest, pandas）、`dev`（build, jupyter, pandas）、`docs`（sphinx 一式）

### Common Commands

```bash
# Test:  pytest -xs .
# Lint:  ruff check . && ruff format --check .
# Type:  mypy src
# Build: python -m build
# Docs:  sphinx-apidoc -f -o ./docs_src ./src/ternary_diagram --module-first \
#          && sphinx-build -b html ./docs_src ./docs
```

## CI / Release

- **CI**: すべての push で Python 3.8〜3.13 のマトリクスを組み、`pip install .[test,optional]` のあと `pytest -xs .` を実行
- **リリース**: `vX.Y.Z` または `vX.Y.Z-rc.N` タグの push を起点に、PyPI（Trusted Publishing）、TestPyPI、GitHub Release（Sigstore 署名付き）へ自動で公開する。タグに `-` を含むものはプレリリース扱い
- **バージョン更新**: `src/ternary_diagram/__init__.py` の `__version__` だけを書き換え、コミットメッセージはバージョン番号のみ（例: `v3.2.1-rc.0` → `v3.2.1`）
- **ドキュメント**: 正式版タグで sphinx-apidoc が API リファレンスを生成し、GitHub Pages にデプロイする。生成された `.rst` はコミットしない
- **リリースノート**: GitHub の自動生成。PR ラベル `enhancement` / `bug` で分類される

## Key Technical Decisions

- **pymatgen 非依存**: 三角図に必要な座標変換と化学式の LaTeX 整形を自前で実装し、依存を最小限に保つ
- **kwargs の透過とデフォルト注入**: ライブラリ側のデフォルトは `_set_default_params` で「ユーザーが指定していなければ設定」する。ユーザー指定が常に優先される
- **zorder による描画レイヤーの固定**: 等高線 (0) < グリッド (1) < 線 (2) < 散布図 (3) をモジュール定数 `DEFAULT_ZORDER_*` で管理し、呼び出し順に関係なく重なり順を保つ
- **入力の自動正規化**: 各行を合計 1 に正規化してから座標変換するので、ユーザーは比率をそのまま渡せる
- **描画ごとの `fig.tight_layout()`**: 各 Plotter は描画後にレイアウトを整え、colorbar やラベルのはみ出しを防ぐ

---
_Document standards and patterns, not every dependency_
