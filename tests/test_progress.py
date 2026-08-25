"""Tests for the progress indicator: the markup, and the payload behind it.

Two halves, because there are two ways to get this wrong. The markup is
recorded from the reference component into ``react_goldens.json`` and
compared byte for byte here. The payload -- which of the three renderings a
survey's config produces, and what it says about this position -- is decided by
``progress.resolve``, which mirrors the live server's resolver; those tests
assert on payloads rather than on HTML, since that is where the decision is.

Runs under pytest, or directly:
    python tests/test_progress.py
"""

from __future__ import annotations

import goldens
from runway import progress, render_progress

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

PROGRESS_CASES = sorted(k for k, v in CASES.items() if v["kind"] == "progress")
PAYLOADS = [CASES[name]["progress"] for name in PROGRESS_CASES]

# A survey to resolve steps against: four items, one of them an instruction, so
# a boundary can land on something that is not a question.
ITEMS = ["intro", "commute_mode", "commute_time", "commute_breakdown"]


def stepped(*boundaries: tuple[str | None, str | None], marker: str = "number") -> dict:
    """A steps config from ``(label, complete_after)`` pairs."""
    return {
        "type": "steps",
        "marker": marker,
        "steps": [
            {"label": label, "complete_after": after} for label, after in boundaries
        ],
    }


def statuses(payload: dict) -> list[str]:
    return [step["status"] for step in payload["steps"]]


# --------------------------------------------------------------------------
# The markup
# --------------------------------------------------------------------------


def test_every_recorded_payload_matches_react():
    for name in PROGRESS_CASES:
        assert render_progress(CASES[name]["progress"]) == GOLDENS[name], name


def test_recorded_payloads_cover_every_rendering():
    # Guards the case list rather than the renderer: byte parity is only worth
    # as much as the set of things it was recorded for.
    assert {payload["type"] for payload in PAYLOADS} == {"bar", "hidden", "steps"}

    bars = [payload for payload in PAYLOADS if payload["type"] == "bar"]
    fractions = [bar["fraction"] for bar in bars]
    assert 0 in fractions and 1 in fractions, "record the bar at both ends"
    assert any(fraction * 100 % 1 for fraction in fractions), (
        "record a fraction that does not divide evenly, where the label rounds"
    )
    assert any(bar["label"] is None for bar in bars), "record a bar with no label"

    steps = [payload for payload in PAYLOADS if payload["type"] == "steps"]
    assert {payload["marker"] for payload in steps} == {"number", "dot"}
    assert {step["status"] for payload in steps for step in payload["steps"]} == set(
        progress.STEP_STATUSES
    ), "record a step in every status"


def test_percent_label_rounds_like_javascript():
    # Python's round() is banker's rounding: round(12.5) == 12, where
    # Math.round(12.5) == 13. An 8-question survey hits this on question 2.
    # The golden is the component's own output, so this asserts on what JS did.
    assert 'aria-valuenow="13"' in GOLDENS["progress_bar_eighth"]
    assert 'aria-valuetext="13%"' in GOLDENS["progress_bar_eighth"]
    assert render_progress(progress.bar(0.125)) == GOLDENS["progress_bar_eighth"]


def test_the_value_and_its_label_cannot_disagree():
    # The component rounds to a whole percent before drawing anything, so the
    # bar's value, its accessible text and its caption are one number.
    html = render_progress(progress.bar(1 / 3))
    assert 'aria-valuenow="33" aria-valuetext="33%"' in html
    assert 'data-value="33"' in html and ">33%</span>" in html


def test_an_unconfigured_survey_draws_the_bar_at_zero():
    # What a survey rendered before the indicator was configurable, and what a
    # single-question preview shows.
    assert render_progress() == GOLDENS["progress_bar_zero"]
    assert render_progress(None) == GOLDENS["progress_bar_zero"]


def test_hidden_renders_nothing_at_all():
    assert render_progress(progress.HIDDEN) == ""


def test_a_fraction_outside_the_range_is_clamped():
    assert render_progress(progress.bar(1.4)) == GOLDENS["progress_bar_complete"]
    assert render_progress(progress.bar(-0.2)) == GOLDENS["progress_bar_zero"]


def test_an_unknown_step_status_renders_as_upcoming():
    # A status from a newer server -- "skipped" is the expected next one -- must
    # not leave a marker with no shape. The component makes the same fallback.
    html = render_progress(
        {
            "type": "steps",
            "marker": "number",
            "steps": [
                {"label": "Skipped over", "status": "skipped"},
                {"label": "Here", "status": "current"},
            ],
        }
    )
    assert "edsl-progress-step-upcoming" in html
    assert "not yet reached" in html
    assert "edsl-progress-step-skipped" not in html


