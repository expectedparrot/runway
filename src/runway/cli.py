"""The ``runway`` command line.

    runway render examples/mixed_survey.json
    runway render survey.ep
    runway check  examples/mixed_survey.json
    runway types
    runway guide
    runway version

A verb is always required. ``runway survey.json`` is not a shortcut for
``runway render survey.json`` -- there is no bare form, deliberately, so that
what a command does is never a function of what its argument happens to be
named.

Kept to argparse and relative imports: no CLI dependency of its own, and the
same ``main`` serves both ``python -m runway`` and the console script.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, inspection, pages, scenarios
from .question_types import RENDERERS, background, unsupported
from .survey import (
    SurveyLoadError,
    iter_questions,
    load,
    load_schema,
    name_for,
    output_paths,
)

DEFAULT_OUT = Path("previews")

# Aligns the status column in `check` output without a formatting library.
_STATUS_WIDTH = max(len(status) for status in inspection.STATUSES)

GUIDE = """\
runway renders EDSL human-survey questions as static HTML that looks like the
page a respondent is served. It is one-shot: a survey file in, HTML out. There
is no project, no state and no session to resume.

  runway check  survey.ep       what each question will render as
  runway render survey.ep       write the HTML
  runway types                  which question types have a control
  runway guide                  this text
  runway version                the version, and the types it draws

A survey file is anything edsl saves a survey as: a `.ep` package -- what
`Survey.save()` writes by default -- or a `.json.gz` or `.json` dump. All three
are opened by `Survey.load()`, so all three describe the same survey the same
way. Its keys about survey flow are ignored; a preview only needs the questions.

A bare list of question dicts is not a survey and is not accepted -- wrap it in
{"questions": [...]}, or save the survey with Survey.save().

A humanize schema is not part of an EDSL survey -- edsl neither writes one nor
reads one -- so it travels in a file of its own, whatever format the survey is
in. Both commands take it, since it can change what a question renders as:

  runway check  survey.ep --schema schema.json
  runway render survey.ep --schema schema.json

Start with `check`. It writes nothing and tells you which questions preview
with their real control, which fall back to a note because no control is
transcribed for the type yet, which are answered on the server without a
respondent, and which cannot be shown to a person at all. Only the last is a
problem with the survey; the rest are a problem with this tool, or with
nothing.

Then `render`. It writes ./previews/<survey>.html unless `-o DIR` says
otherwise: one file holding every page, with a toolbar to move between them.
`--split` writes one file per page instead, which is much larger -- the
stylesheet is most of a page's weight and a bundle inlines it once.

A page is one question unless the survey groups them. A survey that names
question groups, and whose schema asks for them with
{"survey": {"presentation": "group"}}, is served a whole group per page and is
previewed that way: one panel, or one split file, per group. Both halves are
needed -- groups without the schema, and the schema without groups, are served a
question at a time -- and `check` says which of the two is missing.

A survey may also be bound to a scenario list. A respondent is assigned one
scenario for their whole response, so each scenario is a different rendering of
the survey, and a preview of one is a page nobody is served:

  runway render survey.ep --scenarios scenarios.json
  runway render survey.ep --scenarios scenarios.json --scenario-index 0,17,204

The bundle then carries a second dropdown. A question that pipes nothing renders
once and is shown for every scenario, so the file grows only where the survey
really differs. A list longer than 25 is refused rather than truncated; pick
from it with `--scenario-index`.

What a preview cannot show: agent traits and prior answers (`{{ agent.x }}` and
`{{ q.answer }}` render as written, and a question applying a *filter* to one of
those does not pipe at all), option randomization, media resolved server-side
from a file (an option referencing one previews as its reference text), a matrix
configured as a carousel (it previews as a note naming the reason), and position
under skip logic, which is inferred from authored order. Controls tick but
mostly do not behave: checkbox Select all and exclusive options work; validation,
selection limits and the Next button do not.

