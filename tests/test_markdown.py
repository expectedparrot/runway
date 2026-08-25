"""Tests for the two markdown surfaces.

Byte parity with the recordings is already guaranteed elsewhere:
``test_every_recorded_question_case_matches`` compares this package against
every recorded case, markdown ones included. These tests are the other half --
what the two surfaces *are*, stated so the difference between them survives
someone reading only one of the renderers.

Question text renders into a ``<div>`` and may emit anything. An option label
renders inside the ``<label>`` around a radio, which admits phrasing content
only, so paragraphs become spans and links and inline code carry classes of
their own. Same parse, two serializations.

Runs under pytest, or directly:
    python tests/test_markdown.py
"""

from __future__ import annotations

from runway import render_question
from runway.markdown import render_option_text, render_question_text

# --------------------------------------------------------------------------
# The two surfaces
# --------------------------------------------------------------------------


def test_question_text_wraps_a_paragraph_in_p():
    assert (
        render_question_text("Really **now**?") == "<p>Really <strong>now</strong>?</p>"
    )


def test_an_option_wraps_a_paragraph_in_span():
    # A <p> inside the <label> around a radio would be invalid, and would drop
    # the label below its input instead of keeping it on the same line.
    assert (
        render_option_text("**Strongly** agree")
        == "<span><strong>Strongly</strong> agree</span>"
    )


def test_an_options_second_paragraph_is_also_a_span():
    assert (
        render_option_text("First.\n\nSecond.")
        == "<span>First.</span>\n<span>Second.</span>"
    )


def test_a_block_element_in_an_option_stays_a_block():
    # Only paragraphs are remapped. A list in a label renders as a list --
    # which is how an author discovers it does not belong in one.
    assert (
        render_option_text("- one\n- two") == "<ul>\n<li>one</li>\n<li>two</li>\n</ul>"
    )


# --------------------------------------------------------------------------
# Links and code: styled in an option, plain in question text
# --------------------------------------------------------------------------


def test_an_option_link_is_styled_and_opens_a_new_tab():
    # A link inside a label is a control inside a control: clicking it both
    # follows the link and selects the option, so it must not take the
    # respondent away from the survey they are part-way through.
    html = render_option_text("See [the terms](https://example.com)")
    assert (
        '<a class="text-blue-600 underline dark:text-blue-400" target="_blank"'
        ' rel="noreferrer" href="https://example.com">the terms</a>' in html
    )


def test_a_question_text_link_carries_none_of_that():
    html = render_question_text("See [our policy](https://example.com)")
    assert '<a href="https://example.com">our policy</a>' in html


def test_inline_code_is_styled_in_an_option_only():
    assert 'class="rounded bg-muted px-1 py-0.5 text-[0.85em]"' in render_option_text(
        "Run `git status`"
    )
    assert "<code>SELECT *</code>" in render_question_text("Type `SELECT *`")


def test_a_language_beats_the_styled_class_on_a_fenced_block():
    # The reference's option-label component writes
    # `<code className="..." {...props}/>`: the spread is last, so a fenced
    # block's own language class wins. A fence with no
    # language has no class in props, so the styled one survives. Both branches
    # are recorded; this says which is which.
    assert '<code class="language-py">' in render_option_text("```py\nx = 1\n```")
    assert '<code class="rounded bg-muted' in render_option_text("```\nx = 1\n```")
    # Question text has no styled class to lose either way.
    assert '<code class="language-py">' in render_question_text("```py\nx = 1\n```")
    assert "<pre><code>x = 1\n</code></pre>" == render_question_text("```\nx = 1\n```")


# --------------------------------------------------------------------------
# Serializing the way React does, not the way markdown-it does
# --------------------------------------------------------------------------


def test_quotes_are_escaped_reacts_way():
    # MarkupSafe would write &#39;/&#34; here, and markdown-it leaves ' alone.
    assert render_question_text('Don\'t say "hi" & <b>x</b>') == (
        "<p>Don&#x27;t say &quot;hi&quot; &amp; &lt;b&gt;x&lt;/b&gt;</p>"
    )


def test_void_elements_have_no_space_before_the_slash():
    assert "<br/>" in render_question_text("one  \ntwo")
    assert "<hr/>" in render_question_text("a\n\n---\n\nb")
    assert '<img src="x.png" alt="a"/>' in render_question_text("![a](x.png)")


def test_strikethrough_is_del_not_s():
    assert render_question_text("~~wrong~~") == "<p><del>wrong</del></p>"


def test_a_table_carries_no_newlines_between_its_cells():
    assert render_question_text("| a |\n| - |\n| 1 |") == (
        "<table><thead><tr><th>a</th></tr></thead>"
        "<tbody><tr><td>1</td></tr></tbody></table>"
    )


def test_a_raw_html_block_is_escaped_and_unwrapped():
    # react-markdown runs without rehype-raw, so remark's `html` node reaches
    # React as text -- escaped, and with no paragraph around it, unlike a
    # paragraph of the same characters.
    assert render_question_text('<div class="x">hi</div>') == (
        "&lt;div class=&quot;x&quot;&gt;hi&lt;/div&gt;"
    )


def test_text_that_only_looks_like_markdown_is_left_alone():
    assert render_question_text("snake_case_word and 2 * 3 * 4 = 24") == (
        "<p>snake_case_word and 2 * 3 * 4 = 24</p>"
    )


def test_empty_text_renders_nothing():
    for value in ("", None):
        assert render_question_text(value) == ""
        assert render_option_text(value) == ""


# --------------------------------------------------------------------------
# Where markdown does and does not apply
# --------------------------------------------------------------------------


def test_a_dropdown_shows_its_options_literally():
    # A <select> holds text and nothing else. Rendering markdown into one is
    # impossible, and quietly swapping the layout would hide from the author
    # that the two settings do not combine.
    html = render_question(
        {
            "question_name": "q",
            "question_type": "multiple_choice",
            "question_text": "Pick **one**",
            "question_options": ["**Strongly** agree"],
        },
        {"format": {"type": "dropdown"}},
    )
    assert ">**Strongly** agree</option>" in html
    # ...while the question text above it is markdown either way.
    assert "<p>Pick <strong>one</strong></p>" in html


def test_footnotes_are_the_known_gap():
    """remark-gfm implements GFM footnotes; markdown-it's gfm-like does not.

    Pinned rather than left to be discovered: the live page draws a footnote
    with a section, a screen-reader heading and a backref, and the preview
    shows the author's literal source instead. Recording the gap here is what
    stops it being mistaken for a bug in a survey.
    """
    html = render_question_text("Text[^1]\n\n[^1]: The note.")
    assert "[^1]" in html
    assert "data-footnote-ref" not in html


def _main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc or '(assertion failed)'}")
        else:
            print(f"ok   {name}")
    print("\n" + ("all passed" if not failures else f"{failures} failure(s)"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
