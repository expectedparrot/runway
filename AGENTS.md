# Runway repository operating contract

Read `SPEC.md` before changing anything under `src/runway/templates/`. The
sections that matter most are **Design constraints** and **The goldens**; the
rules there are the reason the output is trustworthy, and none of them is
obvious from the code alone. `README.md` is the user-facing half: what runway
is, how to run it, and which question types it draws.

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

## Examples

`examples/*.json` and `examples/schemas/*.json` are **generated** from
`examples/src/*.py`, where each module builds a `Survey` and names a
`humanize_schema` when the survey needs one. Edit the source, then:

```bash
uv run python examples/build.py            # rewrite the JSON
uv run python examples/build.py --render   # and the previews, via the CLI
```

Do not hand-edit the JSON — the next build reverts it. CI runs
`build.py --check`, which fails if anything no longer matches its source,
including a schema left behind by a survey that stopped needing one.

`examples/src` is on the import path while a source is loaded, so one example
may import another's `survey` rather than restating it — which is how a pair
that differs only in its schema is built, and why the two cannot drift apart.
The importing example's JSON is then a byte-identical twin, which is the point:
two identical surveys, one schema between them, so a preview pair shows what
`custom_css` did and nothing else.

The survey file is `Survey.to_dict()` **verbatim**, so it carries `edsl_version`
and an edsl upgrade will show up here as a diff. That is deliberate: an example
that differed from what `to_dict()` writes would be demonstrating a format
nobody produces.

The output is committed all the same, because the tests read it: a suite that
built its own fixtures would need edsl working to tell you anything at all,
including that edsl had broken something.

Read examples through `tests/examples.py`, never `load()` directly. The schema
is a separate file now, and a test that forgot it would leave the cases that
only exist *because* of a schema — the carousel note, a dropdown, an exclusive
option — green and unexercised.

`mixed_survey` is the one to leave alone. Several survey-level tests assert
progress values that follow from it having exactly seven items.

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

A survey file is anything edsl saves: `.ep`, `.json.gz` or `.json`. **All three
go through `Survey.load()`**, flattened with `to_dict()` — do not add a reader
here that parses survey JSON itself. A survey does not survive JSON unchanged
(integer `option_labels` keys come back as strings), so a second reader would
drift from edsl's and make one format preview differently from another;
`tests/test_formats.py` holds the three to byte-identical output.

`survey.load` returns questions and nothing else. **A humanize schema is not
part of an EDSL survey** — edsl neither writes one nor reads one — so it is not
something a survey file can carry in any format, and a `humanize_schema` key
written into a survey document is ignored rather than honoured. `load_schema`
and `--schema` are the only route. Do not add an inline form back: it would be a
runway-only extension to a format runway does not own.

Survey JSON is parsed here in exactly one place, `survey._json_document`, and
only to explain a *failure* — never on the path that succeeds. It turns edsl's
`ValueError` about sequence lengths into "this is a bare list of question dicts"
and its bare `KeyError` into "this has no memory_plan". Keep it on the error
path; the moment it reads something the happy path depends on, the two readers
can drift.

Two things a survey file may no longer be, both deliberate: a bare list of
question dicts (edsl cannot build a `Survey` from one) and a document that stubs
`memory_plan` or `rule_collection`. Test fixtures build real surveys with edsl
rather than approximating a dump — see `tests/test_cli.py::_survey_dict`.

Everything downstream still takes a list of question dicts; nothing but
`survey.load` knows about formats.

Import `Survey` from `edsl.surveys`, not from the `edsl` top level.

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
**Adding a question type** in SPEC.md. A type with no renderer is not a bug:
it falls through to a stand-in that renders a complete page with a note in
place of the control, and that is the intended behavior for everything outside
the supported table.

Nothing here calls a model or needs node, and **rendering** does not go through
`edsl` — a preview is still a pure function from a question dict to a string.
Reading a survey does go through edsl, in every format, and the import is kept
lazy in `survey._load_questions` so that `types`, `version`, `guide` and every
library call starting from a question dict do not pay for it.

Reading a `.ep` is the one exception to run-time isolation: it shells out to
`git`, and, for a package Coop holds, syncs it against the remote and rewrites
the file. That is edsl's `load()` semantics rather than a choice made here; it is
documented in the README under Known gaps.

The single external reference in a rendered page is the Google Fonts stylesheet
link, which is deliberate and documented under **Known gaps**. Keep it that way:
a new runtime dependency needs a reason in the README.

## Public repository

This is a public repository. Do not add references to private repository
layouts, internal file paths, internal service names, or component filenames
from the reference application. Where the README needs to talk about that
application it does so generically ("the reference implementation", "the live
survey"), and `assets/tailwind.config.cjs` takes its location from
`RUNWAY_REFERENCE_APP` rather than assuming one.