Add `--json` to `check`, `types` and `version` for machine-readable output.\
"""


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def cmd_render(args: argparse.Namespace) -> int:
    loaded = _load_all(args.survey, args.schema, args.scenarios, args.scenario_index)
    if loaded is None:
        return 1
    surveys, scenarios = loaded
    surveys = _without_repeats(surveys)
    if _colliding(surveys, args.out, args.split, scenarios):
        return 1

    written: list[Path] = []
    for path, questions, humanize_schema, groups in surveys:
        name = name_for(path)
        written.extend(
            _render_survey(
                questions,
                humanize_schema,
                args.out,
                split=args.split,
                title=args.title or name,
                name=name,
                scenarios=scenarios,
                groups=groups,
            )
        )
    for path in written:
        print(path)
    print(f"\n{len(written)} file(s) written to {args.out}", file=sys.stderr)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Report what each question will render as. Writes nothing."""
    loaded = _load_all(args.survey, args.schema, args.scenarios, args.scenario_index)
    if loaded is None:
        return 1
    surveys, scenarios = loaded

    reports = []
    for path, questions, humanize_schema, groups in surveys:
        # The schema is read here rather than ignored because it can change the
        # answer: a layout this package has not transcribed leaves a question
        # undrawn however ordinary its type is.
        per_question = humanize_schema.get("questions") or {}
        # Resolved before the questions are described, because one thing about a
        # question is not in the question: whether any page of this survey
        # carries it. See `pages` and `question_types.ungrouped`.
        survey_pages = pages.resolve(questions, groups, humanize_schema)
        unserved = {
            position for page in survey_pages if page.unserved for position in page.positions
        }
        entries = [
            inspection.describe(
                question,
                position,
                per_question.get(question.get("question_name") or ""),
                unserved=index in unserved,
            )
            for index, (position, question) in enumerate(iter_questions(questions))
        ]
        if scenarios:
            _add_piping(entries, questions, scenarios)
        _add_pages(entries, survey_pages)
        reports.append(
            {
                "survey": str(path),
                "items": len(questions),
                "pages": len(survey_pages),
                "questions": entries,
                "summary": inspection.summarize(entries),
                "notes": _group_notes(humanize_schema, groups),
            }
        )

    if args.json:
        print(json.dumps({"surveys": reports}, indent=2))
    else:
        for report in reports:
            _print_check(report)

    # A type nobody can be shown is the survey's problem, and the only outcome
    # here worth failing on -- a missing control is this package being behind.
    return 1 if any(r["summary"]["warning"] for r in reports) else 0


def _type_status(question_type: str) -> str:
    """How a question of this type previews, judged on the type alone.

    Only ever ``drawn``, ``automatic`` or ``note``: a type in the humanized set
    can never be the ``warning`` case, and the thinking wrapper is a property
    of a question rather than of a type, so it cannot be seen from here.
    """
    if question_type in background.BACKGROUND_TYPES:
        return "automatic"
    return "drawn" if question_type in RENDERERS else "note"


def cmd_types(args: argparse.Namespace) -> int:
    """Which question types have a control here, and which could."""
    rows = [
        {"type": question_type, "status": _type_status(question_type)}
        for question_type in sorted(unsupported.HUMANIZED_TYPES)
    ]
    if args.json:
        print(json.dumps({"types": rows}, indent=2))
        return 0

    width = max(len(row["type"]) for row in rows)
    print("Question types a human survey can be configured for:\n")
    for row in rows:
        print(f"  {row['type']:<{width}}  {'-' if row['status'] == 'note' else row['status']}")

    drawn = sum(row["status"] == "drawn" for row in rows)
    automatic = sum(row["status"] == "automatic" for row in rows)
    print(f"\n{drawn} of {len(rows)} have a control here.")
    print(
        f"{automatic} are answered on the server, so they are complete without one "
        "-- no\nrespondent is ever shown them."
    )
    print(
        "A type absent from this list has no human-survey rendering at all, so "
        "no preview\ncould exist for it -- see `runway guide`."
    )
    return 0


