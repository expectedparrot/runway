"""Tests for the hand-written stylesheet rules that show a chosen answer.

Everything else in ``questions.css`` is generated from classes a component
emits, so the parity tests cover it. These rules are authored, and they exist
because a preview is static: the reference hides the real input and publishes
which control is chosen as ``data-checked`` / ``data-unchecked`` attributes it
rewrites on re-render, so in a preview every control stays ``data-unchecked``
however many times it is clicked. Without these rules a click would change
nothing on screen at all.

Their whole design is about how they win -- over the utility they replace -- and
how they lose, to a survey's own CSS. Neither is visible from the markup, so it
is asserted here or nowhere.

Runs under pytest, or directly: python tests/test_selected_state.py
"""

from __future__ import annotations

from pathlib import Path

from runway import render_question
from runway import renderer as runway_renderer

STYLESHEET = (Path(runway_renderer.__file__).parent / "assets/questions.css").read_text(
    encoding="utf-8"
)

# The control's outline and fill: one rule each, at one class of weight.
CONTROL_RULES = (
    ".edsl-radio-control:where(:has(.edsl-radio:checked)){",
    ".edsl-checkbox-control:where(:has(.edsl-checkbox:checked)){",
)

# The dot and the tick, which are hidden by a variant utility rather than by a
# plain one -- see the weight test below.
INDICATOR_RULE = (
    ".edsl-checkbox:checked~.edsl-checkbox-indicator,"
    ".edsl-radio:checked~.edsl-radio-indicator{display:revert}"
)

# What the indicator rule has to outrank: a class and an attribute selector,
# emitted after custom CSS as every variant utility is.
HIDDEN_UTILITY = r".data-\[unchecked\]\:hidden[data-unchecked]{display:none}"


def _without_where(selector: str) -> str:
    """Drop every ``:where(...)`` and its contents, nesting included.

    A regex cannot: ``:where(:has(:checked))`` nests, and one that stopped at
    the first closing paren would leave the second behind and quietly report
    the wrong weight.
    """
    out, index = [], 0
    while index < len(selector):
        if selector.startswith(":where(", index):
            depth, index = 1, index + len(":where(")
            while depth:
                depth += {"(": 1, ")": -1}.get(selector[index], 0)
                index += 1
            continue
        out.append(selector[index])
        index += 1
    return "".join(out)


def test_the_rules_ship():
    """In the vendored stylesheet, which is what the package actually serves."""
    for rule in CONTROL_RULES:
        assert rule in STYLESHEET, rule
    assert INDICATOR_RULE in STYLESHEET


def test_the_control_rules_carry_one_class_of_weight():
    """`:where()` is load-bearing, not decoration.

    At one class these tie with the plain utilities they override and win on
    order -- the cascade the live page has, where the checked classes simply
    replace the unchecked ones. Spelled as plain selectors they would outrank a
    survey's own `.edsl-radio-control` rule, where the live page's styling never
    does.
    """
    for rule in CONTROL_RULES:
        bare = _without_where(rule.rstrip("{")).strip()
        assert bare in (".edsl-radio-control", ".edsl-checkbox-control"), bare


def test_the_control_rules_are_emitted_after_what_they_override():
    """Winning on order only works if the order is that way round."""
    for rule in CONTROL_RULES:
        at = STYLESHEET.index(rule)
        for utility in (".border-gray-500{", ".bg-white{"):
            assert STYLESHEET.index(utility) < at, (rule, utility)


def test_the_indicator_rule_is_won_on_weight_instead():
    """It cannot be won on order: the utility hiding the dot is a variant one,
    and Tailwind emits those after custom CSS whatever it is written next to.

    So this one is deliberately not wrapped in `:where()` -- three compound
    selectors against that utility's two. The cost is stated in `base.css`: a
    survey hiding `.edsl-radio-indicator` in its own CSS would not be honoured
    here, where on the live page it would.
    """
    assert HIDDEN_UTILITY in STYLESHEET
    assert ":where(" not in INDICATOR_RULE
    assert STYLESHEET.index(HIDDEN_UTILITY) > STYLESHEET.index(INDICATOR_RULE)


def test_no_row_highlight_is_invented_anywhere():
    """The rules reach the control and stop there.

    An earlier version highlighted the whole option row for the stacked matrix
    and the carousel, because the reference drew those rows as cards whose
    classes it swapped. It draws them as plain rows now, like every other
    question's options, so a rule reaching `.edsl-option` would draw a
    highlight no live survey draws.
    """
    assert ".edsl-option:where(:has(:checked))" not in STYLESHEET


def test_the_rules_reach_what_the_questions_emit():
    """Not just present in the stylesheet -- scoped to classes really rendered."""
    choice = render_question(
        {
            "question_name": "q",
            "question_type": "multiple_choice",
            "question_text": "T",
            "question_options": ["a", "b"],
        }
    )
    assert "edsl-radio-control" in choice and "edsl-radio-indicator" in choice

    checkbox = render_question(
        {
            "question_name": "q",
            "question_type": "checkbox",
            "question_text": "T",
            "question_options": ["a", "b"],
        }
    )
    assert "edsl-checkbox-control" in checkbox and "edsl-checkbox-indicator" in checkbox

    # The matrix asks for the same control at a second size, in both the layouts
    # it draws -- the grid and the carousel. The carousel is checked explicitly
    # because it was once left out of a rule the stacked list had.
    matrix = {
        "question_name": "q",
        "question_type": "matrix",
        "question_text": "T",
        "question_items": ["row"],
        "question_options": ["a", "b"],
    }
    for schema in (None, {"format": {"type": "carousel"}}):
        html = render_question(matrix, schema)
        assert "edsl-radio-control" in html and "edsl-radio-indicator" in html


def test_a_surveys_own_css_is_still_emitted_last():
    """What lets a matched-weight rule be overridden at all."""
    page = runway_renderer.render_page(
        {
            "question_name": "q",
            "question_type": "multiple_choice",
            "question_text": "T",
            "question_options": ["a", "b"],
        },
        custom_css=".edsl-radio-control{border-color:red}",
    )
    assert page.index(CONTROL_RULES[0]) < page.index(
        ".edsl-radio-control{border-color:red}"
    )


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
