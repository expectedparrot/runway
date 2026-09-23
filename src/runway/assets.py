"""Fetching the images a humanize schema names, which only Coop holds.

A schema names its logo by asset uuid, and the image lives in the author's asset
library on Coop. Getting it means a network call with the caller's Coop
credentials, so it is **opt-in** -- ``render --fetch-assets`` -- and a preview
made without it draws the placeholder; see :mod:`branding`. That is the same
line this package draws for an offloaded scenario file, which it never fetches.

The fetch goes through edsl's own client, ``Coop.get_human_survey_asset``, rather
than an HTTP call written here: edsl already owns the API key, the endpoint and
the access rule, which lets the owner fetch an asset and so anyone who can view
a survey using it.

The image is embedded in the page as a ``data:`` URI, as a scenario's files are,
so a preview stays one file. A fetched asset is also kept in an ``assets``
folder beside the previews, where it can be seen and deleted like the rest of
the output -- and nowhere else on the machine. **Assets are immutable** --
replacing a logo means uploading a new asset with a new uuid -- so a kept one
never goes stale, and a second render into the same directory needs neither the
network nor credentials. Each asset is two files, the image and its metadata,
and the metadata is written last: an entry whose metadata exists is complete,
and one interrupted mid-download is simply fetched again.

Nothing here raises over a logo. A preview that could not fetch one draws the
placeholder and says why; the rest of the survey is not the logo's hostage.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from . import branding

# The formats the asset library accepts, and the suffix each is kept under. An
# asset reporting anything else is not drawn: a preview must not show a logo the
# live page would not.
IMAGE_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}

# The folder, under the output directory, that fetched assets are kept in.
FOLDER = "assets"


def _meta_path(out_dir: Path, uuid: str) -> Path:
    return out_dir / FOLDER / f"{uuid}.json"


def cached(uuid: str, out_dir: Path) -> dict | None:
    """An asset kept in ``out_dir``, as :func:`fetch` returns one, or ``None``."""
    meta = _meta_path(out_dir, uuid)
    try:
        entry = json.loads(meta.read_text(encoding="utf-8"))
        data = meta.with_name(entry["file"]).read_bytes()
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return {**entry, "base64": base64.b64encode(data).decode("ascii")}


def _store(out_dir: Path, uuid: str, asset: dict) -> dict:
    """Download a fetched asset into ``out_dir``; return it as :func:`cached` does."""
    mime = asset.get("mime_type")
    if mime not in IMAGE_TYPES:
        # Returned rather than kept: nothing is written for an asset that will
        # not be drawn, and the caller reports it.
        return {"mime_type": mime}
    meta = _meta_path(out_dir, uuid)
    meta.parent.mkdir(parents=True, exist_ok=True)
    image = meta.with_name(f"{uuid}.{IMAGE_TYPES[mime]}")
    partial = image.with_name(f"{image.name}.part")
    asset.download(str(partial))
    os.replace(partial, image)
    entry = {
        "file": image.name,
        "mime_type": mime,
        "width": asset.get("width"),
        "height": asset.get("height"),
    }
    written = meta.with_name(f"{meta.name}.part")
    written.write_text(json.dumps(entry), encoding="utf-8")
    os.replace(written, meta)
    return cached(uuid, out_dir) or {}


def fetch(
    humanize_schema: dict | None,
    out_dir: Path,
    coop=None,
) -> tuple[dict[str, dict], list[str]]:
    """Fetch every asset the schema names. Returns ``(assets, problems)``.

    ``assets`` maps uuid to ``{"mime_type", "width", "height", "base64"}``,
    which is what :func:`branding.resolve` takes. ``problems`` is a line per
    asset that could not be had, for the caller to print; an asset in it simply
    previews as the placeholder.

    ``out_dir`` is the directory the previews are written to. Fetched assets are
    kept in its ``assets`` folder, and one already there is not fetched again.

    ``coop`` is edsl's client, made on first need so a schema naming nothing --
    or naming only assets already kept -- never constructs one. Passed in by
    tests.
    """
    wanted = [branding.asset_uuid(branding.logo_config(humanize_schema))]
    assets: dict[str, dict] = {}
    problems: list[str] = []
    for uuid in (uuid for uuid in wanted if uuid):
        entry = cached(uuid, out_dir)
        if entry is None:
            try:
                if coop is None:
                    from edsl.coop import Coop

                    coop = Coop()
                entry = _store(out_dir, uuid, coop.get_human_survey_asset(uuid))
            # Anything at all: a missing API key, no access, no network, an
            # asset since deleted. Each is a reason to draw the placeholder, and
            # none is a reason to fail a preview of the rest of the survey.
            except Exception as exc:  # noqa: BLE001
                problems.append(f"could not fetch logo asset {uuid}: {exc}")
                continue
        if entry.get("mime_type") not in IMAGE_TYPES or not entry.get("width"):
            problems.append(
                f"logo asset {uuid} is not an image the survey page would draw "
                f"({entry.get('mime_type')})"
            )
            continue
        assets[uuid] = entry
    return assets, problems
