"""Question groups: a page that holds more than one question.

A survey defines the groups and its humanize schema asks to be presented by
them; neither half does anything alone. What follows from that is in three
parts, and the tests below are in the same order.

**The arithmetic**, which is `pages.resolve`: group ranges index the survey's
*questions* while its item list also holds instructions, so the two numberings
have to be kept apart -- and an instruction belongs to the page of the question
after it, which is where EDSL puts it when it serves one.

**The page**, which is a panel holding several questions rather than one. The
sharpest test here is `test_a_checkbox_sharing_a_page_carries_its_own_positions`:
exclusive options are a rule rather than markup, and the panel that used to
speak for one question cannot speak for four.

**What is unchanged**, which is most of it. A survey with no groups, or with
groups its schema does not ask for, renders exactly the bytes it did before any
of this existed -- `test_groups_alone_change_nothing` is that promise.

Uses examples/group_survey.json, whose four pages are two groups of three, a
question in no group at all, and a group of one.

Runs under pytest, or directly: python tests/test_groups.py
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

import examples
import goldens
from runway import pages
from runway.renderer import render_body, render_bundle, render_page_of
from runway.survey import item_names, previewable, render_survey

EXAMPLE = examples.EXAMPLES / "group_survey.json"

GROUPED = {"survey": {"presentation": "group"}}


def _example() -> tuple[list[dict], dict, dict]:
    return examples.load_grouped_example(EXAMPLE)


def _question(name: str) -> dict:
    return {
        "question_name": name,
        "question_type": "free_text",
        "question_text": f"{name}?",
    }


def _instruction(name: str) -> dict:
    return {"edsl_class_name": "Instruction", "name": name, "text": "Read this."}


def _bundle() -> str:
    questions, humanize_schema, groups = _example()
    return render_bundle(
        previewable(questions),
        humanize_schema,
        item_names=item_names(questions),
        pages=pages.resolve(questions, groups, humanize_schema),
    )


# --------------------------------------------------------------------------
# The arithmetic
# --------------------------------------------------------------------------


def test_without_groups_a_page_is_one_question():
    items = [_question("a"), _instruction("i"), _question("b")]
    resolved = pages.resolve(items)
    assert [page.positions for page in resolved] == [(0,), (1,)]
    # Positions count questions; the index counts items, which is what a
    # progress reading is measured against.
    assert [page.index for page in resolved] == [0, 2]
    assert [page.name for page in resolved] == ["a", "b"]


def test_groups_alone_change_nothing():
    """Both halves or neither: this is the pair EDSL rejects as a mistake."""
    items = [_question("a"), _question("b")]
    groups = {"both": (0, 1)}
    assert pages.resolve(items, groups) == pages.resolve(items)
    assert pages.resolve(items, None, GROUPED) == pages.resolve(items)


def test_a_group_is_a_page():
    items = [_question("a"), _question("b"), _question("c")]
    resolved = pages.resolve(items, {"first": (0, 1), "second": (2, 2)}, GROUPED)
    assert [page.positions for page in resolved] == [(0, 1), (2,)]
    assert [page.name for page in resolved] == ["first", "second"]
    assert [page.group for page in resolved] == ["first", "second"]


def test_a_group_range_counts_questions_not_items():
    """The trap: an instruction between two questions must not shift a range."""
    items = [_question("a"), _instruction("i"), _question("b"), _question("c")]
    resolved = pages.resolve(items, {"pair": (0, 1), "last": (2, 2)}, GROUPED)
    assert [page.positions for page in resolved] == [(0, 1), (2,)]


def test_an_instruction_belongs_to_the_page_after_it():
    """Where EDSL puts it when it serves the page, so where the page starts."""
    items = [_question("a"), _instruction("i"), _question("b")]
    resolved = pages.resolve(items, {"one": (0, 0), "two": (1, 1)}, GROUPED)
    assert [page.index for page in resolved] == [0, 1]
    # The second page begins at the instruction, not at its first question.
    assert items[resolved[1].index] == _instruction("i")


def test_a_run_of_instructions_all_join_the_following_page():
    items = [_question("a"), _instruction("i"), _instruction("j"), _question("b")]
    resolved = pages.resolve(items, {"one": (0, 0), "two": (1, 1)}, GROUPED)
    assert [page.index for page in resolved] == [0, 1]


def test_a_trailing_instruction_joins_the_last_page():
    items = [_question("a"), _question("b"), _instruction("outro")]
    resolved = pages.resolve(items, {"one": (0, 0), "two": (1, 1)}, GROUPED)
    # Two pages, not three: an instruction alone is not a page anyone is served,
    # and it has no preview here in any case.
    assert [page.positions for page in resolved] == [(0,), (1,)]


def test_a_question_in_no_group_gets_a_page_of_its_own():
    """Never served live, and all the more reason to draw it here."""
    items = [_question("a"), _question("loose"), _question("b")]
    resolved = pages.resolve(items, {"one": (0, 0), "two": (2, 2)}, GROUPED)
    assert [page.name for page in resolved] == ["one", "loose", "two"]
    assert resolved[1].group is None


def test_group_ranges_survive_a_json_round_trip():
    """edsl writes tuples; JSON gives back lists. Both have to page the same."""
    items = [_question("a"), _question("b")]
    assert pages.resolve(items, {"both": [0, 1]}, GROUPED) == pages.resolve(
        items, {"both": (0, 1)}, GROUPED
    )


def test_a_malformed_range_is_dropped_rather_than_raised_on():
    assert pages.normalize({"ok": (0, 1), "bad": "0-1", "short": [2]}) == {
        "ok": (0, 1)
    }


def test_the_example_pages_as_its_source_says():
    questions, humanize_schema, groups = _example()
    resolved = pages.resolve(questions, groups, humanize_schema)
    assert [page.name for page in resolved] == [
        "background",
        "about_choices",
        "commute_days",
        "wrap_up",
    ]
    assert [page.positions for page in resolved] == [
        (0, 1, 2),
        (3, 4, 5),
        (6,),
        (7,),
    ]
    assert [page.index for page in resolved] == [0, 3, 6, 7]
    # The one page the live survey would never serve.
    assert [page.unserved for page in resolved] == [False, False, True, False]


# --------------------------------------------------------------------------
# The page
# --------------------------------------------------------------------------


def test_a_bundle_has_a_panel_per_page():
    html = _bundle()
    assert html.count('class="preview-panel') == 4
    assert html.count('class="preview-panel is-active"') == 1
    assert 'data-question-name="background"' in html


def test_every_question_of_a_group_is_on_its_page():
    html = _bundle()
    first = html.split('<div class="preview-panel')[1]
    for text in ("Where do you usually work?", "What is your role?", "How many years"):
        assert text in first


def test_an_item_block_matches_react():
    """The wrapper the page puts round every item, byte for byte.

    Recorded rather than transcribed, like everything else the page is built
    from: `survey_item_with_comment` and `survey_item_without_comment` are the
    cases, and `test_every_recorded_question_case_matches` sweeps them along
    with the rest. This says what they are for.
    """
    for name in ("survey_item_without_comment", "survey_item_with_comment"):
        case = goldens.load_cases()[name]
        assert goldens.render_case(case) == goldens.load_goldens()[name]


def test_every_item_is_wrapped_in_the_reference_block():
    """The live page wraps each item, one question or several -- `custom_css`
    hangs the separation between them off exactly this class."""
    assert _bundle().count('class="edsl-survey-item"') == 8
    assert render_body(_question("a")).count('class="edsl-survey-item"') == 1


def test_the_toolbar_names_pages_rather_than_questions():
    html = _bundle()
    assert '<option value="0">1. background — 3 questions</option>' in html
    assert '<option value="1">2. about_choices — 3 questions</option>' in html
    # A group of one is still a group, and is named after it -- but it is one
    # question, so its type is the more useful thing to say.
    assert '<option value="3">4. wrap_up — Free Text</option>' in html
    # ...and the page nobody is served says so before it is even opened.
    assert (
        '<option value="2">3. commute_days — Multiple Choice (no group)</option>'
        in html
    )


def test_a_checkbox_sharing_a_page_carries_its_own_positions():
    """The rule the panel cannot hold for a page of several questions."""
    html = _bundle()
    page = html.split('<div class="preview-panel')[2]
    assert 'class="preview-item" style="display:contents" data-exclusive="4"' in page
    # ...and the panel itself claims nothing, since it would be claiming it for
    # the likert question above as well.
    assert page[: page.index("preview-item")].count("data-exclusive") == 0


def test_a_page_of_one_question_keeps_the_markup_it_had():
    html = _bundle()
    page = html.split('<div class="preview-panel')[-1]
    assert 'data-question-name="wrap_up"' in page
    assert "preview-item" not in page


def test_progress_is_read_from_where_the_page_begins():
    questions, humanize_schema, groups = _example()
    resolved = pages.resolve(questions, groups, humanize_schema)
    html = _bundle()
    panels = html.split('<div class="preview-panel')[1:]
    # Three steps, and each page is on its own: the schema's boundaries name the
    # last question of each group, so a marker fills as a page is submitted.
    assert len(resolved) == 4
    # Three steps over four pages: the schema's boundaries name the last question
    # of a group, so the marker moves as a group is submitted and holds across
    # the pages inside the last step.
    complete = [panel.count("edsl-progress-step-complete") for panel in panels]
    assert complete == [0, 1, 2, 2]
    for panel in panels:
        assert panel.count("edsl-progress-step-current") == 1


def test_a_page_is_deduplicated_across_scenarios_as_a_whole():
    """A page is the unit a binding is compared on, not a question.

    Two scenarios, two pages. The first holds a question that pipes, so it
    renders differently under each and is repeated; the second pipes nothing
    and is drawn once, marked as serving both.
    """
    items = [_question("piped"), _question("fixed"), _question("last")]
    resolved = pages.resolve(items, {"one": (0, 1), "two": (2, 2)}, GROUPED)
    variants = [
        [dict(items[0], question_text="In Boston?"), items[1], items[2]],
        [dict(items[0], question_text="In Lisbon?"), items[1], items[2]],
    ]
    html = render_bundle(
        items,
        GROUPED,
        variants=variants,
        scenarios=[{"index": 0, "label": "Boston"}, {"index": 1, "label": "Lisbon"}],
        pages=resolved,
    )
    panels = html.split('<div class="preview-panel')[1:]
    assert len(panels) == 3
    assert 'data-question-index="0" data-scenario-indices="0"' in panels[0]
    assert 'data-question-index="0" data-scenario-indices="1"' in panels[1]
    # The page that does not vary is one panel serving both scenarios.
    assert 'data-question-index="1" data-scenario-indices="0 1"' in panels[2]


# --------------------------------------------------------------------------
# Writing the files
# --------------------------------------------------------------------------


def _write(**kwargs) -> list[tuple[Path, str]]:
    questions, humanize_schema, groups = _example()
    with tempfile.TemporaryDirectory() as tmp:
        written = render_survey(
            questions, humanize_schema, out_dir=Path(tmp), groups=groups, **kwargs
        )
        return [(path, path.read_text(encoding="utf-8")) for path in written]


def test_split_writes_a_file_per_page_named_after_its_group():
    written = _write(split=True, name="group_survey")
    assert [path.name for path, _ in written] == [
        "group_survey-01-background.html",
        "group_survey-04-about_choices.html",
        "group_survey-07-commute_days.html",
        "group_survey-08-wrap_up.html",
    ]


def test_a_split_page_holds_the_whole_group():
    written = dict((path.name, html) for path, html in _write(split=True))
    first = written["01-background.html"]
    assert first.count('class="edsl-survey-item"') == 3
    # One document, one stylesheet, one Next button -- it is a page, not three.
    assert first.count('type="submit"') == 1


def test_a_split_group_page_puts_its_positions_on_the_items():
    written = dict((path.name, html) for path, html in _write(split=True))
    page = written["04-about_choices.html"]
    assert 'data-exclusive="4"' in page
    assert 'id="root" class="h-full">' in page


def test_render_page_of_one_item_is_render_page():
    from runway.renderer import render_page

    question = _question("a")
    assert render_page_of([(question, None)]) == render_page(question)


# --------------------------------------------------------------------------
# What check says
# --------------------------------------------------------------------------


def _check(*argv: str, code: int = 0) -> str:
    """Run `check` and give back what it printed.

    Captured here rather than through pytest's `capsys`, so this file still runs
    on its own. ``code`` is the exit status expected -- 1 where the survey has a
    problem of its own, which a question in no group is.
    """
    from runway.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        assert main(["check", *argv]) == code
    return buffer.getvalue()


def test_check_names_the_group_each_question_is_served_on():
    # Exits 1 for the question this example deliberately leaves out of every
    # group; the column is what this is about.
    out = _check(
        str(EXAMPLE), "--schema", str(examples.schema_path(EXAMPLE)), code=1
    )
    assert "8 items, 4 pages" in out
    assert "background     work_location" in out
    assert "wrap_up        anything_else" in out


def test_check_says_nothing_about_pages_for_an_ungrouped_survey():
    """The column and the count would be the questions, said twice."""
    out = _check(str(examples.EXAMPLES / "checkbox_survey.json"))
    assert "pages" not in out


def test_check_reports_a_schema_asking_for_groups_a_survey_does_not_have():
    """An authoring mistake that leaves no mark on any page: the preview and the
    live survey both fall back to a question at a time, silently."""
    with tempfile.TemporaryDirectory() as tmp:
        survey = Path(tmp) / "ungrouped.json"
        document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        document["question_groups"] = {}
        survey.write_text(json.dumps(document), encoding="utf-8")
        schema = Path(tmp) / "schema.json"
        schema.write_text(json.dumps(GROUPED), encoding="utf-8")
        out = _check(str(survey), "--schema", str(schema))
    assert "note: the schema asks for grouped pages" in out
    # Every question is its own page now, so none of them is in the wrong one.
    assert "warning" not in out


def test_check_warns_about_a_question_no_group_holds():
    """A survey problem, so it fails the check -- the same as a question no
    human survey could put to anybody, which is what this one amounts to."""
    out = _check(
        str(EXAMPLE), "--schema", str(examples.schema_path(EXAMPLE)), code=1
    )
    # Said against the question, where an author can act on it, rather than in a
    # footnote about the survey.
    warning_line = next(line for line in out.splitlines() if "warning" in line)
    assert "commute_days" in warning_line
    assert "in no question group" in warning_line


def test_a_question_no_group_holds_draws_a_warning_instead_of_its_control():
    html = _bundle()
    page = html.split('<div class="preview-panel')[3]
    # Its text is drawn -- an author has to recognise which question this is --
    # and its options are not.
    assert "How many days a week do you travel to an office?" in page
    assert "edsl-preview-ungrouped" in page
    assert "Never served" in page
    assert 'type="radio"' not in page


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
