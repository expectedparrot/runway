"""Tests for the branding banner: the markup, the block behind it, the fetch.

Three halves, because there are three ways to get this wrong. The markup is
recorded from the reference component into ``react_goldens.json`` and compared
byte for byte here. The block -- what a schema's logo resolves to, fetched or
not -- is decided by ``branding.resolve``, and those tests assert on the block
rather than on HTML, since that is where the decision is. And the fetch goes to
Coop, so its tests stand a fake client in for edsl's and check what reaches the
cache and what does not.

Runs under pytest, or directly:
    python tests/test_branding.py
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import tempfile
from pathlib import Path

import goldens
from runway import assets, branding, render_bundle, render_survey
from runway.cli import main
from runway.renderer import render_banner, render_page

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

BANNER_CASES = sorted(k for k, v in CASES.items() if v["kind"] == "banner")

UUID = "6f1c2a4e-9b7d-4c1e-8a2f-3d5e6f7a8b9c"

# A 1x1 transparent PNG: real bytes, so a data URI built from them is one a
# browser would draw.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)

QUESTION = {
    "question_name": "q",
    "question_text": "Which?",
    "question_type": "multiple_choice",
    "question_options": ["A", "B"],
}


def schema(**logo) -> dict:
    """A schema naming a logo, with the given fields over a default one."""
    return {
        "survey": {
            "branding": {
                "logo": {
                    "source": {"type": "asset", "asset_uuid": UUID},
                    "alt": "Lab name",
                    **logo,
                }
            }
        }
    }


FETCHED = {UUID: {"mime_type": "image/png", "width": 640, "height": 160, "base64": "QUJD"}}


# --------------------------------------------------------------------------
# markup
# --------------------------------------------------------------------------


def test_banner_cases_are_recorded():
    # Every position, a decorative logo, and both ways of having none.
    assert len(BANNER_CASES) == 6


def test_every_recorded_banner_matches_react():
    for name in BANNER_CASES:
        assert render_banner(CASES[name]["branding"]) == GOLDENS[name], name


def test_no_logo_draws_no_banner_at_all():
    # Not an empty banner: the reference returns nothing, and so does this.
    assert render_banner(None) == ""
    assert render_banner({"logo": None}) == ""


def test_the_banner_is_the_first_thing_on_the_page():
    html = render_page(QUESTION, branding=branding.resolve(schema()))
    container = html.index("edsl-survey-container")
    assert container < html.index("edsl-survey-banner") < html.index("<form")


def test_a_page_without_branding_is_unchanged():
    assert render_page(QUESTION) == render_page(QUESTION, branding=None)
    assert "edsl-survey-banner" not in render_page(QUESTION)


# --------------------------------------------------------------------------
# the resolved block
# --------------------------------------------------------------------------


def test_no_logo_resolves_to_no_block():
    for none in (None, {}, {"survey": {}}, {"survey": {"branding": None}},
                 {"survey": {"branding": {"logo": None}}}):
        assert branding.resolve(none) is None, none


def test_an_unfetched_logo_is_the_placeholder_with_the_authors_text():
    logo = branding.resolve(schema(position="center"))["logo"]
    assert logo == {
        "url": branding.LOGO_PLACEHOLDER,
        "alt": "Lab name",
        "width": branding.PLACEHOLDER_WIDTH,
        "height": branding.PLACEHOLDER_HEIGHT,
        "position": "center",
    }


def test_a_fetched_logo_is_embedded_at_its_own_size():
    logo = branding.resolve(schema(), FETCHED)["logo"]
    assert logo["url"] == "data:image/png;base64,QUJD"
    assert (logo["width"], logo["height"]) == (640, 160)


def test_an_asset_fetched_for_another_logo_is_not_used():
    other = {"a" * 8 + "-0000-4000-8000-" + "0" * 12: FETCHED[UUID]}
    assert branding.resolve(schema(), other)["logo"]["url"] == branding.LOGO_PLACEHOLDER


def test_position_and_alt_fall_back_the_way_the_reference_does():
    logo = branding.resolve(schema(position="top", alt="  Lab  "))["logo"]
    assert logo["position"] == "left"
    assert logo["alt"] == "Lab"
    assert branding.resolve(schema(alt=""))["logo"]["alt"] == ""


def test_only_an_asset_uuid_is_an_asset():
    assert branding.asset_uuid(schema()["survey"]["branding"]["logo"]) == UUID
    assert branding.asset_uuid({"source": {"type": "scenario", "key": "logo"}}) is None
    # Named a cache file, so it has to be a uuid and nothing that spells a path.
    assert branding.asset_uuid({"source": {"type": "asset", "asset_uuid": "../x"}}) is None
    assert branding.asset_uuid({"source": {"asset_uuid": UUID.upper()}}) == UUID


def test_every_page_of_a_bundle_carries_the_banner():
    questions = [dict(QUESTION, question_name=name) for name in ("a", "b", "c")]
    html = render_bundle(questions, schema(), assets=FETCHED)
    assert html.count("edsl-survey-banner-content") == 3
    assert "data:image/png;base64,QUJD" in html


def test_every_split_page_carries_the_banner():
    questions = [dict(QUESTION, question_name=name) for name in ("a", "b")]
    with tempfile.TemporaryDirectory() as tmp:
        written = render_survey(questions, schema(), Path(tmp), split=True)
        assert len(written) == 2
        for path in written:
            assert branding.LOGO_PLACEHOLDER in path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------


class FakeAsset(dict):
    """What ``Coop.get_human_survey_asset`` returns: metadata, and a download."""

    def download(self, path):
        Path(path).write_bytes(PNG)
        return path


class FakeCoop:
    def __init__(self, fail: Exception | None = None, mime: str = "image/png"):
        self.calls: list[str] = []
        self.fail = fail
        self.mime = mime

    def get_human_survey_asset(self, uuid):
        self.calls.append(uuid)
        if self.fail:
            raise self.fail
        return FakeAsset(uuid=uuid, mime_type=self.mime, width=640, height=160)


def test_a_fetched_asset_is_cached_and_not_fetched_again():
    with tempfile.TemporaryDirectory() as tmp:
        coop = FakeCoop()
        fetched, problems = assets.fetch(schema(), Path(tmp), coop)
        assert problems == []
        # Beside the previews, under a name that says what it is.
        assert (Path(tmp) / "assets" / f"{UUID}.png").read_bytes() == PNG
        assert fetched[UUID]["base64"] == base64.b64encode(PNG).decode("ascii")
        assert (fetched[UUID]["width"], fetched[UUID]["height"]) == (640, 160)
        again, _ = assets.fetch(schema(), Path(tmp), coop)
        assert again == fetched
        assert coop.calls == [UUID]


def test_a_failed_fetch_is_a_problem_not_an_error():
    with tempfile.TemporaryDirectory() as tmp:
        fetched, problems = assets.fetch(
            schema(), Path(tmp), FakeCoop(fail=RuntimeError("no API key"))
        )
        assert fetched == {}
        assert len(problems) == 1 and "no API key" in problems[0]
        # Nothing half-written is left to be mistaken for a cached asset.
        assert assets.cached(UUID, Path(tmp)) is None


def test_an_asset_that_is_not_a_logo_image_is_not_drawn():
    with tempfile.TemporaryDirectory() as tmp:
        fetched, problems = assets.fetch(
            schema(), Path(tmp), FakeCoop(mime="image/svg+xml")
        )
        assert fetched == {}
        assert "image/svg+xml" in problems[0]
        # Nothing is kept for an asset that will not be drawn.
        assert not (Path(tmp) / "assets").exists()


def test_a_schema_with_no_logo_fetches_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        coop = FakeCoop()
        assert assets.fetch({}, Path(tmp), coop) == ({}, [])
        assert coop.calls == []


# --------------------------------------------------------------------------
# the command line
# --------------------------------------------------------------------------


def keep_the_logo(out_dir: Path) -> None:
    """Put the logo in ``out_dir`` as a fetch would have left it."""
    folder = out_dir / assets.FOLDER
    folder.mkdir(parents=True)
    (folder / f"{UUID}.png").write_bytes(PNG)
    entry = {"file": f"{UUID}.png", "mime_type": "image/png", "width": 640, "height": 160}
    (folder / f"{UUID}.json").write_text(json.dumps(entry), encoding="utf-8")


def _survey_and_schema(tmp: Path) -> tuple[Path, Path]:
    from test_cli import _survey_dict

    schema_path = tmp / "schema.json"
    schema_path.write_text(json.dumps(schema()), encoding="utf-8")
    return _survey_dict(tmp), schema_path


def test_render_draws_the_placeholder_unless_asked_to_fetch():
    embedded = "data:image/png;base64," + base64.b64encode(PNG).decode("ascii")
    with tempfile.TemporaryDirectory() as tmp:
        survey, schema_path = _survey_and_schema(Path(tmp))
        plain, fetched = Path(tmp) / "plain", Path(tmp) / "fetched"
        # Both already hold the logo, so neither render needs Coop -- and the
        # plain one still does not use it: without the flag the output depends
        # on the inputs alone, not on what a directory happens to hold.
        keep_the_logo(plain)
        keep_the_logo(fetched)
        main(["render", str(survey), "--schema", str(schema_path), "-o", str(plain)])
        main(["render", str(survey), "--schema", str(schema_path), "-o", str(fetched),
              "--fetch-assets"])
        plain_html = next(plain.glob("*.html")).read_text(encoding="utf-8")
        fetched_html = next(fetched.glob("*.html")).read_text(encoding="utf-8")
        assert branding.LOGO_PLACEHOLDER in plain_html
        assert embedded not in plain_html
        assert embedded in fetched_html


def test_check_says_which_logo_a_preview_stands_in_for():
    with tempfile.TemporaryDirectory() as tmp:
        survey, schema_path = _survey_and_schema(Path(tmp))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main(["check", str(survey), "--schema", str(schema_path), "--json"])
        notes = json.loads(buffer.getvalue())["surveys"][0]["notes"]
        assert any(UUID in note and "--fetch-assets" in note for note in notes)


def _main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc or '(assertion failed)'}")
        else:
            print(f"ok   {name}")
    print("\n" + ("all passed" if not failures else f"{failures} failure(s)"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
