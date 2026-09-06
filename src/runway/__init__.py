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
output, and escaping that matches it exactly. Both are documented in SPEC.md.

    from runway import load, render_page
    survey = load(Path("survey.ep"))
    question = survey["questions"][0]
    html = render_page(question, humanize_schema={"format": {"type": "dropdown"}})

:func:`load` reads any of the formats edsl saves a survey as -- ``.ep``,
``.json.gz`` and ``.json``, all of them through ``Survey.load()`` -- and raises
:class:`SurveyLoadError` for anything it cannot. It gives back the survey as
``Survey.to_dict()`` writes it: ``questions`` is the item list a preview is
built from, and ``question_groups`` says which of them share a page. A humanize
schema is *not* in there -- it is not part of an EDSL survey -- and comes from
:func:`load_schema` and its own file.
"""

from __future__ import annotations

from . import inspection, pages, progress, scenarios
from .markdown import render_option_text, render_question_text
from .question_types import RENDERERS, get_renderer
from .renderer import (
    render_body,
    render_bundle,
    render_comment,
    render_item,
    render_page,
    render_page_body,
    render_page_of,
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
    "pages",
    "previewable",
    "progress",
    "scenarios",
    "render_body",
    "render_bundle",
    "render_comment",
    "render_item",
    "render_option_text",
    "render_page",
    "render_page_body",
    "render_page_of",
    "render_progress",
    "render_question_text",
    "render_question",
    "render_question_with_comment",
    "render_survey",
]

__version__ = "0.1.0"

SUPPORTED_QUESTION_TYPES = tuple(sorted(RENDERERS))
