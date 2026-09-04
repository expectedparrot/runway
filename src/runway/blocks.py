"""Question text split into text and file blocks, the way the live page splits it.

A question whose text names a file is not rendered as one string. The reference
splits it on each ``<see file KEY>`` marker into an ordered list of blocks --
text, file, text -- and draws each: markdown for a text block, an ``<img>`` for
an image, a ``<video>`` for a video, an ``<object>`` for a PDF. So a scenario
holding an image is not decoration on the question; it is *part of* the question
a respondent reads, and a preview that showed the marker instead would be
showing a page nobody is served.

**Where the reference has a link, this has the bytes.** The live page uploads a
file, signs a URL and puts that in the block. Nothing here uploads anything, and
there is no server to sign against -- but a scenario list carries each file
inline, base64 already, because that is how a ``FileStore`` serializes. So the
block is built with a ``data:`` URI in place of the link. Same markup, same
splitting, same order; only the source of the bytes differs, and it has to,
because a preview is one file with nothing behind it.

That is also the one thing to know about size. A preview of a scenario list
carrying large media inlines all of it, so the page is as big as the files are.
A survey of small images costs nothing; twenty scenarios of video is a very
large file.

An **audio** file previews as "Unsupported file type", which is not an omission
here: the reference's own block renderer draws images, video and PDFs and says
exactly that for everything else.
"""

from __future__ import annotations

import re

# Which control draws a file, chosen by its extension. Transcribed from the
# reference's own table, including that audio is classified and then not drawn --
# see the module docstring.
FILE_TYPE_BY_SUFFIX = {
    "mp4": "video",
    "mov": "video",
    "avi": "video",
    "webm": "video",
    "pdf": "pdf",
    "png": "image",
    "jpg": "image",
    "jpeg": "image",
    "gif": "image",
    "webp": "image",
    "avif": "image",
    "mp3": "audio",
    "wav": "audio",
    "ogg": "audio",
    "m4a": "audio",
}

# A file reference in question text. The key is matched narrowly -- letters,
# digits, underscore, dot, hyphen -- so that prose containing an angle bracket
# is not mistaken for a marker.
_FILE_REFERENCE = re.compile(r"<see file ([a-zA-Z0-9_.-]+)>")

# What a marker is worth when nothing resolves it: no type and no source, which
# draws as the reference's "Unsupported file type". An author can type
# `<see file x>` by hand, and a scenario key can simply be missing.
_UNRESOLVED = {"file_store_type": "", "file_load_link": ""}

# A file whose bytes were moved out of the scenario and left a receipt behind:
# `base64_string` says so literally. The live survey fetches it back; nothing here
# can, so the file resolves to no source and draws as the reference draws a file
# it cannot show. Taking the word for base64 would emit `src="data:...,offloaded"`
# -- a broken image on every page, which is worse than saying so.
OFFLOADED = "offloaded"


def data_uri(value: dict) -> str:
    """A file's bytes as a ``data:`` URI, or ``""`` if it carries none.

    The stand-in for the signed URL the live page has and this does not. A file
    that has already been resolved elsewhere brings its own link, which is used
    as it stands rather than rebuilt from bytes it no longer carries.
    """
    existing = value.get("file_load_link")
    if isinstance(existing, str) and existing:
        return existing
    encoded = value.get("base64_string")
    if not isinstance(encoded, str) or not encoded or encoded == OFFLOADED:
        return ""
    mime = value.get("mime_type")
    if not isinstance(mime, str) or not mime:
        mime = "application/octet-stream"
    return f"data:{mime};base64,{encoded}"


def file_type_of(value: dict) -> str:
    """Which of the reference's four branches draws this file.

    A resolved file states its type outright. A raw one states only its suffix,
    so the suffix is what it is looked up by -- the same lookup the live page
    does when it resolves a file in the first place.
    """
    stated = value.get("file_store_type")
    if isinstance(stated, str) and stated:
        return stated
    suffix = value.get("suffix")
    if not isinstance(suffix, str):
        return ""
    return FILE_TYPE_BY_SUFFIX.get(suffix.lower(), suffix.lower())


