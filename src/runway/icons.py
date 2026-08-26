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
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
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
    "triangle-alert": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"></path>'
        '<path d="M12 9v4"></path>'
        '<path d="M12 17h.01"></path>'
    ),
}


def render(name: str, *, size: int = 24, class_name: str = "") -> str:
    """Return the inline ``<svg>`` for a lucide icon."""
    geometry = _GEOMETRY[name]
    attrs = _LUCIDE_ATTRS.format(size=size)
    classes = f"lucide lucide-{name}"
    if class_name:
        classes = f"{classes} {class_name}"
    return f'<svg {attrs} class="{classes}" aria-hidden="true">{geometry}</svg>'
