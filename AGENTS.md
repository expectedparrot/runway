# Runway repository operating contract

Read `README.md` before changing anything under `src/runway/templates/`. The
sections that matter most are **Design constraints** and **The goldens**; the
rules there are the reason the output is trustworthy, and none of them is
obvious from the code alone.

## The one rule

**The markup here is a transcription, not a design.** Class strings, attribute
order and whitespace are copied from the reference web survey's React
components. If a template and a golden disagree, the golden is right and the
template is wrong — never the other way round, and never "fix" a parity test by
loosening its assertion.

Byte equality is the assertion everywhere. Do not normalize, pretty-print, or
tree-compare. If a template has to become uglier to emit exactly what React
emits, make it uglier.

## Development checks

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest -q
```

Commit `uv.lock` whenever you change a dependency — CI syncs with `--locked`
and fails rather than re-resolving, so an unlocked `pyproject.toml` change
breaks the build instead of quietly making CI test something nobody else has.

`pytest` runs against the source tree. `tests/test_packaging.py` is the one
that also means something against a built wheel — run the suite from an
installed wheel when you have changed packaging, since a wheel that ships no
templates still imports cleanly and fails only at render time.

## Goldens

`tests/react_cases.json` and `tests/react_goldens.json` are **generated data**.
Do not hand-edit either one, and do not add a case to the first without the
matching recording in the second — `test_every_case_has_a_golden` will catch
it, but the reason it exists is that an unrecorded case is silently never
compared.

Recording happens in the repository that owns the React components, not here.
A change to those components arrives as a new pair of files; the diff is the
specification for whatever the templates then need.

## Scope

Question types are added one at a time, each with a recorded parity test — see
**Adding a question type** in the README. A type with no renderer is not a bug:
it falls through to a stand-in that renders a complete page with a note in
place of the control, and that is the intended behavior for everything outside
the supported table.

Nothing here calls a model, reaches the network at run time, or needs node —
`edsl` is a declared dependency but rendering does not go through it, and a
preview is still a pure function from a question dict to a string. The single
external reference in a rendered page is the Google Fonts stylesheet link, which
is deliberate and documented under **Known gaps**. Keep it that way: a new
runtime dependency needs a reason in the README.

## Public repository

This is a public repository. Do not add references to private repository
layouts, internal file paths, internal service names, or component filenames
from the reference application. Where the README needs to talk about that
application it does so generically ("the reference implementation", "the live
survey"), and `assets/tailwind.config.cjs` takes its location from
`RUNWAY_REFERENCE_APP` rather than assuming one.