def file_entries(scenario: dict) -> dict[str, dict]:
    """The drawable form of each file in a scenario, by key.

    What the marker in the question text is looked up against. Keys that are not
    files are left out entirely, so a marker naming one resolves to nothing and
    draws as unsupported -- which is what it is.
    """
    from .scenarios import _is_file_value

    return {
        key: {
            "file_store_type": file_type_of(value),
            "file_load_link": data_uri(value),
        }
        for key, value in scenario.items()
        if _is_file_value(value)
    }


def text_to_blocks(text: str, files: dict[str, dict]) -> list[dict]:
    """Question text as an ordered list of text and file blocks.

    Transcribed from the reference, whose details are all load-bearing:

    * text between markers is **stripped**, and dropped entirely when that
      leaves it empty -- so a question that is nothing but a marker produces one
      block, not three;
    * a marker naming something that is not a file still produces a **file
      block**, with no type and no source. It is not left as text and it is not
      an error: an author may type one by hand, and it draws as unsupported;
    * order is the order of appearance, which is the whole point -- text before
      an image and text after it are different blocks of the same question.

    Returns an empty list for text with no markers in it, which is the signal to
    draw the question the way it was drawn before any of this existed.
    """
    if not text or not _FILE_REFERENCE.search(text):
        return []

    blocks: list[dict] = []
    last_end = 0
    for match in _FILE_REFERENCE.finditer(text):
        if match.start() > last_end:
            before = text[last_end : match.start()].strip()
            if before:
                blocks.append({"type": "text", "content": before})
        key = match.group(1)
        entry = files.get(key)
        if not isinstance(entry, dict):
            entry = _UNRESOLVED
        blocks.append(
            {
                "type": "file",
                "filename": key,
                "file_type": entry.get("file_store_type") or "",
                "file_load_link": entry.get("file_load_link") or "",
            }
        )
        last_end = match.end()
    if last_end < len(text):
        after = text[last_end:].strip()
        if after:
            blocks.append({"type": "text", "content": after})
    return blocks


def _prepare(blocks: object, render) -> list[dict]:
    from markupsafe import Markup

    if not isinstance(blocks, list):
        return []
    return [
        {**block, "content_html": Markup(render(block.get("content", "")))}
        if block.get("type") == "text"
        else block
        for block in blocks
        if isinstance(block, dict)
    ]


def prepared(blocks: object) -> list[dict]:
    """Question-text blocks, with each text block's markdown rendered.

    The markdown pass is the one a question with no blocks goes through, so a
    text block and a whole question text draw identically -- splitting a
    question around an image must not change how its words are rendered.
    """
    from .markdown import render_question_text

    return _prepare(blocks, render_question_text)


def prepared_option(blocks: object) -> list[dict]:
    """Option-label blocks, rendered as option text rather than question text.

    A different markdown pass, because an option label renders *inside* the
    label wrapping a radio, which admits phrasing content only -- a paragraph
    becomes a span there. Running question-text markdown over an option's words
    would drop a block element into a label, putting a one-line label below its
    input instead of beside it.
    """
    from .markdown import render_option_text

    return _prepare(blocks, render_option_text)


def options_to_blocks(options: object, files: dict[str, dict]) -> list[list[dict]] | None:
    """Per-option blocks, one entry per option, in the order given.

    The option-level counterpart of :func:`text_to_blocks`: an author who writes
    ``{{ scenario.dog }}`` as an option gets the image in that option's label,
    exactly as they would in the question text.

    **Positional**, so it has to be built from the option order actually being
    drawn -- pair a label with another option's image and a respondent clicks
    one picture and answers with a different one.

    ``None`` -- not an empty list -- when no option references a file, which is
    every survey that does not use image options. Those draw the option strings
    they already have, so the page carries no second copy of every label. A
    non-string option (a linear scale's numbers) gets an empty list and falls
    back the same way, and options still sitting as an unresolved template
    *string* are refused outright: a string is iterable, and scanning one would
    hand back a block per character.
    """
    if not isinstance(options, list):
        return None
    per_option = [
        text_to_blocks(option, files) if isinstance(option, str) else []
        for option in options
    ]
    if not any(block["type"] == "file" for blocks in per_option for block in blocks):
        return None
    return per_option
