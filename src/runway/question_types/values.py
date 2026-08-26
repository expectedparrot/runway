"""How a question's own values are spelled.

Two rules that come from JavaScript rather than from any component, which is why
they sit apart from the renderers using them. A linear scale and a matrix both
answer with numbers and both let an author name a point on the scale, so both
need these -- and a second copy of either is a divergence waiting to happen,
since neither is a rule anybody would arrive at twice by reasoning.
"""

from __future__ import annotations


def as_text(value: object) -> str:
    """A question value as text, the way JavaScript would write it.

    Numeric options are turned into strings over there by interpolating them.
    JavaScript has one number type, so a scale point that arrives as ``1.0`` --
    from a survey serialized by a tool that writes whole numbers as floats --
    reads there as ``1`` and would read here as ``1.0``: every option value and
    label off by a suffix, with nothing to notice it.
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def option_labels(question: dict) -> dict[str, str]:
    """``option_labels`` keyed the way an option will be looked up.

    The reference reads this with the option as a property key, and JavaScript
    property access turns a number into its text form -- so a live question's
    integer keys and a JSON round-tripped question's string keys behave
    identically over there. Normalizing to text is how that holds here too.

    A missing table means unlabelled options, as does an explicit null. The
    reference only tolerates the null in the choice family: reading
    ``option in undefined`` throws, so a linear scale with no ``option_labels``
    at all cannot be served to a respondent. Previewing it as a bare scale says
    more about the question than failing to draw it would.
    """
    labels = question.get("option_labels") or {}
    if not isinstance(labels, dict):
        return {}
    return {as_text(key): str(value) for key, value in labels.items()}
