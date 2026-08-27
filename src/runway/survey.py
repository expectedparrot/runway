"""Survey-level input handling and output writing."""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

from . import progress as progress_module
from .renderer import render_bundle, render_page

# Non-question items in an EDSL survey's item list. Skipped for now; they are
# not questions and have no preview yet.
NON_QUESTION_CLASSES = {"Instruction", "ChangeInstruction"}

# The formats edsl saves a survey as, and so the only ones read here. ``.ep`` is
# the package ``Survey.save()`` writes by default -- a git repository in a zip,
# one JSON file per question. The other two are the plain and compressed dumps
# of ``Survey.to_dict()``.
PACKAGE_SUFFIX = ".ep"
JSON_SUFFIXES = (".json.gz", ".json")
SURVEY_SUFFIXES = (PACKAGE_SUFFIX, *JSON_SUFFIXES)


class SurveyLoadError(Exception):
    """A survey or schema file that could not be read.

    Carries a message already fit to print: the CLI reports these rather than
    letting a bad path become a traceback, and a survey can fail to load in more
    ways than one caller should have to know about -- malformed JSON, a missing
    ``git``, a document edsl will not accept as a survey.
    """


def _slug(value: str) -> str:
    """Filesystem-safe stem for a question name."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return cleaned or "question"


def name_for(path: Path) -> str:
    """A survey's own name: its file name with the format suffix taken off.

    ``Path.stem`` is right for ``.json`` and for ``.ep``, but leaves the
    ``.json`` behind on a ``.json.gz`` -- which would name the output
    ``survey.json.html``. The name is what written files are stemmed with, so it
    is worth it being the survey's rather than the file's.
    """
    name = path.name
    for suffix in SURVEY_SUFFIXES:
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _json_document(path: Path) -> dict | list | None:
    """The raw JSON behind a survey file, or ``None`` if there is none to read.

    Called only to explain a failure, never on the path that succeeds: the
    questions come from ``Survey.load()``, and nothing else in a survey file is
    this package's to read. An unreadable file answers ``None`` too -- there is
    no diagnosis to offer, and the caller already has a failure to report.
    """
    if not path.name.lower().endswith(JSON_SUFFIXES):
        return None
    compressed = path.name.lower().endswith(".json.gz")
    try:
        with (
            gzip.open(path, "rt", encoding="utf-8")
            if compressed
            else path.open(encoding="utf-8")
        ) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _explain(path: Path, exc: Exception) -> str:
    """Why a survey file would not load, said in terms of the file.

    edsl reports wherever it gave up, which is rarely where the problem is: a
    ``ValueError`` about sequence lengths for a bare list of question dicts, a
    bare ``KeyError`` for a survey missing its flow. Both of those are shapes a
    survey file used to be allowed to have here, so they are what someone
    arriving with an older file hits, and both are worth naming.
    """
    detail = f"{type(exc).__name__}: {exc}"
    document = _json_document(path)
    if isinstance(document, list):
        return (
            f'{path} is a bare list of question dicts. Wrap it in {{"questions": '
            "[...]}, or save the survey with Survey.save(): a survey file has to "
            "be a survey, not just its questions."
        )
    if isinstance(document, dict):
        missing = [
            key for key in ("memory_plan", "rule_collection") if not document.get(key)
        ]
        if missing:
            return (
                f"{path} has no {' and no '.join(missing)}, which edsl needs to "
                f"build a survey ({detail}). Save a real Survey with "
                "Survey.save() rather than approximating its dump."
            )
    return f"{path} could not be opened by edsl ({detail})."


def load(path: Path) -> list[dict]:
    """The questions in a survey file, whatever format it is in.

    A ``.ep`` package, a ``.json.gz`` dump and a ``.json`` dump are all opened by
    ``Survey.load()``, which dispatches on the file name itself -- so what a
    ``.ep`` package actually is stays edsl's business, and a ``.json`` is read by
    the code that wrote it rather than by a second, lookalike reader here. The
    survey that comes back is flattened with ``to_dict()`` into question dicts,
    which is what everything downstream renders from.

    Loading through edsl is also what makes the formats agree. A survey does not
    survive JSON unchanged -- integer ``option_labels`` keys come back as
    strings, among other things -- so a JSON file read directly and a package
    read through edsl could describe the same survey and preview differently.
    Reading both the same way is what stops that; ``tests/test_formats.py``
    holds them to it.

    Only the questions come back, because only the questions are in the file. A
    humanize schema is not part of an EDSL survey -- edsl neither writes one nor
    reads one -- so it reaches a preview through :func:`load_schema` and nowhere
    else. A ``humanize_schema`` key written into a survey document is not a
    survey's to carry and is ignored, as it would be by edsl.

    edsl is imported here rather than at module scope. Rendering never touches
    it, so `types`, `version`, `guide` and every library call that starts from a
    question dict stay as cheap as they were.

    Opening a package shells out to ``git``, which is a runtime requirement
    nothing else here has; a machine without it fails on this line, and the
    message says which file was being read when it did. A package that Coop
    holds is also synced against the remote by ``load()`` before it is returned,
    which is the only path in this tool that reaches the network or writes to
    its own input -- edsl's behaviour rather than this package's, and noted in
    the README under Known gaps because nothing else here does either.

    Raises :class:`SurveyLoadError` for anything unreadable.
    """
    try:
        from edsl.surveys import Survey
    except ImportError as exc:  # pragma: no cover - a declared dependency
        raise SurveyLoadError(
            f"{path} needs edsl to open, and it is not installed: {exc}"
        ) from exc
    try:
        survey = Survey.load(str(path))
    except Exception as exc:
        raise SurveyLoadError(_explain(path, exc)) from exc
    return survey.to_dict().get("questions") or []


def load_schema(path: Path) -> dict:
    """Read a humanize schema saved on its own.

    This is the only way a schema reaches a preview. It is not part of an EDSL
    survey -- edsl neither writes one nor reads one -- so it is configured and
    saved on its own, whatever format the survey itself is in.

    The schema is the object with ``survey`` and ``questions`` keys -- the shape
    ``Survey.humanize()`` takes. A file that wraps it under ``humanize_schema``
    is accepted too, that being what the parameter is called and so a natural
    thing to have saved it as.

    A survey document handed over by mistake is refused rather than read for
    what it does not have: a schema's ``questions`` is an object keyed by
    question name, where a survey's is a list.

    Raises :class:`SurveyLoadError` for anything unreadable.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SurveyLoadError(f"{path} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise SurveyLoadError(f"{path} could not be read: {exc}") from exc
    if not isinstance(data, dict):
        raise SurveyLoadError(f"{path}: a humanize schema is an object, not a list")
    wrapped = data.get("humanize_schema")
    if isinstance(wrapped, dict):
        return wrapped
    if isinstance(data.get("questions"), list):
        raise SurveyLoadError(
            f"{path}: this looks like a survey document rather than a humanize "
            "schema: its 'questions' is a list of questions, not a table keyed by name"
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


def _page_name(page_num: int, question: dict) -> str:
    """The file name one split page takes, without its prefix or directory."""
    question_name = question.get("question_name") or f"question-{page_num}"
    return f"{page_num:02d}-{_slug(question_name)}.html"


def output_paths(
    questions: list[dict],
    out_dir: Path | None = None,
    split: bool = False,
    name: str | None = None,
) -> list[Path]:
    """The files :func:`render_survey` would write, without writing them.

    The CLI asks this of every survey it was given and refuses the set if two
    would write the same file. What that is depends on the questions and on
    ``split``, not on the survey's name alone: two surveys sharing a name split
    into pages named after *their questions*, which may not overlap at all.

    :func:`render_survey` writes to exactly these paths, in this order, so the
    two cannot disagree about where a preview lands.
    """
    out_dir = Path(out_dir or "previews")
    stem = _slug(name) if name else ""
    if not split:
        return [out_dir / f"{stem or 'index'}.html"]
    prefix = f"{stem}-" if stem else ""
    return [
        out_dir / f"{prefix}{_page_name(page_num, question)}"
        for page_num, question in iter_questions(questions)
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
    passes the survey file's own name, and refuses a set whose names agree.
    Omitted, the bundle is ``index.html`` and split pages are numbered alone --
    right for a directory holding the one survey.
    """
    humanize_schema = humanize_schema or {}
    out_dir = Path(out_dir or "previews")
    out_dir.mkdir(parents=True, exist_ok=True)

    names = item_names(questions)
    items = previewable(questions)
    written = output_paths(questions, out_dir, split=split, name=name)
    if not split:
        written[0].write_text(
            render_bundle(items, humanize_schema, title=title, item_names=names),
            encoding="utf-8",
        )
        return written

    survey_schema = humanize_schema.get("survey") or {}
    per_question = humanize_schema.get("questions") or {}
    custom_css = survey_schema.get("custom_css")
    progress_config = survey_schema.get("progress")
    total = len(questions)

    # strict: output_paths and this loop walk the same questions, and a
    # disagreement would silently drop or misname a page.
    for (page_num, question), path in zip(
        iter_questions(questions), written, strict=True
    ):
        question_name = question.get("question_name") or f"question-{page_num}"
        path.write_text(
            render_page(
                question,
                humanize_schema=per_question.get(question_name),
                custom_css=custom_css,
                progress=progress_module.resolve(
                    progress_config, page_num - 1, total, names
                ),
            ),
            encoding="utf-8",
        )
    return written