def cmd_guide(args: argparse.Namespace) -> int:
    print(GUIDE)
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    if args.json:
        print(
            json.dumps(
                {
                    "version": __version__,
                    "drawn_types": sorted(RENDERERS),
                    "humanized_types": sorted(unsupported.HUMANIZED_TYPES),
                },
                indent=2,
            )
        )
        return 0
    print(f"runway {__version__}")
    print(f"draws {len(RENDERERS)} question types: {', '.join(sorted(RENDERERS))}")
    return 0


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _load_all(
    paths: list[Path],
    schema_path: Path | None = None,
    scenarios_path: Path | None = None,
    index_spec: str | None = None,
) -> tuple[list[tuple[Path, list[dict], dict, dict]], list[tuple[int, dict]]] | None:
    """Read every input before any is acted on, or report and return None.

    Reading first means a bad path among several leaves the output directory as
    it was, rather than half rewritten.

    ``schema_path`` is a humanize schema saved on its own, which is the only way
    one reaches a preview: it is not part of an EDSL survey, so no survey file
    of any format has one to give. It applies to every survey given -- rendering
    a set of surveys against one schema is the reason to pass several at once.

    ``scenarios_path`` is a scenario list, and applies to every survey for the
    same reason. It comes back as ``(index, scenario)`` pairs carrying the
    list's own numbering, which is what a selection has to preserve.
    """
    schema: dict = {}
    if schema_path is not None:
        if not schema_path.exists():
            print(f"error: no such schema file: {schema_path}", file=sys.stderr)
            return None
        try:
            schema = load_schema(schema_path)
        except SurveyLoadError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return None

    chosen: list[tuple[int, dict]] = []
    if scenarios_path is not None:
        if not scenarios_path.exists():
            print(f"error: no such scenario list: {scenarios_path}", file=sys.stderr)
            return None
        # Imported here rather than at module scope: it reaches edsl, and
        # `types`, `guide` and `version` have no reason to pay for that.
        from .scenarios import load_selection

        try:
            chosen = load_selection(scenarios_path, index_spec)
        except SurveyLoadError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return None
    elif index_spec is not None:
        print(
            "error: --scenario-index selects from a scenario list, and none was "
            "given. Add --scenarios PATH.",
            file=sys.stderr,
        )
        return None

    surveys: list[tuple[Path, list[dict], dict, dict]] = []
    for path in paths:
        if not path.exists():
            print(f"error: no such survey file: {path}", file=sys.stderr)
            return None
        try:
            document = load(path)
        except SurveyLoadError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return None
        questions = document.get("questions") or []
        if not questions:
            print(f"error: no questions found in {path}", file=sys.stderr)
            return None
        # The groups travel alongside: a survey's own, which page the preview
        # where the schema asks for that presentation and are ignored otherwise.
        surveys.append((path, questions, schema, document.get("question_groups")))
    return surveys, chosen


def _add_pages(entries: list[dict], survey_pages: list[pages.Page]) -> None:
    """Record which group each question is served on, in place.

    Recorded only for a survey that pages by group. Telling every question of an
    ordinary survey that it is alone on a page of its own would be a column
    saying nothing, for every survey ever written.

    Entries are in the order ``iter_questions`` yields them, which is the order
    a page's ``positions`` index into, so the two line up by position rather
    than by name -- a name is not something a question dict is guaranteed to
    carry.
    """
    for page in survey_pages:
        if page.group is None:
            continue
        for position in page.positions:
            if position < len(entries):
                entries[position]["group"] = page.group


def _group_notes(humanize_schema: dict, groups: dict) -> list[str]:
    """What is worth saying about how this survey pages, if anything.

    One case, and it is here rather than against a question because it is not
    about any one of them: a schema asking for grouped pages from a survey that
    defines no groups. Nothing on any page can show it -- every page is what it
    would have been -- and the live survey does the same thing quietly, so the
    report is the only place it can be said.

    The other grouping mistake, a question no group holds, is a warning against
    that question instead: it has a page of its own to be said on.
    """
    notes = []
    if pages.presentation(humanize_schema) == pages.PER_GROUP and not groups:
        notes.append(
            "the schema asks for grouped pages, but the survey defines no "
            "question groups -- it will be served a question at a time"
        )
    return notes


def _add_piping(
    entries: list[dict], questions: list[dict], scenarios: list[tuple[int, dict]]
) -> None:
    """Record on each entry what a scenario does to it, in place.

    Two different pieces of news, and the second is the one worth reporting
    loudly. ``pipes`` is what a scenario resolves, which is the question working
    as intended. ``unresolved`` is a name that is neither a scenario key nor a
    deferred one, and those fail silently in one of two ways -- the text renders
    as nothing, or the whole question stops piping. Neither leaves a mark on the
    page, which is why this is the place to say it.

    Reported against the first scenario. A key missing from one scenario but not
    another is a ragged list rather than a survey problem, and naming every
    scenario it is missing from would bury the case that matters.
    """
    from .scenarios import references, root_of, unresolved

    _, first = scenarios[0]
    names = [
        question["question_name"]
        for question in questions
        if question.get("question_name")
    ]
    by_name = {question.get("question_name"): question for question in questions}
    for entry in entries:
        question = by_name.get(entry["name"])
        if question is None:
            continue
        missing = unresolved(question, first, names)
        resolved = [
            reference
            for reference in references(question)
            if root_of(reference) in first or root_of(reference) == "scenario"
        ]
        # A deferred root -- `agent`, or another question's answer -- is
        # neither. It renders back as written, which is what this package
        # promises for it, so it is not news in either column.
        if resolved:
            entry["pipes"] = resolved
        if missing:
            entry["unresolved"] = missing


