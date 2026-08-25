"""The ``runway`` command line.

    runway examples/mixed_survey.json
    runway examples/mixed_survey.json --split
    runway examples/*.json -o build/previews

Kept to argparse and relative imports so the same function serves both
``python -m runway`` and the ``runway`` console script.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .survey import load, render_survey

DEFAULT_OUT = Path("outputs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runway",
        description=(
            "Render static HTML previews of EDSL human-survey questions. "
            "Question types with no renderer yet are drawn as a full page "
            "carrying a note in place of the control."
        ),
    )
    parser.add_argument(
        "survey",
        type=Path,
        nargs="+",
        help="Survey JSON: a list of question dicts, or an object with "
        "'questions' and an optional 'humanize_schema'. Several may be given; "
        "each is written under its own file name, so they can share one "
        "output directory.",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory (default: ./outputs, created if absent).",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Write one file per question instead of a single bundle. "
        "Each file re-inlines the stylesheet, so this is much larger for "
        "anything but a short survey.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Document title for the bundled page (default: the survey file's "
        "name, which is what distinguishes several rendered together).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Every survey is read before any is written, so a bad path among several
    # leaves the output directory as it was rather than half rewritten.
    surveys: list[tuple[Path, list[dict], dict]] = []
    for survey_path in args.survey:
        if not survey_path.exists():
            print(f"error: no such survey file: {survey_path}", file=sys.stderr)
            return 1
        questions, humanize_schema = load(survey_path)
        if not questions:
            print(f"error: no questions found in {survey_path}", file=sys.stderr)
            return 1
        surveys.append((survey_path, questions, humanize_schema))

    written: list[Path] = []
    for survey_path, questions, humanize_schema in surveys:
        written.extend(
            render_survey(
                questions,
                humanize_schema,
                args.out,
                split=args.split,
                title=args.title or survey_path.stem,
                name=survey_path.stem,
            )
        )
    for path in written:
        print(path)
    print(f"\n{len(written)} file(s) written to {args.out}", file=sys.stderr)
    return 0
