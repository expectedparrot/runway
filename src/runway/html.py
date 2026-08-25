"""HTML escaping, matched to React's.

Byte parity with the web survey's server-rendered output means escaping exactly
as React does, which is not what most escapers do:

===========  ==================  =================  ==================
character    React               Python (quote=1)   MarkupSafe / Jinja
===========  ==================  =================  ==================
``&``        ``&amp;``           ``&amp;``          ``&amp;``
``<``        ``&lt;``            ``&lt;``           ``&lt;``
``>``        ``&gt;``            ``&gt;``           ``&gt;``
``"``        ``&quot;``          ``&quot;``         ``&#34;``
``'``        ``&#x27;``          ``&#x27;``         ``&#39;``
===========  ==================  =================  ==================

Two things follow. First, stdlib ``html.escape(s, quote=True)`` is a byte-exact
match for React, so that is what this module uses. Second, MarkupSafe is *not*,
so Jinja's autoescaping cannot be relied on directly -- see ``templating.py``,
which routes every interpolation through ``escape`` below.

React also escapes quotes in **text** content, not only in attributes, so there
is a single escape function here rather than separate text/attribute ones.
"""

from __future__ import annotations

from html import escape as _escape


def escape(value: object) -> str:
    """Escape a value exactly as React's ``escapeTextForBrowser`` does."""
    return _escape(str(value), quote=True)


# Kept as names for the two call sites' intent; both escape identically because
# React makes no distinction.
text = escape
attr = escape
