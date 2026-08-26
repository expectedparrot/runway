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

The single exception is `assets/base.css`, which carries one hand-written rule
for the selected state of a stacked matrix option — state the reference
expresses by swapping classes on re-render, which a static page cannot do. It is
CSS, not markup, so parity is untouched. Anything else that wants to be
hand-written should be a recorded case instead; read that file's comment first,
including why `:where()` is load-bearing there.

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

## The command line

Five commands, argparse, no CLI dependency: `render`, `check`, `types`,
`guide`, `version`. A verb is always required. `render` writes into `./previews`
unless `-o` says otherwise — relative to the caller's directory, not to this
repository.

`check` classifies without rendering, and `inspection.classify` must keep
mirroring `renderer.render_question`'s dispatch order — background questions
are tested for *before* the type registry, because a thinking-wrapped
`multiple_choice` is still `multiple_choice` and the registry would happily
promise a radio list for a page nobody is served.
`test_check_agrees_with_what_render_produces` renders every example and holds
the two to each other, so adding a renderer without updating the classifier
fails there rather than in someone's report.

A renderer that draws only *some* of what its type can be configured as says so
through `question_types.DECLINES` rather than by rendering the wrong thing —
`matrix` declines the carousel format. Both `render_question` and `classify` ask
`declined()` before the registry, which is what keeps them from disagreeing; a
new partial renderer belongs there rather than in either caller.

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
