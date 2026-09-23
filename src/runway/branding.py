"""The survey's branding: the author's logo, in a banner above the survey.

A humanize schema names a logo at ``survey.branding.logo`` -- its ``source``, its
``alt`` text and a ``position`` -- but not the image. The source is an asset in
the author's library on Coop, named by uuid, and the live page never reads the
schema to draw it either: the server resolves the asset and hands the page a
block of its own, with a signed URL and the image's size, and the banner draws
that block without consulting the config.

:func:`resolve` is that resolution, for a preview. It returns the same block, so
the banner template has one shape to draw whichever way the image arrived:

* **fetched** -- ``assets`` holds the image, from :mod:`assets`, and the block
  carries it as a ``data:`` URI, the way a scenario's own files are carried;
* **not fetched** -- the default, since fetching is a network call and opt-in.
  The block carries :data:`LOGO_PLACEHOLDER` at its own size, so the banner is
  still where the page puts it, positioned as configured, with the alt text the
  author wrote. What is missing is only the picture, which is exactly what an
  offloaded scenario image draws as too.

A preview cannot tell the difference between a logo it was not asked to fetch
and one the live page could not resolve either -- the live page drops the
banner in the second case -- so it draws the placeholder for both, and ``check``
says which logo it is standing in for.
"""

from __future__ import annotations

import base64
import uuid

# What the reference accepts. A newer position reads as left, the reference's
# own fallback for one it does not know.
POSITIONS = ("left", "center", "right")

# The placeholder's intrinsic size. Only the aspect ratio matters -- the banner
# draws a logo 40px tall whatever its size -- and a 4:1 box is the shape of a
# wordmark, which is what most logos in a banner are.
PLACEHOLDER_WIDTH = 160
PLACEHOLDER_HEIGHT = 40

# Drawn in the same palette as the scenario image placeholder in `blocks`, so
# the two read as the same kind of thing: an image goes here, and this page does
# not have it. `[src^="data:image/svg+xml"]` selects it for an author who wants
# it treated differently from a real logo.
_PLACEHOLDER_SVG = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{PLACEHOLDER_WIDTH}" '
    f'height="{PLACEHOLDER_HEIGHT}" viewBox="0 0 {PLACEHOLDER_WIDTH} '
    f'{PLACEHOLDER_HEIGHT}" role="img" aria-label="Logo">'
    '<rect x="0.5" y="0.5" width="159" height="39" rx="6" fill="#eef3fe" '
    'stroke="#5b8cea" stroke-dasharray="4 3"/>'
    '<text x="80" y="25" text-anchor="middle" fill="#5b8cea" '
    'font-family="system-ui, sans-serif" font-size="13" '
    'letter-spacing="0.08em">LOGO</text></svg>'
)

LOGO_PLACEHOLDER = "data:image/svg+xml;base64," + base64.b64encode(
    _PLACEHOLDER_SVG.encode("utf-8")
).decode("ascii")


def logo_config(humanize_schema: dict | None) -> dict | None:
    """The schema's ``survey.branding.logo``, or ``None`` if it names none.

    ``branding`` absent, ``branding: null`` and ``logo: null`` all mean the
    same thing to the reference: no banner.
    """
    survey = (humanize_schema or {}).get("survey") or {}
    branding = survey.get("branding") or {}
    logo = branding.get("logo") if isinstance(branding, dict) else None
    return logo if isinstance(logo, dict) else None


def asset_uuid(logo: dict | None) -> str | None:
    """The asset a logo's source names, canonicalized, or ``None``.

    ``None`` for a source of any other kind -- the schema is built to take more
    than one -- and for a uuid that is not one. Canonicalized because the value
    names a cache file in :mod:`assets`, and a schema is not trusted to spell a
    path.
    """
    source = (logo or {}).get("source")
    if not isinstance(source, dict) or source.get("type", "asset") != "asset":
        return None
    try:
        return str(uuid.UUID(str(source.get("asset_uuid"))))
    except ValueError:
        return None


def data_uri(asset: dict) -> str:
    """A fetched asset's bytes as a ``data:`` URI."""
    return f"data:{asset['mime_type']};base64,{asset['base64']}"


def resolve(humanize_schema: dict | None, assets: dict | None = None) -> dict | None:
    """The branding block the banner draws, or ``None`` for no banner.

    The same shape the live server resolves the schema into, so the template
    is written against one payload whatever produced it. ``assets`` is what
    :func:`assets.fetch` returned, by uuid; a logo whose asset is not in it --
    including every logo when nothing was fetched -- draws as the placeholder.
    """
    logo = logo_config(humanize_schema)
    if logo is None:
        return None
    asset = (assets or {}).get(asset_uuid(logo) or "")
    position = logo.get("position")
    alt = logo.get("alt")
    return {
        "logo": {
            "url": data_uri(asset) if asset else LOGO_PLACEHOLDER,
            # Stripped as the server strips it on the way in; a schema read
            # from a file has not been through that.
            "alt": alt.strip() if isinstance(alt, str) else "",
            "width": asset["width"] if asset else PLACEHOLDER_WIDTH,
            "height": asset["height"] if asset else PLACEHOLDER_HEIGHT,
            "position": position if position in POSITIONS else "left",
        }
    }
