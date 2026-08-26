"""Survey-level input handling and output writing."""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import progress as progress_module
from .renderer import render_bundle, render_page

# Non-question items in an EDSL survey's item list. Skipped for now; they are
# not questions and have no preview yet.
NON_QUESTION_CLASSES = {"Instruction", "ChangeInstruction"}


def _slug(value: str) -> str:
    """Filesystem-safe stem for a question name."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return cleaned or "question"


def load(path: Path) -> tuple[list[dict], dict]:
    """Read a survey document.

    Accepts either a bare list of question dicts, or an object with
    ``questions`` and an optional ``humanize_schema``. Returns the questions
    and the humanize schema (``{}`` when absent).

    ``Survey.to_dict()`` is the second of those: it carries a top-level
    ``questions`` list of question dicts, alongside keys about flow that a
    preview has no use for. It has no ``humanize_schema`` -- that is configured
    separately and saved separately -- so a survey dumped that way loads with an
    empty one, and :func:`load_schema` is how the other file reaches it.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, {}
    return data.get("questions") or [], data.get("humanize_schema") or {}


def load_schema(path: Path) -> dict:
    """Read a humanize schema saved on its own.

    The schema is the object with ``survey`` and ``questions`` keys -- the shape
    ``Survey.humanize()`` takes. A file that wraps it under ``humanize_schema``
    is accepted too, since that is what a survey document calls it and so the
    natural thing to have saved.

    The two are told apart without ambiguity: a schema's ``questions`` is an
    object keyed by question name, where a survey document's is a list.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("a humanize schema is an object, not a list")
    wrapped = data.get("humanize_schema")
    if isinstance(wrapped, dict):
        return wrapped
    if isinstance(data.get("questions"), list):
        raise ValueError(
            "this looks like a survey document rather than a humanize schema: "
            "its 'questions' is a list of questions, not a table keyed by name"
        )
    return data


def iter_questions(questions: list[dict]):
    """Yield ``(page_num, question)`` for the previewable items in a survey.

    Page numbers count every item, so they line up with what a respondent sees
    even though non-question items are not yielded.
    """
    for index, item in enumerate(questions, start=1):
        if item.get("edsl_class_name") in NON_QUESTION_CLASSES:
            continue
        yield index, item


def previewable(questions: list[dict]) -> list[dict]:
    """The questions a preview can render, in survey order."""
    return [question for _, question in iter_questions(questions)]


def item_names(questions: list[dict]) -> list[str]:
    """The name of every survey item, in order -- instructions included.

    Progress is measured against all of them, not just the previewable ones: a
    respondent passes an instruction the same way they pass a question, and a
    stepped indicator's boundaries may name either.
    """
    return [
        item.get("question_name") or item.get("name") or f"item-{index}"
        for index, item in enumerate(questions, start=1)
    ]


def render_survey(
    questions: list[dict],
    humanize_schema: dict | None = None,
    out_dir: Path | None = None,
    split: bool = False,
    title: str = "Survey preview",
    name: str | None = None,
) -> list[Path]:
    """Write a survey preview into ``out_dir``. Returns the paths written.

    By default this is a single ``index.html`` holding every question, with a
    toolbar to jump between them. ``split=True`` writes one file per question
    instead -- useful for handing someone a single question, at the cost of
    re-inlining the stylesheet in each file.

    ``name`` is the stem the written files take, so several surveys can share
    an output directory without overwriting each other: the bundle becomes
    ``<name>.html`` and split pages ``<name>-01-<question>.html``. The CLI
    passes the survey file's own name. Omitted, the bundle is ``index.html``
    and split pages are numbered alone -- right for a directory holding the
    one survey.
    """
    humanize_schema = humanize_schema or {}
    out_dir = Path(out_dir or "previews")
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = _slug(name) if name else ""
    names = item_names(questions)
    items = previewable(questions)
    if not split:
        path = out_dir / f"{stem or 'index'}.html"
        path.write_text(
            render_bundle(items, humanize_schema, title=title, item_names=names),
            encoding="utf-8",
        )
        return [path]

    survey_schema = humanize_schema.get("survey") or {}
    per_question = humanize_schema.get("questions") or {}
    custom_css = survey_schema.get("custom_css")
    progress_config = survey_schema.get("progress")
    total = len(questions)

    prefix = f"{stem}-" if stem else ""
    written: list[Path] = []
    for page_num, question in iter_questions(questions):
        question_name = question.get("question_name") or f"question-{page_num}"
        page = render_page(
            question,
            humanize_schema=per_question.get(question_name),
            custom_css=custom_css,
            progress=progress_module.resolve(
                progress_config, page_num - 1, total, names
            ),
        )
        path = out_dir / f"{prefix}{page_num:02d}-{_slug(question_name)}.html"
        path.write_text(page, encoding="utf-8")
        written.append(path)
    return written
