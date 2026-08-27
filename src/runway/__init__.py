"""Runway -- static HTML previews of EDSL human-survey questions.

Renders a question dict -- the shape ``edsl``'s ``question.to_dict()``
produces, which is also what the live web survey consumes -- into a
self-contained HTML page that looks like the page a respondent is served.

Not every question type has a control here yet; the rest render a full page
with a note in place of the input, so a mixed survey still previews end to end.
:data:`SUPPORTED_QUESTION_TYPES` is the current set, and README.md has the
table.

Markup lives in ``templates/`` and is rendered with Jinja. Two constraints
shape it: byte parity with the reference implementation's server-rendered
output, and escaping that matches it exactly. Both are documented in README.md.

    from runway import load, render_page
    questions = load(Path("survey.ep"))
    html = render_page(questions[0], humanize_schema={"format": {"type": "dropdown"}})

:func:`load` reads any of the formats edsl saves a survey as -- ``.ep``,
``.json.gz`` and ``.json``, all of them through ``Survey.load()`` -- and raises
:class:`SurveyLoadError` for anything it cannot. It returns questions and only
questions; a humanize schema is not part of an EDSL survey, and comes from
:func:`load_schema` and its own file.
"""

from __future__ import annotations

from . import inspection, progress
from .markdown import render_option_text, render_question_text
from .question_types import RENDERERS, get_renderer
from .renderer import (
    render_body,
    render_bundle,
    render_comment,
    render_page,
    render_progress,
    render_question,
    render_question_with_comment,
)
from .survey import (
    SurveyLoadError,
    item_names,
    iter_questions,
    load,
    load_schema,
    previewable,
    render_survey,
)

__all__ = [
    "RENDERERS",
    "SUPPORTED_QUESTION_TYPES",
    "SurveyLoadError",
    "__version__",
    "get_renderer",
    "inspection",
    "item_names",
    "iter_questions",
    "load",
    "load_schema",
    "previewable",
    "progress",
    "render_body",
    "render_bundle",
    "render_comment",
    "render_option_text",
    "render_page",
    "render_progress",
    "render_question_text",
    "render_question",
    "render_question_with_comment",
    "render_survey",
]

__version__ = "0.1.0"

SUPPORTED_QUESTION_TYPES = tuple(sorted(RENDERERS))
