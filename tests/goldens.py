"""The recorded reference markup the parity tests compare against.

The markup in ``react_goldens.json`` is not written by hand. It is
``renderToStaticMarkup`` output captured from the reference web survey's own
React components, one entry per case in ``react_cases.json``. Both files are
committed data, and these tests read nothing else -- which is the point: the
contract has to be checkable with Python alone, on any checkout, with no
node and no copy of the reference application.

Re-recording lives with the reference implementation, not here; see
``README.md`` under "The goldens". A recording that no longer matches this
package shows up as a failing parity test after the new file lands.

The two files are a matched pair, and :func:`check_pairing` is what says so --
a case with no golden is a case that would silently never be compared.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE / "react_cases.json"
GOLDENS = HERE / "react_goldens.json"

# A literal owned by the recording harness: the shell case is recorded with
# this string standing in for the question, so the markup before and after a
# question can be checked without the recording knowing what a question looks
# like. It spells the old name of this package because that is what is in the
# recorded file; changing it here would simply stop matching.
CONTENT_MARKER = "__SURVEY_PREVIEW_CONTENT__"


def load_cases() -> dict[str, dict]:
    """What was rendered: question dicts, progress payloads, keyed by name."""
    return json.loads(CASES.read_text(encoding="utf-8"))


def load_goldens() -> dict[str, str]:
    """What came out: the recorded markup, keyed by the same names."""
    return json.loads(GOLDENS.read_text(encoding="utf-8"))


def check_pairing() -> None:
    """Raise unless every case has a golden and every golden has a case."""
    cases, goldens = load_cases(), load_goldens()
    unrecorded = sorted(set(cases) - set(goldens))
    orphaned = sorted(set(goldens) - set(cases))
    assert not unrecorded, f"case with no recorded golden: {unrecorded}"
    assert not orphaned, f"golden with no case: {orphaned}"
