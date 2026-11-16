# リリース手順

バージョンは git のタグから setuptools-scm が決める。`__version__` を書き換えるコミットは不要。

## CHANGELOG

`CHANGELOG.md` の `Unreleased` を、リリースするバージョン名に書き換えてコミットする。

```bash
git commit -m "docs: update CHANGELOG for v0.0.1"  # バージョンは適宜変更
```

## タグ

```bash
git tag v0.0.1
git push origin v0.0.1
```

タグは頭に'v'をつける以外は、原則 [Semantic Versioning](https://semver.org/lang/ja/) に従う。

e.g.) v1.0.0 v3.2.1-alpha.0 v4.1.2-beta.1 v0.2.1-rc.0

## リリース

タグを push すると `.github/workflows/release-pypi.yml` が次を行う。

- PyPI に公開する。対象は `-` を含まないタグと、`rc` を含むタグ
- TestPyPI に公開する。対象はすべてのタグ
- GitHub Release を作成し、Sigstore で署名した配布物を添付する。`-` を含むタグはプレリリース扱い。リリースノートは PR のラベル (`enhancement` / `bug`) から自動生成される

`vX.Y.Z` 形式のタグでは、`.github/workflows/docs.yml` がドキュメントを GitHub Pages にデプロイする。

PyPI の Trusted Publishing はワークフローのファイル名 (`release-pypi.yml`) に紐づいている。ファイル名を変えるときは、PyPI と TestPyPI の Trusted Publisher の設定も合わせて変える。

### conda

PyPI に公開されると、bot が feedstock に更新の PR を自動で作る。requirements は変わらなかったりするので手で直さなきゃいけない場面も多そう。

v3.3.0 からビルドに setuptools-scm を使うので、レシピの `requirements.host` に `setuptools-scm` (と `setuptools >=77.0.3`) が必要。

```bash
git remote add regro-cf-autotick-bot git@github.com:regro-cf-autotick-bot/ternary-diagram-feedstock.git
git fetch regro-cf-autotick-bot

```

#### condaのbotによるリリース参考

- [Official Documents](https://conda-forge.org/docs/maintainer/updating_pkgs/)
- [日本語でのブログ記事](https://zenn.dev/pejpo/articles/9f767fa1bf031e)
