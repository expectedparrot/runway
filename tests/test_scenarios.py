"""Binding a survey to a scenario, and what a bundle does with several.

Two halves. The first is the piping itself: what resolves, what deliberately
does not, and what happens to a name nothing can resolve -- the interesting
case, because both of its answers are silent ones.

The second is the bundle. A scenario is a binding and a binding is a rendering,
so a survey bound to three scenarios is three surveys; the questions that differ
between them are repeated and the ones that do not are shared. The sharpest test
here is `test_the_exclusive_positions_differ_between_panels`, which is the case
the exclusive options moved onto the panel for.

Uses examples/scenario_survey.json, whose three questions cover all three
shapes: one pipes a word, one pipes its whole option list to lists of different
lengths, and one pipes nothing at all.

Runs under pytest, or directly: python tests/test_scenarios.py
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import examples
from runway import scenarios
from runway.renderer import render_bundle
from runway.survey import (
    SurveyLoadError,
    item_names,
    load,
    load_schema,
    output_paths,
    previewable,
    render_survey,
)

EXAMPLE = examples.EXAMPLES / "scenario_survey.json"


def _survey() -> tuple[list[dict], dict, list[tuple[int, dict]]]:
    questions, schema = examples.load_example(EXAMPLE)
    chosen = scenarios.load_selection(examples.scenarios_path(EXAMPLE), None)
    return questions, schema, chosen


def _a_question(text: str, **extra) -> dict:
    return {
        "question_name": "q",
        "question_type": "free_text",
        "question_text": text,
        **extra,
    }


def _pipe_one(question: dict, scenario: dict, names: list[str] | None = None) -> dict:
    names = names if names is not None else ["q", "earlier"]
    return scenarios.pipe_question(
        question, scenario, scenarios.replacements(scenario, names)
    )


# --------------------------------------------------------------------------
# The replacement dictionary
# --------------------------------------------------------------------------


def test_both_spellings_of_a_key_resolve():
    """The live page exposes every non-file key twice, bare and namespaced, and
    both are in real surveys."""
    piped = _pipe_one(
        _a_question("{{ city }} and {{ scenario.city }}"), {"city": "Boston"}
    )
    assert piped["question_text"] == "Boston and Boston"


def _a_raw_file_value(path: str = "x.png") -> dict:
    """A FileStore as a *saved scenario list* holds one, before any media pass.

    The shape this package is actually given. Spelled out rather than
    abbreviated because an abbreviation is what let a detection bug live: a
    fixture that invented an `is_file_store` flag passed against a predicate
    that no scenario off a researcher's disk ever matched.
    """
    return {
        "path": path,
        "base64_string": "iVBORw0KGgo=",
        "binary": True,
        "suffix": "png",
        "mime_type": "image/png",
        "external_locations": {},
        "extracted_text": None,
    }


def _a_resolved_file_value() -> dict:
    """A file value that has already been resolved for display, and so is flagged.

    Nothing here produces this shape -- resolving media takes a fetch a preview
    does not make -- but it is the shape a file is recognized by once it has
    been, so the predicate has to keep matching it.
    """
    return {
        "is_file_store": True,
        "file_store_type": "png",
        "file_name": "swatch.png",
        "mime_type": "image/png",
    }


def test_a_file_key_is_the_marker_and_is_absent_from_the_namespace():
    """The marker is the text form the live page holds before its own media
    pass, which this package does not have. Absent from the namespace because
    it is absent there too -- `{{ scenario.photo }}` is undefined on the live
    page, and inventing a value for it here would preview a page nobody gets."""
    for value in (_a_raw_file_value(), _a_resolved_file_value()):
        scenario = {"photo": value, "city": "Austin"}
        replacements = scenarios.replacements(scenario, [])
        assert replacements["photo"] == "<see file photo>"
        assert "photo" not in replacements["scenario"]
        assert replacements["scenario"] == {"city": "Austin"}


def test_a_file_key_survives_the_trip_through_a_saved_scenario_list():
    """End to end, because the bug this covers lived *between* the two halves.

    `replacements` was correct and its unit test passed; what no test held was
    that `load` hands it a live `FileStore` object rather than the dict the
    live page works with, so the predicate matched nothing on the command line.
    Only loading a real saved file exercises that seam.
    """
    from edsl.scenarios import FileStore, Scenario, ScenarioList

    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / "swatch.png"
        image.write_bytes(bytes.fromhex("89504e470d0a1a0a"))  # a PNG magic number
        saved = Path(tmp) / "list"
        ScenarioList(
            [Scenario({"city": "Austin", "photo": FileStore(str(image), binary=True)})]
        ).save(str(saved))

        scenario = scenarios.load(saved.with_suffix(".ep"))[0]

    assert scenarios._is_file_value(scenario["photo"]), scenario["photo"]
    assert scenarios.replacements(scenario, [])["photo"] == "<see file photo>"
    assert scenarios.label(0, scenario) == "0 — city=Austin, photo=<file>"


def test_an_ordinary_scenario_value_is_not_taken_for_a_file():
    """A miss costs a base64 dump in the question; a false positive costs a key
    replaced by a marker and dropped from the namespace."""
    assert not scenarios._is_file_value({"path": "x.png"})
    assert not scenarios._is_file_value({"city": "Boston"})
    assert not scenarios._is_file_value({"is_file_store": False, "city": "B"})
    assert not scenarios._is_file_value("Boston")
    assert not scenarios._is_file_value(["Boston"])


# --------------------------------------------------------------------------
# The undefined-name trap
#
# `QuestionBase.render` renders a question's text as one template, and reading
# an attribute off an undefined name discards the entire render -- it warns
# rather than raising. `{{ agent.name }}` and `{{ q1.answer }}` are both that
# shape, so without a stand-in for them a survey naming either would pipe
# nothing at all, and look exactly like an unpiped preview while doing it.


def test_a_deferred_name_survives_beside_a_resolved_one():
    """The regression test for the trap. Both halves matter: the scenario key
    has to resolve *and* the deferred names have to come through as written."""
    piped = _pipe_one(
        _a_question("In {{ city }}: {{ agent.name }} said {{ earlier.answer }}"),
        {"city": "Boston"},
    )
    assert piped["question_text"] == (
        "In Boston: {{ agent.name }} said {{ earlier.answer }}"
    )


def test_a_filtered_deferred_name_leaves_the_whole_question_unpiped():
    """The placeholder is not a string, and this is why.

    Against a string standing in for the answer, `| length` is the length of
    the placeholder text -- a plausible wrong number with nothing to notice it
    by. Against the real one `len()` raises, edsl gives up, and the question
    previews exactly as it did before scenarios existed.
    """
    piped = _pipe_one(
        _a_question("In {{ city }}, {{ earlier.answer | length }} words"),
        {"city": "Boston"},
    )
    assert piped["question_text"] == "In {{ city }}, {{ earlier.answer | length }} words"


def test_a_name_nothing_can_resolve_is_reported_rather_than_hidden():
    """Undefined fails twice over and neither leaves a mark: `{{ typo }}`
    renders as nothing, and `{{ typo.attr }}` stops the whole question piping.
    Both are what the live page does, so `check` is where they get said."""
    question = _a_question("{{ city }} and {{ nowhere }}")
    assert scenarios.unresolved(question, {"city": "B"}, ["q"]) == ["nowhere"]
    assert scenarios.unresolved(question, {"city": "B", "nowhere": 1}, ["q"]) == []
    # A deferred name is not one of these: it has somewhere to go.
    assert scenarios.unresolved(
        _a_question("{{ agent.x }} {{ earlier.answer }}"), {}, ["earlier"]
    ) == []


# --------------------------------------------------------------------------
# Piping a question
# --------------------------------------------------------------------------


def test_a_templated_option_list_resolves_to_a_list():
    """`render` cannot do this one -- it would substitute the list's text form
    into a string field -- so the option processor runs first, as it does on the
    live page."""
    piped = _pipe_one(
        {
            "question_name": "q",
            "question_type": "checkbox",
            "question_text": "Which?",
            "question_options": "{{ brands }}",
        },
        {"brands": ["Apple", "Nokia"]},
    )
    assert piped["question_options"] == ["Apple", "Nokia"]


def test_an_unresolvable_option_list_becomes_edsl_placeholders():
    """Not this package's invention, and not its explanatory line either.

    edsl's option processor answers an option template it cannot resolve with
    three named placeholders, and the live page runs the same processor -- so
    these are the options a respondent would be shown. Left to fall back to the
    unpiped string, the preview would show the "each item will be shown as a
    separate option" line for a question the live page fills with placeholders.
    """
    piped = _pipe_one(
        {
            "question_name": "q",
            "question_type": "checkbox",
            "question_text": "Which?",
            "question_options": "{{ nothing_supplies_this }}",
        },
        {"city": "B"},
    )
    assert all("Placeholder" in option for option in piped["question_options"])


def test_piping_leaves_a_question_that_references_nothing_exactly_as_it_was():
    """The round trip through edsl -- from_dict, render, to_dict -- has to be
    lossless, or binding a scenario would quietly rewrite questions that have
    nothing to do with it.

    Over every example, so a question type whose dict does not survive that trip
    cannot slip by. Questions that *do* reference something are excluded rather
    than asserted about: an empty scenario resolves none of their keys, and what
    happens then is `test_a_name_nothing_can_resolve_...`'s business.
    """
    checked = 0
    for survey in examples.paths():
        questions = load(survey)
        for before, after in zip(
            questions, scenarios.pipe(questions, {}), strict=True
        ):
            if scenarios.references(before):
                continue
            assert before == after, f"{survey.name}: {before.get('question_name')}"
            checked += 1
    assert checked > 20, "the sweep stopped covering the examples"


def test_instructions_are_passed_through_untouched():
    """They are not questions, edsl does not render them through QuestionBase,
    and this package does not preview them -- but they hold their place, because
    position is counted over every item."""
    instruction = {"edsl_class_name": "Instruction", "name": "intro", "text": "Hi"}
    piped = scenarios.pipe([instruction, _a_question("{{ city }}")], {"city": "B"})
    assert piped[0] == instruction
    assert piped[1]["question_text"] == "B"


# --------------------------------------------------------------------------
# Selecting scenarios
# --------------------------------------------------------------------------


def test_indices_and_ranges_are_accepted_in_the_order_given():
    assert scenarios.parse_indices("0", 10) == [0]
    assert scenarios.parse_indices("0-3", 10) == [0, 1, 2, 3]
    assert scenarios.parse_indices("7,0,2", 10) == [7, 0, 2]
    assert scenarios.parse_indices("0-2,7", 10) == [0, 1, 2, 7]
    # Said twice is a list with something said twice, not a collision.
    assert scenarios.parse_indices("1,1,2", 10) == [1, 2]


def test_a_selection_that_cannot_be_met_says_why():
    for spec in ("99", "a-b", "3-1", ""):
        try:
            scenarios.parse_indices(spec, 10)
        except ValueError as exc:
            assert str(exc)
        else:  # pragma: no cover - the assertion is that this does not happen
            raise AssertionError(f"{spec!r} was accepted")


def test_a_long_list_is_refused_rather_than_truncated():
    """A silently shortened preview is one that lies about which scenarios were
    checked."""
    many = {
        "edsl_class_name": "ScenarioList",
        "scenarios": [
            {"edsl_class_name": "Scenario", "n": index}
            for index in range(scenarios.MAX_SCENARIOS + 1)
        ],
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "many.json"
        path.write_text(__import__("json").dumps(many), encoding="utf-8")
        try:
            scenarios.load_selection(path, None)
        except SurveyLoadError as exc:
            assert "--scenario-index" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("a list past the guard was accepted")
        # And named explicitly, it renders.
        assert len(scenarios.load_selection(path, "0-3")) == 4


def test_a_label_leads_with_the_index_it_is_known_by():
    """The index is the identity -- it is how the live survey names a scenario,
    so it is the number worth carrying back to a bug report."""
    assert scenarios.label(17, {"city": "Austin"}) == "17 — city=Austin"
    # A list is written out rather than repr'd: quotes and brackets would spend
    # a third of the label saying nothing.
    assert "[a, b]" in scenarios.label(0, {"modes": ["a", "b"]})
    assert scenarios.label(2, {}) == "2"


# --------------------------------------------------------------------------
# The bundle
# --------------------------------------------------------------------------


def _panels(html: str) -> list[str]:
    return [
        chunk.split(">")[0]
        for chunk in html.split('<div class="preview-panel')[1:]
    ]


def _bundle() -> str:
    questions, schema, chosen = _survey()
    return render_bundle(
        previewable(questions),
        schema,
        item_names=item_names(questions),
        variants=[
            previewable(scenarios.pipe(questions, scenario))
            for _, scenario in chosen
        ],
        scenarios=[
            {"index": index, "label": scenarios.label(index, scenario)}
            for index, scenario in chosen
        ],
    )


def test_a_question_that_pipes_nothing_is_one_panel_serving_every_scenario():
    """What keeps a bundle from being questions times scenarios in size."""
    panels = [panel for panel in _panels(_bundle()) if "anything" in panel]
    assert len(panels) == 1
    assert 'data-scenario-indices="0 1 2"' in panels[0]


def test_a_question_that_pipes_is_one_panel_each():
    panels = [panel for panel in _panels(_bundle()) if 'name="familiar"' in panel]
    assert len(panels) == 3
    assert [f'data-scenario-indices="{n}"' in p for n, p in enumerate(panels)] == [
        True,
        True,
        True,
    ]


def test_the_exclusive_positions_differ_between_panels():
    """The case the positions moved onto the panel for.

    One question, one schema naming one exclusive option by text, and three
    resolved option lists of different lengths -- so the position it lands at is
    3, 1 and 4. A table keyed by question name has one slot for those, and two
    of the three panels would act on another's positions: clicking an ordinary
    option would clear the rest while the exclusive one did nothing.
    """
    panels = [panel for panel in _panels(_bundle()) if 'name="modes"' in panel]
    assert len(panels) == 3
    found = [
        panel.split('data-exclusive="')[1].split('"')[0] for panel in panels
    ]
    assert found == ["3", "1", "4"]


def test_a_bundle_with_no_scenarios_carries_no_scenario_markup():
    """Nothing about an ordinary render changes, which is the whole contract of
    adding this."""
    questions, schema = examples.load_example(EXAMPLE)
    html = render_bundle(
        previewable(questions), schema, item_names=item_names(questions)
    )
    # On the panels, not in the document: the page script names both attributes
    # in the branch that falls back when they are absent.
    for panel in _panels(html):
        assert "data-scenario-indices" not in panel
        assert "data-question-index" not in panel
    assert 'id="preview-scenario-select"' not in html
    # The checkbox still carries its own positions, which are not a scenario's
    # doing: unresolved options are a list of nothing to be exclusive of.
    assert 'data-exclusive=""' in html


def test_the_scenario_select_appears_only_when_bound():
    assert 'id="preview-scenario-select"' in _bundle()


# --------------------------------------------------------------------------
# Writing files
# --------------------------------------------------------------------------


def test_split_pages_are_named_per_scenario_and_agree_with_output_paths():
    """`_colliding` asks `output_paths` what a render would produce, so the two
    disagreeing would let a set through that overwrites itself."""
    questions, schema, chosen = _survey()
    with tempfile.TemporaryDirectory() as tmp:
        written = render_survey(
            questions,
            schema,
            out_dir=Path(tmp),
            split=True,
            name="scen",
            scenarios=chosen,
        )
        expected = output_paths(
            questions,
            Path(tmp),
            split=True,
            name="scen",
            scenario_indices=[index for index, _ in chosen],
        )
        assert written == expected
        assert len(written) == 9
        assert written[0].name == "scen-s00-01-familiar.html"
        assert all(path.is_file() for path in written)
        # Not deduplicated: a page whose name says scenario 2 has to exist.
        assert "Boston" in written[0].read_text(encoding="utf-8")
        assert "Chicago" in written[6].read_text(encoding="utf-8")


def test_one_scenario_names_files_the_way_no_scenario_does():
    """A segment saying "scenario 0" on the only scenario there is would be
    noise, and would rename every file of anyone who bound a single-scenario
    list."""
    questions = load(EXAMPLE)
    assert output_paths(questions, Path("."), split=True, name="s") == output_paths(
        questions, Path("."), split=True, name="s", scenario_indices=[0]
    )


def test_the_example_survey_and_its_scenarios_are_a_matched_pair():
    """The schema names an option by text that every scenario has to supply, or
    the example stops demonstrating what it is here for."""
    _, schema, chosen = _survey()
    exclusive = schema["questions"]["modes"]["exclusive_options"]
    for _, scenario in chosen:
        assert set(exclusive) <= set(scenario["transport"])


def test_the_schema_beside_the_example_is_read():
    assert load_schema(examples.schema_path(EXAMPLE))["questions"]["modes"]


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


# --------------------------------------------------------------------------
# Carousel rows under a scenario
# --------------------------------------------------------------------------


def _carousel_survey():
    question = {
        "question_name": "m",
        "question_type": "matrix",
        "edsl_class_name": "QuestionMatrix",
        "question_text": "Rate each.",
        "question_items": ["Row A", "Row B"],
        "question_options": ["{{ scenario.word }}", "No"],
    }
    schema = {"questions": {"m": {"format": {"type": "carousel"}}}}
    return question, schema


def _parked(html: str) -> dict[str, str]:
    """The parked carousel rows on a page, by the panel they belong to."""
    return dict(
        re.findall(
            r'<template class="preview-matrix-carousel-options"[^>]*'
            r'data-scenario-indices="([^"]*)"[^>]*>(.*?)</template>',
            html,
            re.S,
        )
    )


def test_carousel_rows_are_parked_per_panel_and_carry_that_binding():
    """A carousel draws one row and parks the rest, and the parked ones have to
    be the same binding as the drawn one.

    Two failures at once if they are not. The rows go up unpiped -- the visible
    row shows the scenario's wording and the next row shows the template it came
    from -- and, because the script *moves* them out of the template as it
    mounts them, a single shared set leaves every panel after the first with no
    options at all.
    """
    question, schema = _carousel_survey()
    variants = [
        scenarios.pipe([question], one) for one in ({"word": "Oui"}, {"word": "Ja"})
    ]
    html = render_bundle(
        [question],
        schema,
        variants=variants,
        scenarios=[{"index": 0, "label": "0"}, {"index": 1, "label": "1"}],
        title="t",
    )
    parked = _parked(html)
    assert sorted(parked) == ["0", "1"], "one parked set per panel"
    assert "Oui" in parked["0"] and "Ja" not in parked["0"]
    assert "Ja" in parked["1"] and "Oui" not in parked["1"]
    assert "{{ scenario.word }}" not in html


def test_scenarios_that_render_alike_share_one_parked_set():
    """Panels are grouped on what they draw, and the parked rows follow that
    grouping -- otherwise a survey whose carousel does not vary would carry a
    copy of every row per scenario."""
    question, schema = _carousel_survey()
    question = {**question, "question_options": ["Yes", "No"]}
    variants = [scenarios.pipe([question], one) for one in ({"a": 1}, {"a": 2})]
    html = render_bundle(
        [question],
        schema,
        variants=variants,
        scenarios=[{"index": 0, "label": "0"}, {"index": 1, "label": "1"}],
        title="t",
    )
    assert sorted(_parked(html)) == ["0 1"]


def test_an_unbound_carousel_parks_its_rows_exactly_as_it_always_did():
    """No scenarios, no key: the markup an ordinary bundle carries is the markup
    it carried before any of this existed."""
    question, schema = _carousel_survey()
    question = {**question, "question_options": ["Yes", "No"]}
    html = render_bundle([question], schema, title="t")
    tag = re.search(
        r'<template class="preview-matrix-carousel-options"[^>]*>', html
    ).group(0)
    assert "data-scenario-indices" not in tag
    assert 'data-question-name="m"' in tag