def _without_repeats(surveys: list[tuple[Path, list[dict], dict, dict]]):
    """Drop repeats of the same file, keeping the first.

    Naming one survey twice is not a collision -- it is a list with something
    said twice, and rendering it once is what was meant. Compared on the
    resolved path so that `survey.ep` and `./survey.ep` count as one.
    """
    seen: set[Path] = set()
    unique = []
    for entry in surveys:
        try:
            resolved = entry[0].resolve()
        except OSError:  # pragma: no cover - a path the OS will not resolve
            resolved = entry[0]
        if resolved not in seen:
            seen.add(resolved)
            unique.append(entry)
    return unique


def _colliding(
    surveys: list[tuple[Path, list[dict], dict, dict]],
    out_dir: Path,
    split: bool,
    scenarios: list[tuple[int, dict]] | None = None,
) -> bool:
    """Report and return True if two surveys would write the same file.

    Compared on the paths a render would actually produce, which is not the
    survey's name alone: bundled, each survey writes one `<name>.html`, so two
    surveys sharing a name collide; `--split` names pages after the questions,
    so the same two may not overlap at all. Asking :func:`output_paths` is what
    keeps this answer and the writer's the same.

    Refused rather than renamed: a made-up name would no longer match the
    survey it came from, and working out which was which is worse than being
    told to render them apart.

    *Every* clash is reported, in the order the surveys were given, so that a
    caller fixing them -- an agent especially -- can fix the lot in one pass
    rather than discovering the next on each re-run. Checked before anything is
    written, so a set that cannot all be rendered leaves the output directory
    as it was, the same way an unreadable one does.
    """
    indices = [index for index, _ in scenarios] if scenarios else None
    claimed: dict[Path, Path] = {}
    clashes: dict[Path, list[Path]] = {}
    for source, questions, humanize_schema, groups in surveys:
        for target in output_paths(
            questions,
            out_dir,
            split=split,
            name=name_for(source),
            scenario_indices=indices,
            # The same pages the render will write, since that is what a
            # collision is about: a survey paging by group writes a file per
            # group, and two surveys' groups may collide where their questions
            # would not.
            pages=pages.resolve(questions, groups, humanize_schema),
        ):
            first = claimed.setdefault(target, source)
            if first != source:
                clashes.setdefault(target, [first]).append(source)
    if not clashes:
        return False

    print("error: these surveys would be written to the same file:", file=sys.stderr)
    width = max(len(target.name) for target in clashes)
    for target, sources in clashes.items():
        listed = ", ".join(str(source) for source in sources)
        print(f"  {target.name:<{width}}  <- {listed}", file=sys.stderr)
    print(
        "Rename them, render them separately, or write into different "
        "directories with -o.",
        file=sys.stderr,
    )
    return True


def _render_survey(*args, **kwargs) -> list[Path]:
    # Imported at call time: `check`, `types`, `guide` and `version` have no
    # reason to build a Jinja environment or read the stylesheet off disk.
    from .survey import render_survey

    return render_survey(*args, **kwargs)


def _print_check(report: dict) -> None:
    entries = report["questions"]
    name = Path(report["survey"]).name
    grouped = any(entry.get("group") for entry in entries)
    # Pages are worth counting only where they are not the questions counted
    # again: a survey served a question at a time has as many pages as it has
    # questions, and saying so twice reads as though it meant something.
    paging = f", {report['pages']} pages" if grouped else ""
    print(f"\n{name}  -  {report['items']} items{paging}")
    if not entries:
        print("  (no previewable questions)")
        return

    print()
    name_width = max(len(entry["name"]) for entry in entries)
    type_width = max(len(entry["type"]) for entry in entries)
    # A column only where there is something to put in it -- see `_add_pages`.
    group_width = (
        max(len(entry.get("group") or "") for entry in entries) if grouped else 0
    )
    for entry in entries:
        page = f"{entry.get('group') or '':<{group_width}}  " if grouped else ""
        detail = ""
        if entry.get("reason"):
            detail = f"  ({entry['reason']})"
        elif entry["status"] == "note":
            detail = "  (no preview built for this type yet)"
        elif entry["status"] == "warning":
            detail = "  (never shown to a respondent)"
        elif entry["status"] == "automatic":
            detail = f"  ({entry['kind']})"
        piping = ""
        if entry.get("pipes"):
            piping = f"  pipes {', '.join(entry['pipes'])}"
        if entry.get("unresolved"):
            piping += f"  {', '.join(entry['unresolved'])} (unresolved)"
        print(
            f"  {entry['status']:<{_STATUS_WIDTH}}  "
            f"{page}"
            f"{entry['name']:<{name_width}}  "
            f"{entry['type']:<{type_width}}{detail}{piping}"
        )

    counts = report["summary"]
    parts = [
        f"{counts[status]} {status}" for status in inspection.STATUSES if counts[status]
    ]
    print(f"\n{', '.join(parts)}")

    # Said separately from the status counts, because it is a different kind of
    # news: a status is about whether a question can be drawn at all, where this
    # is about whether the scenario reached it.
    pipes = sum(1 for entry in entries if entry.get("pipes"))
    missing = sum(1 for entry in entries if entry.get("unresolved"))
    if pipes or missing:
        said = [f"{pipes} pipe"] if pipes else []
        if missing:
            said.append(
                f"{missing} name{'s' if missing > 1 else ''} nothing can resolve, "
                "so nothing in them pipes at all"
            )
        print(", ".join(said))

    # Last, and a third kind of news again: not about a question at all, but
    # about how the survey is paged -- which the page cannot show, because it
    # looks the same either way.
    for note in report.get("notes") or []:
        print(f"note: {note}")


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


