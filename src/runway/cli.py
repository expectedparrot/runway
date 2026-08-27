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

from . import __version__, inspection
from .question_types import RENDERERS, background, unsupported
from .survey import SurveyLoadError, iter_questions, load, load_schema, name_for

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
otherwise: one file holding every question, with a toolbar to move between them.
`--split` writes one file per question instead, which is much larger -- the
stylesheet is most of a page's weight and a bundle inlines it once.

What a preview cannot show: piped values (`{{ agent.x }}` and `{{ scenario.x }}`
render as written), option randomization, media resolved server-side from a file
(an option referencing one previews as its reference text), a matrix configured
as a carousel (it previews as a note naming the reason), and position under skip
logic, which is inferred from authored order. Controls tick but mostly do not
behave: checkbox Select all and exclusive options work; validation, selection
limits and the Next button do not.

Add `--json` to `check`, `types` and `version` for machine-readable output.\
"""


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def cmd_render(args: argparse.Namespace) -> int:
    surveys = _load_all(args.survey, args.schema)
    if surveys is None:
        return 1

    written: list[Path] = []
    for path, questions, humanize_schema in surveys:
        name = name_for(path)
        written.extend(
            _render_survey(
                questions,
                humanize_schema,
                args.out,
                split=args.split,
                title=args.title or name,
                name=name,
            )
        )
    for path in written:
        print(path)
    print(f"\n{len(written)} file(s) written to {args.out}", file=sys.stderr)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Report what each question will render as. Writes nothing."""
    surveys = _load_all(args.survey, args.schema)
    if surveys is None:
        return 1

    reports = []
    for path, questions, humanize_schema in surveys:
        # The schema is read here rather than ignored because it can change the
        # answer: a layout this package has not transcribed leaves a question
        # undrawn however ordinary its type is.
        per_question = humanize_schema.get("questions") or {}
        entries = [
            inspection.describe(
                question,
                position,
                per_question.get(question.get("question_name") or ""),
            )
            for position, question in iter_questions(questions)
        ]
        reports.append(
            {
                "survey": str(path),
                "items": len(questions),
                "questions": entries,
                "summary": inspection.summarize(entries),
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
    paths: list[Path], schema_path: Path | None = None
) -> list[tuple[Path, list[dict], dict]] | None:
    """Read every survey before any is acted on, or report and return None.

    Reading first means a bad path among several leaves the output directory as
    it was, rather than half rewritten.

    ``schema_path`` is a humanize schema saved on its own, which is the only way
    one reaches a preview: it is not part of an EDSL survey, so no survey file
    of any format has one to give. It applies to every survey given -- rendering
    a set of surveys against one schema is the reason to pass several at once.
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

    surveys: list[tuple[Path, list[dict], dict]] = []
    for path in paths:
        if not path.exists():
            print(f"error: no such survey file: {path}", file=sys.stderr)
            return None
        try:
            questions = load(path)
        except SurveyLoadError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return None
        if not questions:
            print(f"error: no questions found in {path}", file=sys.stderr)
            return None
        surveys.append((path, questions, schema))
    return surveys


def _render_survey(*args, **kwargs) -> list[Path]:
    # Imported at call time: `check`, `types`, `guide` and `version` have no
    # reason to build a Jinja environment or read the stylesheet off disk.
    from .survey import render_survey

    return render_survey(*args, **kwargs)


def _print_check(report: dict) -> None:
    entries = report["questions"]
    name = Path(report["survey"]).name
    print(f"\n{name}  -  {report['items']} items")
    if not entries:
        print("  (no previewable questions)")
        return

    print()
    name_width = max(len(entry["name"]) for entry in entries)
    type_width = max(len(entry["type"]) for entry in entries)
    for entry in entries:
        detail = ""
        if entry.get("reason"):
            detail = f"  ({entry['reason']})"
        elif entry["status"] == "note":
            detail = "  (no preview built for this type yet)"
        elif entry["status"] == "warning":
            detail = "  (never shown to a respondent)"
        elif entry["status"] == "automatic":
            detail = f"  ({entry['kind']})"
        print(
            f"  {entry['status']:<{_STATUS_WIDTH}}  "
            f"{entry['name']:<{name_width}}  "
            f"{entry['type']:<{type_width}}{detail}"
        )

    counts = report["summary"]
    parts = [
        f"{counts[status]} {status}" for status in inspection.STATUSES if counts[status]
    ]
    print(f"\n{', '.join(parts)}")


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


def _add_survey_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "survey",
        type=Path,
        nargs="+",
        help="Survey file: a .ep package, or a .json.gz or .json dump. All "
        "three are opened by Survey.load(). Several may be given.",
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
