# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from ternary_diagram import __author__, __version__

project = "ternary-diagram"
copyright = "2024, yu9824"
author = __author__
release = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",  # docstringからドキュメントを作成してくれる。
    "sphinx.ext.napoleon",  # google式・numpy式docstringを整形してくれる。
    "sphinx.ext.githubpages",  # github-pages用のファイルを生成してくれる。
    "myst_nb",
    "sphinx_book_theme",
    "jupyter_sphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_static_path = ["_static"]

# favicon
# https://pydata-sphinx-theme.readthedocs.io/en/latest/user_guide/branding.html
# html_favicon = "_static/favicon.png"

# テーマのオプション設定
# https://pydata-sphinx-theme.readthedocs.io/en/latest/user_guide/branding.html
html_theme_options = {
    "show_toc_level": 2,  # TOCの表示レベル（見出しの深さ、1-3の範囲）
    # GitHub へのリンクボタン
    "repository_url": "https://github.com/yu9824/ternary-diagram",
    "use_repository_button": True,
    "use_issues_button": True,
    # site logo
    # "logo": {
    #     "image_light": "_static/site_logo.png",
    #     "image_dark": "_static/site_logo_dark.png",
    # },
}

# MyST-NB（ノートブック統合）の設定
# 使い方ページ（出力を持たない MyST Markdown ノートブック）はビルドのたびに実行し、
# チュートリアルは保存済みの出力をそのまま表示する。キャッシュは使わない。
nb_execution_mode = "force"
nb_execution_excludepatterns = ["tutorials/*"]
nb_execution_raise_on_error = True  # セルの例外でビルドを失敗させる
nb_execution_in_temp = True  # savefig などがリポジトリにファイルを作らない
# stderr（FutureWarning を含む）を Sphinx の警告にする
nb_output_stderr = "warn"

# クラスの docstring に続けて __init__ の docstring（作成時の引数）を表示する
autoclass_content = "both"

# MyST の拡張（$$で数式など）
myst_enable_extensions = [
    "dollarmath",
    "colon_fence",
]
