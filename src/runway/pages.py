"""Which of a survey's questions land on one page.

A human survey serves one item per page. A survey that defines **question
groups** and asks for them -- ``humanize_schema["survey"]["presentation"]`` set
to ``"group"`` -- is served a whole group at a time instead, so a page is a run
of questions rather than a single one. Both settle to a list of pages here, and
everything downstream reads one shape: a preview of a three-question group is
not a special case of a preview of one question.

**The groups live on the survey; the schema selects how to present them.**
Neither half enables grouped pages on its own -- a survey with groups whose
schema says nothing still previews one question per page, which is what the live
survey serves it as.

The arithmetic is the fiddly part, and it is the same arithmetic the reference
implementation's own author-side preview does:

* A group's range is a pair of indices into the survey's **questions**, while a
  survey's item list interleaves instructions among them. So a question's group
  is looked up by its position among the questions, not by its position here.
* **An instruction takes the group of the next question after it**, which is how
  EDSL attaches one to a group when it serves the page. A trailing instruction
  with no question after it takes the last group.
* A question in no group gets a page of its own, marked ``unserved``. The live
  survey, paging by group, never serves it at all, and EDSL refuses to build a
  human survey from a grouped survey that leaves one out -- so the page is drawn
  with a warning in place of its control, the way a question nobody is asked is.
  A preview that dropped it would be the one place an author could not see what
  they had done.

Instructions have no preview of their own yet, so a page carries only its
questions; what the assignment above decides is where the page *starts*, which
is what its progress reading is measured against.
"""

from __future__ import annotations

from dataclasses import dataclass

# Non-question items in an EDSL survey's item list, repeated from ``survey`` --
# which imports this module, not the other way round: pagination is upstream of
# reading a file, and a preview built from question dicts in memory needs it
# without needing a loader.
NON_QUESTION_CLASSES = {"Instruction", "ChangeInstruction"}

# What ``presentation`` can say. Anything else -- a value from a newer server --
# reads as the default, the same way an unknown progress type falls back to the
# bar rather than raising.
PER_QUESTION = "question"
PER_GROUP = "group"


@dataclass(frozen=True)
class Page:
    """One page of the survey: what a respondent is served at once.

    ``positions`` are indices into the survey's *previewable* questions -- the
    list :func:`survey.previewable` returns, and the same numbering a group's
    range is written in. ``index`` is where the page begins among *all* the
    survey's items, instructions included, which is the position its progress
    indicator is resolved at. ``group`` is the author's own name for the group,
    or ``None`` for a page that is one question.

    ``unserved`` marks the page nobody is ever shown: a question left out of
    every group, in a survey that pages by them. Never true of an ordinary
    survey, where a page without a group is simply the usual kind of page --
    which is why this is a field of its own rather than something read off
    ``group is None``.
    """

    positions: tuple[int, ...]
    index: int
    group: str | None
    name: str
    unserved: bool = False


def presentation(humanize_schema: dict | None) -> str:
    """How the survey pages, per its humanize schema.

    ``"question"`` for a schema that says nothing, which is every survey written
    before grouped presentation existed.
    """
    survey_schema = (humanize_schema or {}).get("survey") or {}
    return survey_schema.get("presentation") or PER_QUESTION


def normalize(question_groups: dict | None) -> dict[str, tuple[int, int]]:
    """A survey's ``question_groups``, as ranges this module can walk.

    edsl holds them as tuples and JSON gives them back as lists, so a survey read
    from a ``.json`` and the same survey read from a ``.ep`` would otherwise
    describe their groups differently -- the same trap ``option_labels`` keys
    fall into. Anything that is not a pair of integers is dropped rather than
    raised on: a preview should still draw the groups it can read.

    Insertion order is kept, because it is the author's order and the order the
    pages come out in.
    """
    normalized: dict[str, tuple[int, int]] = {}
    for name, span in (question_groups or {}).items():
        if not isinstance(span, (list, tuple)) or len(span) != 2:
            continue
        start, end = span
        if isinstance(start, bool) or isinstance(end, bool):
            continue
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        normalized[str(name)] = (start, end)
    return normalized


