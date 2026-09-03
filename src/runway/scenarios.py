"""Binding a survey to a scenario, the way the live page binds one.

A humanized survey can be attached to a scenario list, and each respondent is
assigned one scenario for the whole of their response. Every page they are then
served is rendered with that scenario's values substituted into the question --
so a scenario is not decoration on a survey, it is *which* survey a given
respondent sees. A preview that ignored it would be showing a page nobody is
served.

**The piping is delegated, not transcribed.** Everywhere else in this package a
divergence is caught by comparing against a recording of the reference's output.
Piping has no markup to record -- it transforms the question *before* any
template sees it -- so the equivalent discipline is to call the same edsl
entry points the live page calls, in the same order, with the same replacement
dictionary and the same sandboxed environment. A second implementation of the
replacement rules here would be exactly the unchecked copy the goldens exist to
prevent.

The sandbox is not optional. A survey's question text is researcher-authored
Jinja, and this renders it on whoever's machine typed the command.

``edsl`` is imported inside the functions, as ``survey.load`` does: a render
without ``--scenarios`` never reaches this module, and one that does should pay
for edsl no earlier than it must.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .survey import NON_QUESTION_CLASSES, SurveyLoadError

# Above this, a preview is not what anybody meant -- a scenario list is
# routinely thousands of rows. Refused rather than truncated: a silently
# shortened preview is one that lies about which scenarios were checked.
MAX_SCENARIOS = 25

# How much of a scenario is summarized into its dropdown entry. Long enough to
# tell two apart, short enough to leave the question select room. Values are
# clipped first and the whole line second, so one long key cannot crowd out the
# rest before they are seen.
LABEL_WIDTH = 60
VALUE_WIDTH = 24

# A Jinja reference, down to one attribute: `{{ city }}`, `{{ scenario.city }}`,
# `{{ q1.answer[0] }}` -> `city`, `scenario.city`, `q1.answer`. One level is
# enough to report with -- `scenario.city` says which key, where a bare
# `scenario` says only that the namespace was used. Used only for reporting,
# never for rendering: what resolves a template is edsl.
_REFERENCE = re.compile(
    r"\{\{-?\s*([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)"
)

# The namespace a question's own answer is *not* in. Kept alongside the survey's
# question names, since both are deferred for the same reason.
AGENT = "agent"


class Unresolved:
    """A name with nothing to resolve it to, which renders back into itself.

    ``QuestionBase.render`` renders a question's text as one template, and an
    *attribute read off an undefined name* discards the entire render -- it does
    not raise, it warns and hands the template back untouched. Every reference
    this class stands in for is that shape: ``{{ agent.name }}``,
    ``{{ q1.answer }}``. So on any survey that also names an agent trait or a
    prior answer, which is most surveys worth binding a scenario to, piping
    would silently do nothing at all -- the page would look exactly like an
    unpiped preview, with the only signal a warning on stderr.

    (A *bare* undefined name is the quieter half of the same story:
    ``{{ typo }}`` renders as nothing and the rest of the question pipes around
    it. Nothing can be done about that from here -- it is Jinja's undefined
    printing as empty, and the live page does the same -- but ``check`` reports
    it, since text that silently disappears is worth being told about.)

    Every attribute of one of these is another one, so ``{{ agent.name }}`` and
    ``{{ q1.answer }}`` survive a render as themselves rather than taking the
    question text down with them. That is also what this package's docs promise
    for them -- there is no later pass here to resolve them in, and no data to
    resolve them from.

    The same trick the live page uses to carry a file token through its own
    render, turned to the opposite purpose: that one defers resolution to a
    later pass, this one stands in for a pass that does not exist.

    Nesting terminates. ``render`` repeats until the text stops changing, and one
    of these maps to itself, so the second pass is already a fixed point.

    **Deliberately not a ``str`` subclass**, which is the version of this that
    does not work. A survey in this repository's own examples asks for
    ``{{ pet.answer | length }}``; against a string standing in for the answer,
    ``length`` is the length *of the placeholder text* -- 16 -- and the preview
    shows a plausible wrong number with nothing to notice it by. Against this,
    ``len()`` raises, edsl gives up on the question, and it previews unpiped,
    which is what it did before scenarios existed. **A question that filters a
    deferred name does not pipe at all**, and that is the intended trade: a
    scenario left unsubstituted is visible, a fabricated number is not.
    """

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    def __str__(self) -> str:
        return f"{{{{ {self._name} }}}}"

    __repr__ = __str__

    def __getattr__(self, item: str) -> Unresolved:
        # Underscored names are refused rather than answered. `_name` itself is
        # one, so answering them would recurse on an instance that lost it, and
        # a `hasattr(x, "__html__")`-style probe would get a value where it
        # tested for a capability. Jinja's sandbox blocks underscored attributes
        # anyway, so nothing legitimate asks.
        if item.startswith("_"):
            raise AttributeError(item)
        return Unresolved(f"{self._name}.{item}")

    def __getitem__(self, item: object) -> Unresolved:
        return Unresolved(f"{self._name}[{item!r}]")


def load(path: Path) -> list[dict]:
    """The scenarios in a scenario list file, in order.

    ``ScenarioList.load()`` opens the same three formats ``Survey.load()`` does
    -- ``.ep``, ``.json.gz`` and ``.json`` -- so this is that function's twin,
    down to raising :class:`SurveyLoadError` with a message already fit to
    print.

    CSV is not among them: the pinned edsl has no ``ScenarioList.from_csv``, and
    guessing at one here would be a second reader for a format edsl does not
    claim.
    """
    try:
        from edsl.scenarios import ScenarioList
    except ImportError as exc:  # pragma: no cover - a declared dependency
        raise SurveyLoadError(
            f"{path} needs edsl to open, and it is not installed: {exc}"
        ) from exc
    try:
        scenario_list = ScenarioList.load(str(path))
    except Exception as exc:
        raise SurveyLoadError(
            f"{path} could not be opened by edsl as a scenario list "
            f"({type(exc).__name__}: {exc}). Save one with ScenarioList.save()."
        ) from exc
    scenarios = [dict(scenario) for scenario in scenario_list]
    if not scenarios:
        raise SurveyLoadError(f"{path} is a scenario list with no scenarios in it")
    return scenarios


def parse_indices(spec: str, total: int) -> list[int]:
    """The scenarios ``--scenario-index`` names, in the order it named them.

    Accepts single indices and ``a-b`` ranges, comma-separated: ``0``,
    ``0,3,7``, ``0-9``, ``0-2,17``. Repeats collapse to the first mention, so a
    list that says something twice renders it once -- the same reading
    :func:`survey.output_paths`' caller gives a survey named twice.

    Raises :class:`ValueError` with a message fit to print.
    """
    chosen: list[int] = []
    seen: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part.lstrip("-"):
            start_text, _, end_text = part.partition("-")
            bounds = (start_text.strip(), end_text.strip())
        else:
            bounds = (part, part)
        try:
            start, end = int(bounds[0]), int(bounds[1])
        except ValueError:
            raise ValueError(
                f"{part!r} is not a scenario index or range (try 0, 0-9, or 0,3,7)"
            ) from None
        if start > end:
            raise ValueError(f"{part!r} counts backwards")
        for index in range(start, end + 1):
            if index < 0 or index >= total:
                raise ValueError(
                    f"there is no scenario {index}: the list has {total} "
                    f"(0-{total - 1})"
                )
            if index not in seen:
                seen.add(index)
                chosen.append(index)
    if not chosen:
        raise ValueError("no scenarios selected")
    return chosen


def _is_file_value(value: object) -> bool:
    """Whether a scenario value is a serialized FileStore."""
    return isinstance(value, dict) and value.get("is_file_store") is True


def _clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def _summarize(value: object) -> str:
    """One scenario value, short enough to sit beside the others.

    A list is written out rather than repr'd: a piped option list is a perfectly
    ordinary scenario value, and ``['The T', 'Commuter rail']`` spends a third of
    the label on quotes and brackets. Clipped per value, not only at the end, so
    one long key cannot crowd out the ones that actually tell two scenarios
    apart. A file-valued key is named without its contents, which are a
    serialized file.
    """
    if _is_file_value(value):
        return "<file>"
    if isinstance(value, (list, tuple)):
        return "[" + _clip(", ".join(str(item) for item in value), VALUE_WIDTH) + "]"
    if isinstance(value, dict):
        return "{…}"
    return _clip(str(value), VALUE_WIDTH)


def label(index: int, scenario: dict) -> str:
    """A scenario's entry in the dropdown: its index, then enough to tell it apart.

    The index comes first because it *is* the identity -- it is how the live
    survey names a scenario, so it is the number worth carrying back to a bug
    report -- and a summary follows because nobody can pick a scenario from a
    bare integer.
    """
    summary = ", ".join(
        f"{key}={_summarize(value)}" for key, value in scenario.items()
    )
    return f"{index} — {_clip(summary, LABEL_WIDTH)}" if summary else str(index)


def replacements(scenario: dict, question_names: list[str]) -> dict:
    """The dictionary a question is rendered against.

    Reproduces the live page's construction, whose two load-bearing details are
    easy to get wrong:

    **Every non-file key is exposed twice** -- bare (``{{ city }}``) and
    namespaced (``{{ scenario.city }}``). Both spellings are in real surveys and
    both have to work.

    **A file-store key is exposed bare only**, as the marker ``<see file key>``,
    and is deliberately absent from the ``scenario`` namespace -- so
    ``{{ scenario.photo }}`` is an undefined name on the live page too. This
    package resolves no media, so the marker is what lands on the page: the text
    form the live page held before its own media pass.

    Everything the survey could otherwise reference -- the agent namespace, and
    every question's answer -- is seeded with an :class:`Unresolved`, so those
    references survive as written instead of discarding the render. A scenario
    key wins a collision with a question name: the live page would resolve that
    to the answer, which there is nothing here to supply, so the scenario value
    is the only reading that resolves to anything at all.
    """
    file_keys = [key for key, value in scenario.items() if _is_file_value(value)]
    plain = {key: value for key, value in scenario.items() if key not in file_keys}
    deferred = {name: Unresolved(name) for name in (AGENT, *question_names)}
    return {
        **deferred,
        **{key: f"<see file {key}>" for key in file_keys},
        **plain,
        "scenario": plain,
    }


def root_of(reference: str) -> str:
    """The name a reference resolves against: ``scenario.city`` -> ``scenario``."""
    return reference.split(".", 1)[0]


def references(question: dict) -> list[str]:
    """What a question's templates refer to, in first-seen order.

    Read off the source with a regex rather than from a parse, and used only for
    reporting -- ``check`` says which questions pipe and which name something
    nothing can resolve. Nothing rendered is decided here.
    """
    sources: list[str] = []
    for key in ("question_text", "question_options", "question_items"):
        value = question.get(key)
        if isinstance(value, str):
            sources.append(value)
        elif isinstance(value, list):
            sources.extend(item for item in value if isinstance(item, str))
        elif isinstance(value, dict):
            sources.extend(str(item) for item in value.values())
    found: list[str] = []
    for source in sources:
        for reference in _REFERENCE.findall(source):
            if reference not in found:
                found.append(reference)
    return found


def unresolved(question: dict, scenario: dict, question_names: list[str]) -> list[str]:
    """Referenced names that nothing can resolve, in either of the two ways.

    Not the same as a deferred name. ``{{ agent.x }}`` and ``{{ q1.answer }}``
    have somewhere to go -- they render back as themselves. A name that is
    neither those nor a scenario key is undefined, and undefined fails twice
    over, both times without a mark on the page:

    * ``{{ typo }}`` renders as **nothing**. The words vanish and the rest of
      the question pipes around the hole.
    * ``{{ typo.attr }}`` discards the **whole question's** render, so every
      other scenario key in it stays as written too.

    Both are what the live page does with the same survey, so neither is worth
    working around -- but neither is visible in the result either, which is why
    ``check`` says them out loud.
    """
    known = set(scenario) | {"scenario", AGENT} | set(question_names)
    return [
        reference
        for reference in references(question)
        if root_of(reference) not in known
    ]


def _piped_fields(data: dict, scenario: dict) -> dict:
    """Resolve templated ``question_options`` / ``question_items`` in place.

    These are the two fields a template can stand in for *whole*, rather than
    appear inside: ``question_options`` may be the string ``"{{ brands }}"``
    naming a list. ``render`` cannot do it -- it would substitute the list's
    text form into a string field -- so the live page runs edsl's option
    processor first, and so does this.

    Gated on the field actually being a template, not on the question's type.
    The live page's gate also names four question classes, because there a
    resolved list is about to be shuffled by ``draw()`` and the shuffle takes a
    string apart character by character. Nothing here draws, so the narrower
    gate would only mean leaving a top-k's options unresolved for a reason that
    does not apply.
    """
    from edsl.invigilators.question_instructions_prompt_builder import (
        QuestionInstructionPromptBuilder,
    )
    from edsl.scenarios import Scenario

    templated = isinstance(data.get("question_options"), str) or isinstance(
        data.get("question_items"), (str, dict)
    )
    if not templated:
        return data
    return QuestionInstructionPromptBuilder._process_question_options(
        data, Scenario(scenario), {}
    )


def pipe_question(question: dict, scenario: dict, render_dict: dict) -> dict:
    """One question, bound to one scenario.

    Anything that goes wrong leaves the question exactly as it arrived. A
    preview that died on question 14 of 20 would be worse than one showing
    question 14 as written, and a question whose options stay a template already
    has a rendering -- the explanatory line the live page shows for one -- so the
    fallback is this package's existing behaviour rather than a new one.
    """
    from edsl.questions import QuestionBase

    try:
        data = _piped_fields(dict(question), scenario)
        rendered = QuestionBase.from_dict(data).render(
            render_dict, jinja_env=_sandbox()
        )
        return rendered.to_dict()
    except Exception:
        return question


def _sandbox():
    from jinja2.sandbox import SandboxedEnvironment

    return SandboxedEnvironment()


def pipe(questions: list[dict], scenario: dict) -> list[dict]:
    """A survey's items, bound to one scenario.

    Instructions are passed through untouched: they are not questions, edsl does
    not render them through ``QuestionBase``, and this package does not preview
    them either -- but they hold their place in the list, because position is
    counted over every item.
    """
    names = [
        question["question_name"]
        for question in questions
        if question.get("question_name")
    ]
    render_dict = replacements(scenario, names)
    return [
        question
        if question.get("edsl_class_name") in NON_QUESTION_CLASSES
        else pipe_question(question, scenario, render_dict)
        for question in questions
    ]


def load_selection(
    path: Path, index_spec: str | None
) -> list[tuple[int, dict]]:
    """The scenarios to render, as ``(index, scenario)`` pairs.

    The indices are the scenario list's own, and they stay so through the
    dropdown: ``--scenario-index 0,17,204`` shows entries reading 0, 17 and 204,
    not 0, 1 and 2. That is the number the live survey identifies a scenario by,
    so renumbering them would be inventing a second naming for the one thing a
    preview and a live response have in common.

    Raises :class:`SurveyLoadError` for a file that will not open, a selection
    that names nothing, or a list long enough that rendering all of it was not
    what anyone meant.
    """
    scenarios = load(path)
    if index_spec is None:
        if len(scenarios) > MAX_SCENARIOS:
            raise SurveyLoadError(
                f"{path} has {len(scenarios):,} scenarios, and a preview renders "
                f"every one of them. Pick some with --scenario-index "
                f"(e.g. --scenario-index 0-9, or 0,17,204)."
            )
        indices = list(range(len(scenarios)))
    else:
        try:
            indices = parse_indices(index_spec, len(scenarios))
        except ValueError as exc:
            raise SurveyLoadError(f"--scenario-index {index_spec}: {exc}") from exc
    return [(index, scenarios[index]) for index in indices]


def _main() -> int:  # pragma: no cover - developer convenience
    """Print what one scenario does to a survey, for a quick look."""
    import sys

    if len(sys.argv) != 3:
        print("usage: python -m runway.scenarios SURVEY SCENARIOS", file=sys.stderr)
        return 2
    from .survey import load as load_survey

    questions = load_survey(Path(sys.argv[1]))
    scenarios = load(Path(sys.argv[2]))
    piped = pipe(questions, scenarios[0])
    print(json.dumps([q.get("question_text") for q in piped], indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