def _add_survey_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "survey",
        type=Path,
        nargs="+",
        help="Survey file: a .ep package, or a .json.gz or .json dump. All "
        "three are opened by Survey.load(). Several may be given; for `render` "
        "their names must differ, since each is written to a file named after "
        "its survey.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        metavar="PATH",
        help="Humanize schema, which is configured and saved separately from "
        "the survey and is the only way one reaches a preview. Applies to "
        "every survey given.",
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=None,
        metavar="PATH",
        help="Scenario list -- a .ep package, or a .json.gz or .json dump, all "
        "opened by ScenarioList.load(). A respondent is assigned one scenario "
        "for their whole response, so each is a different rendering of the "
        "survey; the preview gets a dropdown to move between them. CSV is not "
        "a format edsl loads a scenario list from. Applies to every survey "
        "given.",
    )
    parser.add_argument(
        "--scenario-index",
        default=None,
        metavar="SPEC",
        help="Which scenarios to render: indices and ranges, comma-separated "
        "(0, 0-9, 0,17,204). Needed for a list of more than "
        f"{scenarios.MAX_SCENARIOS}, which is refused rather than truncated. "
        "The indices are the list's own and stay so in the dropdown.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runway",
        description="Static HTML previews of EDSL human-survey questions.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"runway {__version__}"
    )
    commands = parser.add_subparsers(dest="command", metavar="<command>")

    render = commands.add_parser(
        "render",
        help="Write HTML previews of a survey",
        description="Render a survey to static HTML.",
    )
    _add_survey_argument(render)
    render.add_argument(
        "-o",
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory (default: ./previews, created if absent).",
    )
    render.add_argument(
        "--split",
        action="store_true",
        help="One file per question instead of a single bundle. Each file "
        "re-inlines the stylesheet, so this is much larger for anything but a "
        "short survey.",
    )
    render.add_argument(
        "--title",
        default=None,
        help="Document title for the bundled page (default: the survey's own "
        "name -- its file name with the format suffix taken off).",
    )
    render.set_defaults(func=cmd_render)

    check = commands.add_parser(
        "check",
        help="Report what each question will render as",
        description="Report what each question will render as. Writes nothing. "
        "Exits non-zero if any question cannot be shown to a respondent at all.",
    )
    _add_survey_argument(check)
    check.add_argument("--json", action="store_true", help="Machine-readable output.")
    check.set_defaults(func=cmd_check)

    types = commands.add_parser(
        "types",
        help="List supported question types",
        description="The question types a human survey can be configured for, "
        "and which of them have a control here.",
    )
    types.add_argument("--json", action="store_true", help="Machine-readable output.")
    types.set_defaults(func=cmd_types)

    guide = commands.add_parser(
        "guide",
        help="How to use this tool",
        description="Describe what runway does, and what a preview cannot show.",
    )
    guide.set_defaults(func=cmd_guide)

    version = commands.add_parser(
        "version",
        help="Package version and supported types",
        description="Report the package version and which types it draws.",
    )
    version.add_argument("--json", action="store_true", help="Machine-readable output.")
    version.set_defaults(func=cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        # argparse's own message for a missing subcommand says only "invalid
        # choice"; the full help is what someone typing `runway` wants.
        parser.print_help()
        return 2
    return args.func(args)
