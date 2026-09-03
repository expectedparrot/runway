"""Inline SVG copies of the lucide icons the web survey's components use.

Those components render icons through ``lucide-react``; a static page has to
carry the markup itself. Geometry is copied from lucide-react 0.539.0, and the
surrounding attributes match what its icon factory emits, so the rendered
markup is identical to the live page's.

Icons are ISC licensed -- see LICENSES.md.
"""

from __future__ import annotations

_LUCIDE_ATTRS = (
    'xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="{stroke_width}" '
    'stroke-linecap="round" stroke-linejoin="round"'
)

# name -> inner SVG geometry, verbatim from lucide-react's icon nodes.
_GEOMETRY = {
    "info": (
        '<circle cx="12" cy="12" r="10"></circle>'
        '<path d="M12 16v-4"></path>'
        '<path d="M12 8h.01"></path>'
    ),
    "plus": (
        '<path d="M5 12h14"></path>'
        '<path d="M12 5v14"></path>'
    ),
    "x": (
        '<path d="M18 6 6 18"></path>'
        '<path d="m6 6 12 12"></path>'
    ),
    # The carousel's two nav arrows, which are the only icons the reference
    # draws at a weight other than lucide's default -- see ``stroke_width``.
    "chevron-left": '<path d="m15 18-6-6 6-6"></path>',
    "chevron-right": '<path d="m9 18 6-6-6-6"></path>',
    "triangle-alert": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"></path>'
        '<path d="M12 9v4"></path>'
        '<path d="M12 17h.01"></path>'
    ),
}


def render(
    name: str,
    *,
    size: int = 24,
    class_name: str = "",
    stroke_width: float | int = 2,
) -> str:
    """Return the inline ``<svg>`` for a lucide icon.

    ``stroke_width`` is lucide's own default of 2 unless the reference component
    passes something else -- the carousel's arrows are drawn at 1.5. Pass the
    number the component passes: it is formatted the way JavaScript writes it,
    so 1.5 renders as ``1.5`` and 2 as ``2``, never as ``2.0``.
    """
    geometry = _GEOMETRY[name]
    attrs = _LUCIDE_ATTRS.format(size=size, stroke_width=stroke_width)
    classes = f"lucide lucide-{name}"
    if class_name:
        classes = f"{classes} {class_name}"
    return f'<svg {attrs} class="{classes}" aria-hidden="true">{geometry}</svg>'
