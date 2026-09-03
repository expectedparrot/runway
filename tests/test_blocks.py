"""Question text split into blocks, and drawn as the reference draws them.

The split is a transcription, so these hold it against the rules it was copied
from rather than against whatever it happens to do: where a block boundary
falls, what is dropped, and what an unresolvable marker becomes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from runway import render_question
from runway.blocks import (
    data_uri,
    file_entries,
    file_type_of,
    prepared,
    text_to_blocks,
)

PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def _a_file(suffix: str = "png", mime: str = "image/png") -> dict:
    return {
        "path": f"x.{suffix}",
        "base64_string": PNG,
        "binary": True,
        "suffix": suffix,
        "mime_type": mime,
        "external_locations": {},
        "extracted_text": None,
    }


# --------------------------------------------------------------------------
# Splitting
# --------------------------------------------------------------------------


def test_text_with_no_marker_produces_no_blocks_at_all():
    """The signal that a question is drawn the way it always was. An empty list
    rather than one text block, because one text block would send every ordinary
    question down the block path and change markup that has goldens on it."""
    assert text_to_blocks("How was your commute?", {}) == []


def test_a_marker_splits_the_text_around_it_in_order():
    files = {"photo": {"file_store_type": "image", "file_load_link": "data:x"}}
    blocks = text_to_blocks("Before <see file photo> after", files)
    assert [b["type"] for b in blocks] == ["text", "file", "text"]
    assert blocks[0]["content"] == "Before"
    assert blocks[2]["content"] == "after"
    assert blocks[1]["filename"] == "photo"
    assert blocks[1]["file_type"] == "image"


def test_surrounding_text_is_stripped_and_dropped_when_empty():
    """A question that is nothing but a marker is one block, not three: the
    reference strips each side and keeps it only if something is left."""
    files = {"photo": {"file_store_type": "image", "file_load_link": "data:x"}}
    assert [b["type"] for b in text_to_blocks("<see file photo>", files)] == ["file"]
    assert [b["type"] for b in text_to_blocks("  <see file photo>  ", files)] == ["file"]


def test_two_markers_running_together_do_not_invent_a_block_between_them():
    files = {
        "a": {"file_store_type": "image", "file_load_link": "data:a"},
        "b": {"file_store_type": "image", "file_load_link": "data:b"},
    }
    blocks = text_to_blocks("<see file a><see file b>", files)
    assert [b["type"] for b in blocks] == ["file", "file"]
    assert [b["filename"] for b in blocks] == ["a", "b"]


def test_a_marker_nothing_resolves_is_still_a_file_block():
    """An author can type one by hand, and a scenario key can be missing. It is
    not an error and it is not left as prose -- it draws as unsupported."""
    blocks = text_to_blocks("See <see file nope> here", {})
    assert [b["type"] for b in blocks] == ["text", "file", "text"]
    assert blocks[1] == {
        "type": "file",
        "filename": "nope",
        "file_type": "",
        "file_load_link": "",
    }


def test_prose_that_merely_contains_angle_brackets_is_not_a_marker():
    for text in ("a < b and c > d", "<see file>", "<see file bad key>", "<seefile x>"):
        assert text_to_blocks(text, {}) == [], text


# --------------------------------------------------------------------------
# Turning a scenario file into something drawable
# --------------------------------------------------------------------------


def test_a_raw_file_becomes_a_data_uri_carrying_its_own_bytes():
    """The stand-in for the link the live page has: a preview is one file with
    nothing behind it, so the bytes have to be in the page."""
    uri = data_uri(_a_file())
    assert uri.startswith("data:image/png;base64,")
    assert uri.endswith(PNG)


def test_a_file_that_already_has_a_link_keeps_it():
    value = {**_a_file(), "file_load_link": "https://example.invalid/signed"}
    assert data_uri(value) == "https://example.invalid/signed"


def test_a_file_with_no_bytes_and_no_link_resolves_to_nothing():
    assert data_uri({"suffix": "png", "mime_type": "image/png"}) == ""


@pytest.mark.parametrize(
    "suffix, expected",
    [
        ("png", "image"), ("jpg", "image"), ("jpeg", "image"), ("gif", "image"),
        ("webp", "image"), ("avif", "image"), ("mp4", "video"), ("mov", "video"),
        ("avi", "video"), ("webm", "video"), ("pdf", "pdf"), ("mp3", "audio"),
        ("wav", "audio"), ("ogg", "audio"), ("m4a", "audio"),
    ],
)
def test_every_suffix_the_reference_classifies_is_classified_the_same_way(
    suffix, expected
):
    assert file_type_of(_a_file(suffix)) == expected


def test_a_suffix_is_matched_regardless_of_case():
    assert file_type_of(_a_file("PNG")) == "image"


def test_only_the_file_keys_of_a_scenario_become_entries():
    scenario = {"city": "Austin", "photo": _a_file(), "counts": [1, 2]}
    entries = file_entries(scenario)
    assert list(entries) == ["photo"]
    assert entries["photo"]["file_store_type"] == "image"


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------


def _drawn(blocks: list[dict]) -> str:
    return render_question(
        {
            "question_name": "q",
            "question_type": "free_text",
            "edsl_class_name": "QuestionFreeText",
            "question_text": "unused",
            "question_text_blocks": blocks,
        }
    )


def test_an_image_block_draws_the_reference_img():
    html = _drawn(
        [{"type": "file", "filename": "p", "file_type": "image", "file_load_link": "data:image/png;base64,AA"}]
    )
    assert '<img class="edsl-question-image mb-3" src="data:image/png;base64,AA" alt="Image">' in html


def test_a_video_block_draws_a_video_with_controls():
    html = _drawn(
        [{"type": "file", "filename": "v", "file_type": "video", "file_load_link": "data:video/mp4;base64,AA"}]
    )
    assert '<video controls class="max-w-full h-auto" src="data:video/mp4;base64,AA">' in html
    assert "Your browser does not support this video." in html


def test_a_pdf_block_draws_an_object():
    html = _drawn(
        [{"type": "file", "filename": "d", "file_type": "pdf", "file_load_link": "data:application/pdf;base64,AA"}]
    )
    assert 'type="application/pdf"' in html
    assert "Your browser does not support PDF viewing." in html


def test_an_audio_block_says_the_reference_says_it_is_unsupported():
    """Audio is classified and then not drawn, in the reference and so here."""
    html = _drawn(
        [{"type": "file", "filename": "a", "file_type": "audio", "file_load_link": "data:audio/mp3;base64,AA"}]
    )
    assert "Unsupported file type" in html


def test_a_text_block_is_rendered_as_markdown_like_any_question_text():
    html = _drawn([{"type": "text", "content": "**bold** words"}])
    assert "<strong>bold</strong> words" in html
    assert '<div class="edsl-question-text text-xl mb-3 whitespace-pre-wrap">' in html


def test_a_data_uri_is_not_mangled_by_escaping():
    """A base64 payload contains `+` and `/` and can end in `=`; an escaping bug
    here would produce a page whose images silently do not load."""
    uri = f"data:image/png;base64,{PNG}"
    html = _drawn([{"type": "file", "filename": "p", "file_type": "image", "file_load_link": uri}])
    assert f'src="{uri}"' in html


def test_prepared_leaves_a_file_block_alone_and_renders_only_text():
    file_block = {"type": "file", "filename": "p", "file_type": "image", "file_load_link": "data:x"}
    out = prepared([{"type": "text", "content": "hi"}, file_block])
    assert out[1] == file_block
    assert "content_html" in out[0] and "content_html" not in out[1]


# --------------------------------------------------------------------------
# End to end, over the committed example
# --------------------------------------------------------------------------


def test_the_image_example_draws_its_swatch_rather_than_a_marker():
    """The whole point, held against the example a reader will actually open."""
    from runway import scenarios as scenarios_module
    from runway.survey import load

    examples = Path(__file__).resolve().parent.parent / "examples"
    questions = load(examples / "image_scenario_survey.json")
    scenario = scenarios_module.load(examples / "scenarios" / "image_scenario_survey.json")[0]

    piped = scenarios_module.pipe(questions, scenario)
    reaction = next(q for q in piped if q["question_name"] == "reaction")
    assert [b["type"] for b in reaction["question_text_blocks"]] == ["text", "file", "text"]

    html = render_question(reaction)
    assert 'class="edsl-question-image mb-3"' in html
    assert "see file swatch" not in html
    assert re.search(r'src="data:image/png;base64,[A-Za-z0-9+/=]+"', html)