def test_an_unknown_marker_style_renders_as_a_numbered_step():
    html = render_progress(
        {
            "type": "steps",
            "marker": "chevron",
            "steps": [
                {"label": None, "status": "current"},
                {"label": None, "status": "upcoming"},
            ],
        }
    )
    assert "h-8 w-8 border-2 text-sm font-medium" in html
    assert ">1</span>" in html


def test_step_labels_are_escaped():
    # Author-supplied text, escaped the way the component escapes it -- and it
    # appears twice, in the visible label and in the screen-reader line.
    html = render_progress(
        {
            "type": "steps",
            "marker": "number",
            "steps": [
                {"label": "Anything you'd add", "status": "current"},
                {"label": None, "status": "upcoming"},
            ],
        }
    )
    assert html.count("Anything you&#x27;d add") == 2
    assert "Anything you'd add" not in html


# --------------------------------------------------------------------------
# Which payload a survey's config produces
# --------------------------------------------------------------------------


def test_unconfigured_resolves_to_a_labelled_bar():
    # Absent has to keep meaning "the bar", or every survey written before the
    # field existed would preview without the indicator it renders.
    assert progress.resolve(None, 0, 4, ITEMS) == progress.bar(0.0)
    assert progress.resolve({}, 0, 4, ITEMS) == progress.bar(0.0)


def test_the_bar_measures_what_is_behind_the_respondent():
    # A respondent looking at the first question has done none of the survey.
    fractions = [
        progress.resolve(None, index, 4, ITEMS)["fraction"] for index in range(4)
    ]
    assert fractions == [0.0, 0.25, 0.5, 0.75]


def test_an_absent_bar_label_differs_from_an_explicit_null():
    # Absent means "the default caption"; null means "a bar with none".
    assert progress.resolve({"type": "bar"}, 1, 4, ITEMS)["label"] == {
        "type": "percent"
    }
    assert (
        progress.resolve({"type": "bar", "label": None}, 1, 4, ITEMS)["label"] is None
    )


def test_hidden_resolves_to_hidden():
    assert progress.resolve({"type": "hidden"}, 2, 4, ITEMS) == {"type": "hidden"}


def test_an_unknown_rendering_falls_back_to_the_bar():
    # A config written for a newer renderer previews as something.
    assert progress.resolve({"type": "chevrons"}, 1, 4, ITEMS) == progress.bar(0.25)


def test_steps_mark_where_the_respondent_is_not_what_they_finished():
    config = stepped(("One", "commute_mode"), ("Two", "commute_time"), ("Three", None))
    # On the very first item nothing is finished, yet the stepper already sits on
    # step one -- the two readings measure the same position from opposite ends.
    assert statuses(progress.resolve(config, 0, 4, ITEMS)) == [
        "current",
        "upcoming",
        "upcoming",
    ]
    assert statuses(progress.resolve(config, 2, 4, ITEMS)) == [
        "complete",
        "current",
        "upcoming",
    ]
    assert statuses(progress.resolve(config, 3, 4, ITEMS)) == [
        "complete",
        "complete",
        "current",
    ]


def test_a_step_may_end_on_an_instruction():
    # Boundaries are survey items, not questions: "intro" is an instruction, and
    # the step that ends on it still resolves.
    config = stepped(("One", "intro"), ("Two", None))
    assert statuses(progress.resolve(config, 1, 4, ITEMS)) == ["complete", "current"]


def test_a_step_naming_a_deleted_item_is_dropped():
    # Rather than drawn as a marker the respondent could never pass.
    config = stepped(
        ("One", "commute_mode"), ("Gone", "deleted_question"), ("Three", None)
    )
    resolved = progress.resolve(config, 0, 4, ITEMS)
    assert [step["label"] for step in resolved["steps"]] == ["One", "Three"]


def test_too_few_resolvable_steps_fall_back_to_the_bar():
    # One marker is not a progress indicator, and an empty header is worse than
    # the bar the survey would otherwise have drawn.
    config = stepped(("One", "commute_mode"), ("Gone", "deleted_question"))
    assert progress.resolve(config, 1, 4, ITEMS) == progress.bar(0.25)


def test_the_final_step_holds_when_items_follow_its_boundary():
    # Every step given an explicit boundary, with questions after the last one:
    # hold on the final step rather than reading as finished from the middle.
    config = stepped(("One", "intro"), ("Two", "commute_mode"))
    assert statuses(progress.resolve(config, 3, 4, ITEMS)) == ["complete", "current"]


def test_steps_authored_out_of_survey_order_stay_coherent():
    # The current step is the first whose boundary is still ahead, not a count of
    # the boundaries behind -- so a mis-ordered config still marks one step.
    config = stepped(("Later", "commute_breakdown"), ("Earlier", "intro"))
    assert statuses(progress.resolve(config, 1, 4, ITEMS)) == ["current", "upcoming"]


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
