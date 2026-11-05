"""mkdocs hooks for the docs site.

The docstrings use Sphinx roles such as :class:`DocResult`. mkdocstrings keeps
the backticked name as code but leaves the ":class:" prefix in the page, so
this hook removes it from the rendered HTML.
"""

from __future__ import annotations

import re

SPHINX_ROLE = re.compile(r":(?:class|func|meth|attr|mod|data|exc|obj):(?=<code>)")


def on_page_content(html: str, **kwargs) -> str:
    return SPHINX_ROLE.sub("", html)
