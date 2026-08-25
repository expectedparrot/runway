"""Markdown, rendered the way the respond page renders it.

Question text and option text are both markdown on the live page -- each goes
through ``react-markdown`` with ``remark-gfm`` -- so previewing them as plain
text shows an author asterisks where their survey will show emphasis.

**The parse is not the hard part.** ``markdown-it-py`` and ``remark`` are both
CommonMark implementations and agree on the tree for everything this package
has a recording of. What differs is the serialization: ``react-markdown`` hands
its tree to React, so what reaches the page is ``renderToStaticMarkup``'s
output, not a markdown library's. That is why this module is a pair of
renderers over markdown-it's token stream rather than a call to
``md.render()`` -- the escaping, the void-element form and the whitespace are
React's, and :mod:`html` already encodes the first of those.

Concretely, against the recordings in ``tests/react_goldens.json``:

* ``'`` escapes to ``&#x27;`` (:func:`html.escape`, not markdown-it's escaper)
* void elements are ``<br/>``, not ``<br />``
* ``~~x~~`` is ``<del>``, where markdown-it emits ``<s>``
* table elements carry no newlines between them, where markdown-it indents
* a raw HTML block is escaped text with **no** paragraph around it, because
  ``react-markdown`` runs without ``rehype-raw``

**Two surfaces, not one.** Question text renders into a ``<div>`` and may emit
anything. An option label renders inside the ``<label>`` around a radio, which
admits phrasing content only, so the reference's option-label component remaps
paragraphs to spans and gives links and inline code classes of their own. Both are the same
parse; :class:`OptionRenderer` is the second serialization.

One rule of that remapping is worth naming because it is invisible in the JSX:
the component writes ``<code className="..." {...props}/>``, and the spread
comes *last*, so a fenced block -- whose props carry ``className="language-py"``
-- keeps the language class and loses the styled one, while inline code (no
className in props) keeps the styled one. A fence with no language has no
className either, so it takes the styled class. Both branches are recorded.

What is **not** handled: GFM footnotes. ``remark-gfm`` implements them and
markdown-it's ``gfm-like`` preset does not, and the output is deeply
remark-specific (``user-content-fn-1``, ``data-footnote-ref``, a screen-reader
heading, a ``↩`` backref). A footnote in a survey question previews as its
literal source. Everything else in the recordings is byte-exact.
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML

from .html import escape

# Tags ``mdast-util-to-hast`` emits with no newline after them. markdown-it
# indents table markup; React writes it as one line.
TIGHT_TAGS = frozenset({"table", "thead", "tbody", "tr", "th", "td"})

# The classes the reference's option-label component puts on a link and on
# inline code. Written out rather than derived, and held to the recordings --
# they are that component's choices, not ours.
OPTION_LINK_CLASS = "text-blue-600 underline dark:text-blue-400"
OPTION_CODE_CLASS = "rounded bg-muted px-1 py-0.5 text-[0.85em]"


class ReactRenderer(RendererHTML):
    """Serialize markdown-it's tokens as ``renderToStaticMarkup`` would.

    Everything here is a difference from markdown-it's own HTML renderer that
    a golden proves. Nothing is stylistic.
    """

    # The class a fenced block with no language carries. None on this surface;
    # OptionRenderer has one, for the reason in the module docstring.
    default_code_class: str | None = None

    def renderToken(self, tokens, idx, options, env):
        result = super().renderToken(tokens, idx, options, env)
        # React writes void elements as `<img/>`; markdown-it as `<img />`.
        if tokens[idx].nesting == 0:
            result = result.replace(" />", "/>", 1)
        if tokens[idx].tag in TIGHT_TAGS and result.endswith("\n"):
            result = result[:-1]
        return result

    def renderAttrs(self, token):
        # markdown-it's escaper leaves `'` alone; React escapes it everywhere,
        # attributes included.
        if not token.attrs:
            return ""
        return "".join(
            f' {name}="{escape(value)}"' for name, value in token.attrItems()
        )

    def text(self, tokens, idx, options, env):
        return escape(tokens[idx].content)

    def code_inline(self, tokens, idx, options, env):
        token = tokens[idx]
        return f"<code{self.renderAttrs(token)}>{escape(token.content)}</code>"

    def fence(self, tokens, idx, options, env):
        token = tokens[idx]
        info = (token.info or "").strip()
        language = info.split()[0] if info else ""
        if language:
            css_class = f"language-{language}"
        else:
            css_class = self.default_code_class
        attrs = f' class="{escape(css_class)}"' if css_class else ""
        return f"<pre><code{attrs}>{escape(token.content)}</code></pre>\n"

    def image(self, tokens, idx, options, env):
        token = tokens[idx]
        token.attrSet("alt", self.renderInlineAsText(token.children, options, env))
        return self.renderToken(tokens, idx, options, env)

    def hardbreak(self, tokens, idx, options, env):
        return "<br/>\n"

    def softbreak(self, tokens, idx, options, env):
        return "\n"

    def hr(self, tokens, idx, options, env):
        return "<hr/>\n"

    # remark-gfm maps `~~x~~` to <del>; markdown-it to <s>.
    def s_open(self, tokens, idx, options, env):
        return "<del>"

    def s_close(self, tokens, idx, options, env):
        return "</del>"

    def html_block(self, tokens, idx, options, env):
        """A raw HTML block, escaped and unwrapped.

        ``remark`` parses it as an mdast ``html`` node and ``react-markdown``,
        with no ``rehype-raw``, renders that as text -- so it is escaped, and
        unlike a paragraph of the same characters it gets no ``<p>`` around it.
        Parsing it as a block (rather than disabling HTML and letting it fall
        through as a paragraph) is what reproduces the missing wrapper.
        """
        return escape(tokens[idx].content.rstrip("\n"))

    def html_inline(self, tokens, idx, options, env):
        return escape(tokens[idx].content)


class OptionRenderer(ReactRenderer):
    """The option-label surface: markdown restricted to what fits in a label.

    Paragraphs become spans, and links and inline code carry the classes the
    reference's option-label component gives them. Anything the parser makes a block of -- a
    list, a heading -- stays a block, which is how an author finds out it does
    not belong in an option.
    """

    default_code_class = OPTION_CODE_CLASS

    def paragraph_open(self, tokens, idx, options, env):
        tokens[idx].tag = "span"
        return self.renderToken(tokens, idx, options, env)

    def paragraph_close(self, tokens, idx, options, env):
        tokens[idx].tag = "span"
        return self.renderToken(tokens, idx, options, env)

    def link_open(self, tokens, idx, options, env):
        # Attribute order is the component's: className, target and rel are
        # written before `{...props}`, so href and title follow them.
        return (
            f'<a class="{escape(OPTION_LINK_CLASS)}" target="_blank"'
            f' rel="noreferrer"{self.renderAttrs(tokens[idx])}>'
        )

    def code_inline(self, tokens, idx, options, env):
        token = tokens[idx]
        if not token.attrs:
            token.attrSet("class", OPTION_CODE_CLASS)
        return super().code_inline(tokens, idx, options, env)


def _parser(renderer_cls: type[RendererHTML]) -> MarkdownIt:
    """A markdown-it configured to parse what ``remark-gfm`` parses.

    ``gfm-like`` is the preset that turns on tables, strikethrough and
    autolinking, which is what ``remark-gfm`` adds over CommonMark. ``html`` is
    on so raw HTML is *parsed* as HTML -- the renderers above escape it, which
    is what react-markdown does with it; leaving it off would wrap an HTML block
    in a paragraph that the live page does not draw.
    """
    return MarkdownIt("gfm-like", {"html": True}, renderer_cls=renderer_cls)


_QUESTION_PARSER = _parser(ReactRenderer)
_OPTION_PARSER = _parser(OptionRenderer)


def render_question_text(text: object) -> str:
    """Render question text as the respond page's ``QuestionText`` renders it."""
    return _QUESTION_PARSER.render(str(text or "")).rstrip("\n")


def render_option_text(text: object) -> str:
    """Render an option label the way the reference's option-label component does.

    Only for the renderers that draw a label themselves. A question configured
    as a dropdown shows the option string as-is -- a ``<select>`` holds text and
    nothing else -- so the dropdown branch must not call this.
    """
    return _OPTION_PARSER.render(str(text or "")).rstrip("\n")
