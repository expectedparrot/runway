"""How far through the survey the respondent is, in the shape the page draws.

One payload per page, discriminated on ``type``, carrying only what its
rendering needs: a bar needs the fraction it fills to, a stepper needs its
markers' states, and a hidden indicator needs nothing at all.

The live survey resolves this server-side, from the survey's ``progress`` config
and the page it is serving; the page component switches on ``type`` and draws it
without consulting the config. This module is that resolution, for a preview's
fixed position in the survey -- so the same config previews as the same
indicator, and the rendering decision is not made a second way here.

The two readings measure the same position from opposite ends. A bar says how
much is *done*, so a respondent looking at the first question has done none of
it and the bar reads 0%. A stepper says where they *are*, so on that same page
it already sits on step one. Neither is derivable from the other.
"""

from __future__ import annotations

from collections.abc import Sequence

# What an unconfigured survey draws. ``progress`` absent has to keep meaning
# "the bar", or every survey written before the field existed would preview
# without the indicator it actually renders.
PERCENT_LABEL = {"type": "percent"}
HIDDEN: dict = {"type": "hidden"}

# Statuses a step can carry. A newer server may add one -- "skipped" is the
# obvious next -- and the page renders an unrecognized status as upcoming rather
# than blanking the marker, so this is a floor, not a closed set.
STEP_STATUSES = ("complete", "current", "upcoming")


def bar(fraction: float, label: dict | None = PERCENT_LABEL) -> dict:
    """A bar filled to ``fraction`` of the survey, captioned per ``label``."""
    return {"type": "bar", "fraction": fraction, "label": label}


def steps(marker: str, resolved: list[tuple[str | None, str]]) -> dict:
    """A stepper from ``(label, status)`` pairs already in survey order."""
    return {
        "type": "steps",
        "marker": marker,
        "steps": [{"label": label, "status": status} for label, status in resolved],
    }


def resolve(
    config: dict | None,
    index: int,
    total: int,
    item_names: Sequence[str] = (),
) -> dict:
    """The indicator to draw on the page showing item ``index`` of ``total``.

    ``config`` is the survey's ``humanize_schema["survey"]["progress"]``, and
    ``item_names`` the names of every survey item in order -- questions and
    instructions alike, since a step may end on either.

    An unrecognized ``type`` falls back to the bar rather than raising: a config
    written for a newer renderer should preview as *something*, and the bar is
    what the survey rendered before any of this was configurable.
    """
    kind = (config or {}).get("type", "bar")

    if kind == "hidden":
        return dict(HIDDEN)

    if kind == "steps":
        stepped = _steps(config or {}, index, item_names)
        if stepped is not None:
            return stepped
        # Too few of its steps still resolve. The live survey falls back to the
        # bar here too, rather than leaving the page with no indicator.

    label = (
        (config or {}).get("label", PERCENT_LABEL) if kind == "bar" else PERCENT_LABEL
    )
    return bar(index / total if total else 0.0, label)


def _steps(config: dict, index: int, item_names: Sequence[str]) -> dict | None:
    """The stepper, or None when too few of its steps resolve to render one.

    A step is a *boundary*, not a bucket: it covers every item from the end of
    the previous step through ``complete_after``. A step naming an item the
    survey no longer has is dropped rather than drawn as a marker the respondent
    could never pass -- and a single marker is not a progress indicator, so
    fewer than two means there is nothing to draw.
    """
    index_by_name = {}
    for position, name in enumerate(item_names):
        # First occurrence wins, matching how a survey addresses its items.
        index_by_name.setdefault(name, position)

    resolved: list[tuple[str | None, int | None]] = []
    for step in config.get("steps") or []:
        boundary = step.get("complete_after")
        if boundary is None:
            # The final step, which runs to the end of the survey.
            resolved.append((step.get("label"), None))
            continue
        if boundary in index_by_name:
            resolved.append((step.get("label"), index_by_name[boundary]))

    if len(resolved) < 2:
        return None

    # The current step is the first whose boundary the respondent has not passed.
    # Taking the first rather than counting the boundaries behind them keeps the
    # rendering coherent even if the steps were authored out of survey order.
    current = next(
        (
            position
            for position, (_, boundary) in enumerate(resolved)
            if boundary is None or boundary >= index
        ),
        # Past every boundary: a final step given an explicit boundary with items
        # after it. Hold on the last step rather than reading as finished.
        len(resolved) - 1,
    )

    return steps(
        config.get("marker") or "number",
        [
            (
                label,
                "complete"
                if position < current
                else "current"
                if position == current
                else "upcoming",
            )
            for position, (label, _) in enumerate(resolved)
        ],
    )