def is_question(item: dict) -> bool:
    """Whether a survey item is a question rather than an instruction."""
    return item.get("edsl_class_name") not in NON_QUESTION_CLASSES


def _name_of(item: dict, fallback: str) -> str:
    return item.get("question_name") or item.get("name") or fallback


def _group_at(groups: dict[str, tuple[int, int]], position: int) -> str | None:
    """The group holding the question at ``position``, or ``None``.

    First match wins, as it does in the reference: groups are not supposed to
    overlap -- EDSL refuses a schema whose do -- and picking one is better than
    inventing a page from two.
    """
    for name, (start, end) in groups.items():
        if start <= position <= end:
            return name
    return None


def _per_question(items: list[dict]) -> list[Page]:
    """One page per question: what every survey did before groups."""
    pages = []
    position = 0
    for index, item in enumerate(items):
        if not is_question(item):
            continue
        pages.append(
            Page(
                positions=(position,),
                index=index,
                group=None,
                name=_name_of(item, f"question-{position + 1}"),
            )
        )
        position += 1
    return pages


def resolve(
    items: list[dict],
    question_groups: dict | None = None,
    humanize_schema: dict | None = None,
) -> list[Page]:
    """The pages a survey is served as, in order.

    ``items`` is the survey's whole item list -- questions and instructions, as
    ``Survey.to_dict()["questions"]`` gives it. ``question_groups`` is the
    survey's own, from the same document.

    Grouped pages need both halves: a schema asking for them and a survey with
    groups to page by. Given one without the other this returns a page per
    question, which is what the live survey serves in that case too. (EDSL's
    ``validate_humanize_schema`` rejects the combination when it can see both at
    once; nothing here can, since a schema arrives separately from its survey.)
    """
    groups = (
        normalize(question_groups)
        if presentation(humanize_schema) == PER_GROUP
        else {}
    )
    if not groups:
        return _per_question(items)

    # Questions first, by their own index among the questions; instructions are
    # left unassigned for the moment.
    assigned: list[str | None] = []
    position = 0
    for item in items:
        if is_question(item):
            assigned.append(_group_at(groups, position))
            position += 1
        else:
            assigned.append(None)

    # Then instructions, each taking the group of the next question after it.
    # Walking backwards means a run of instructions all inherit the same one, and
    # a trailing instruction inherits the last group in the survey.
    #
    # Only instructions: a *question* left unassigned is in no group and must
    # stay that way. Letting it inherit here would fold it into the following
    # group's page, which is the one thing that cannot happen at runtime -- a
    # question outside every group is never served.
    carry = next((name for name in reversed(assigned) if name is not None), None)
    for index in reversed(range(len(items))):
        if assigned[index] is not None:
            carry = assigned[index]
        elif not is_question(items[index]):
            assigned[index] = carry

    # Consecutive items sharing a group are one page; anything ungrouped is a
    # page of its own -- and one nobody is served, which is what `unserved`
    # below says.
    runs: list[tuple[str | None, int, list[int]]] = []
    position = 0
    for index, item in enumerate(items):
        group = assigned[index]
        question = position if is_question(item) else None
        if question is not None:
            position += 1
        previous = runs[-1] if runs else None
        if previous is not None and group is not None and previous[0] == group:
            if question is not None:
                previous[2].append(question)
            continue
        runs.append((group, index, [question] if question is not None else []))

    # A page with nothing on it is a page nobody could be shown: an instruction
    # run that inherited no group at all. Dropped rather than drawn empty, which
    # is also what a survey without groups does with its instructions today.
    return [
        Page(
            positions=tuple(positions),
            index=index,
            group=group,
            name=group
            if group is not None
            else _name_of(items[index], f"question-{positions[0] + 1}"),
            unserved=group is None,
        )
        for group, index, positions in runs
        if positions
    ]
