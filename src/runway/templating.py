"""The Jinja environment.

Two settings here carry the package's contract and should not be changed
casually.

**Escaping.** ``autoescape`` is on so that a forgotten filter is still safe, but
MarkupSafe's escaping is not byte-identical to React's (``&#39;`` vs
``&#x27;``, ``&#34;`` vs ``&quot;``). ``finalize`` therefore escapes every
interpolated value with :func:`html.escape` -- which *is* byte-identical -- and
marks the result already-safe, so autoescape passes it through untouched. The
result: React-exact escaping applied automatically at every site, with
autoescape left in place as a backstop rather than as the mechanism.

**Whitespace.** Templates must emit no incidental whitespace, because the tests
assert byte equality with the reference implementation's server-rendered output
and JSX discards whitespace between elements. Jinja does not: it emits every
newline and indent it sees. ``trim_blocks`` and ``lstrip_blocks`` handle
newlines around
``{% %}`` tags; boundaries between two literal HTML elements need an explicit
``{#- -#}`` separator line. That is the deliberate ugliness -- see README.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from .html import escape

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _finalize(value: object) -> object:
    """Escape every interpolated value the way React does.

    Returning :class:`Markup` tells autoescape the value is already safe, so it
    is emitted verbatim instead of being re-escaped by MarkupSafe's rules.
    """
    if value is None:
        return ""
    if hasattr(value, "__html__"):
        return value
    return Markup(escape(value))


def build_environment(template_dir: Path | None = None) -> Environment:
    """Construct the package's Jinja environment."""
    return Environment(
        loader=FileSystemLoader(str(template_dir or TEMPLATE_DIR)),
        autoescape=True,
        finalize=_finalize,
        trim_blocks=True,
        lstrip_blocks=True,
        # A typo'd variable should fail loudly rather than render an empty
        # string that silently diverges from the React output.
        undefined=StrictUndefined,
        keep_trailing_newline=False,
    )


_ENV: Environment | None = None


def env() -> Environment:
    """The shared environment, built on first use."""
    global _ENV
    if _ENV is None:
        _ENV = build_environment()
    return _ENV


def render(template_name: str, **context: object) -> str:
    """Render a template by name."""
    return env().get_template(template_name).render(**context)
