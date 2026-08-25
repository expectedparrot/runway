# Runway

Static HTML previews of EDSL human-survey questions.

Runway takes the question dict that `edsl`'s `question.to_dict()` produces and
writes a self-contained HTML page that looks like the live web survey a
respondent would see — same markup, same stylesheet, same font. No browser, no
node, no server: a dict in, a file out.

**Scope today: the choice family — `multiple_choice`, `likert_five`, `yes_no`
and `linear_scale`.** Every other question type renders a "No preview is
available" notice. That is deliberate: the fidelity bar here is byte-for-byte
agreement with the live survey's own components, so types are added one at a
time, each with a recorded parity test.

## Install

```bash
git clone https://github.com/expectedparrot/runway.git
cd runway
uv sync
uv run runway examples/mixed_survey.json
```

Or install it as a tool, so `runway` is on your PATH anywhere:

```bash
uv tool install git+https://github.com/expectedparrot/runway.git
```

To work on it, `uv sync --extra dev` adds pytest and ruff. `pip install -e
".[dev]"` works too, and resolves fresh rather than from `uv.lock`.

Python 3.10+ and three runtime dependencies: **Jinja2** (which brings
MarkupSafe), **`markdown-it-py[linkify]`** for question and option text — see
[Markdown](#markdown) — and **`edsl`** itself. The `linkify` extra is not
optional: the `gfm-like` preset raises `ModuleNotFoundError` without it rather
than quietly leaving bare URLs unlinked.

**`edsl` is tracked from git `main`, not from a release**, which has two
consequences worth knowing before you install. Installing needs git and network
access, so this is not a package you can vendor into an air-gapped build. And a
direct URL reference in the dependency list is something PyPI rejects outright,
so runway is installable from a checkout or a git URL but cannot be published to
PyPI while that line stands. `uv.lock` pins the exact commit, so a locked
install is still reproducible.

## Usage

```bash
runway examples/mixed_survey.json            # -> outputs/mixed_survey.html
runway examples/mixed_survey.json --split    # -> one file per question
runway examples/*.json                       # -> one .html per survey
runway examples/*.json -o build/previews     # -> somewhere else
```

`python -m runway` is the same entry point if you would rather not rely on the
script being on `PATH`.

Each survey is written under its own file name, so several can be rendered into
one output directory and sit side by side. The library call keeps its own
default of `index.html` unless you pass `name=`.

By default the whole survey lands in **one HTML file**: every question rendered
into its own copy of the survey page, one shown at a time, with a toolbar
across the top to jump between them (arrows, a dropdown, and left/right arrow
keys). Bundling is both more convenient and smaller — the stylesheet is most of
a page's weight and a bundle inlines it once:


| survey       | `--split` | bundled |
| ------------ | --------- | ------- |
| 2 questions  | ~103 KB   | ~58 KB  |
| 20 questions | ~1.0 MB   | ~90 KB  |


`--split` writes `<survey>-01-<question>.html`, `<survey>-02-<question>.html`, …
instead. Useful for handing someone a single question; each file carries its own
stylesheet copy.

Questions with no control here still get a full page — same shell, same progress
indicator, and **their question text rendered in the usual markup** — with a note
or a warning standing in for the input. So a mixed survey previews end to end,
and you can still read and check the wording of a question whose control isn't
built yet. The exception is questions whose text a respondent never sees — an
`interview`'s, which instructs the interviewer rather than the respondent, and
every automatic question's, which is a prompt for a model or an expression for
the server: there the text is suppressed, since showing it would imply the
survey displays something it doesn't.

As a library:

```python
from runway import render_bundle, render_page, render_survey

html  = render_bundle(questions, humanize_schema)                # one document
html  = render_page(question, {"format": {"type": "dropdown"}})  # one question
paths = render_survey(questions, humanize_schema, out_dir="outputs", split=False)
paths = render_survey(questions, humanize_schema, name="my_survey")   # -> my_survey.html
```

## Question types

These are the types a human survey can be configured for, and where each one
stands here. A type still awaiting a preview gets a note in place of its
control; the rest of its page is complete, so its wording and position in the
survey can be checked meanwhile.


| question type         | preview         |     | question type                | preview         |
| --------------------- | --------------- | --- | ---------------------------- | --------------- |
| `budget`              | — not yet       |     | `linear_scale`               | **✅ available** |
| `checkbox`            | — not yet       |     | `list`                       | — not yet       |
| `checkbox_with_other` | — not yet       |     | `matrix`                     | — not yet       |
| `compute`             | **✅ automatic** |     | `multiple_choice`            | **✅ available** |
| `file_upload`         | — not yet       |     | `multiple_choice_with_other` | — not yet       |
| `free_text`           | — not yet       |     | `numerical`                  | — not yet       |
| `image_generation`    | **✅ automatic** |     | `rank`                       | — not yet       |
| `interview`           | — not yet       |     | `top_k`                      | — not yet       |
| `likert_five`         | **✅ available** |     | `yes_no`                     | **✅ available** |


A type **outside** this table — `dict`, for instance — is a different matter. It
has no rendering for a human respondent anywhere, so no preview could exist and
nothing here will make one appear. Those pages carry a warning rather than a
note, because what needs changing is the survey rather than this package.

### Questions answered without a respondent

`compute` and `image_generation` are marked *automatic* above because nobody is
ever asked them: the survey evaluates the one and sends the other to an image
model between pages, then advances past both. The same is true of a question of
**any** type wrapped by `thinking_question()`, which answers it with its own
model and system prompt. All three are run by the survey navigator, and their
pages carry a third notice saying so — neither "no preview yet" nor "not
supported", since nothing is missing and nothing is wrong.

The thinking wrapper is the one to watch: it leaves the question's type alone,
so a wrapped `multiple_choice` is still `multiple_choice` and would otherwise be
drawn with a radio list for a page no respondent is ever served. It is detected
on the question rather than its type (the `thinking_model` key `to_dict()`
leaves behind) and intercepted ahead of the type registry. The toolbar marks
these pages *(automatic)* too, since the type alone cannot tell them apart from
the questions that are shown. `examples/background_survey.json` has all three
kinds next to shown questions of the same types.

## Input format

Either a bare list of question dicts, or:

```json
{
  "questions": [ { "question_name": "...", "question_type": "...", ... } ],
  "humanize_schema": {
    "questions": { "question_name": { "format": {"type": "dropdown"} } },
    "survey":    { "custom_css": ".edsl-question-text { font-size: 1.4rem }" }
  }
}
```

`humanize_schema` is the same structure you would pass to `Survey.humanize()`,
so a schema written for a real deployment works here unchanged. `custom_css` is
emitted last in the page so it wins, exactly as the live survey applies it —
`examples/styled_survey.json` is a survey that uses it, against the `edsl-`
hooks the markup carries for exactly this.

## The toolbar

Preview chrome, not survey chrome — every class on it is a Tailwind utility or
a `preview-` hook, never `edsl-`, so a survey's custom CSS cannot style it by
accident. Its essential layout is also re-asserted *after* the custom CSS, so a
stylesheet with broad selectors can't leave the preview unnavigable.

The survey's own **Next button stays inert**. It is part of the page being
previewed, so it is rendered exactly as a respondent would see it; navigation
lives in the toolbar instead.

Panels use `display: contents` when active, so the wrapper drops out of layout
and the survey shell's full-height flex chain still resolves. Without
JavaScript the first panel stays visible and the rest stay hidden, so the
document degrades to "the first question" rather than to every question at
once.

## The progress indicator

`humanize_schema["survey"]["progress"]` selects one of three renderings, and the
preview draws whichever the survey is configured for. Absent means the bar, so a
survey written before the setting existed previews as it renders.

```json
{"type": "bar", "label": {"type": "percent"}}
{"type": "bar", "label": null}
{"type": "hidden"}
{"type": "steps", "marker": "number",
 "steps": [{"label": "About you",    "complete_after": "age"},
           {"label": "Your commute", "complete_after": null}]}
```

A step is a *boundary*, not a bucket: it covers every survey item through
`complete_after`, and the last step runs to the end. The two readings measure the
same position from opposite ends — the bar says how much is **done**, so page one
reads 0%, while the stepper says where the respondent **is**, so page one already
sits on step one. A step naming an item the survey no longer has is dropped, and
if fewer than two survive the indicator falls back to the bar, exactly as the
live survey resolves it.

## Markdown

Question text and option text are both markdown on the live page, so both are
markdown here. An author writing `**Strongly** agree` sees emphasis, not
asterisks.

The parse is the easy half: `markdown-it-py` and `remark` are both CommonMark
implementations and agree on the tree. What differs is the serialization —
`react-markdown` hands its tree to React, so what reaches the page is
`renderToStaticMarkup`'s output rather than a markdown library's. `markdown.py`
is therefore a pair of renderers over markdown-it's token stream, not a call to
`md.render()`: `'` escapes to `&#x27;`, void elements are `<br/>` with no space,
`~~x~~` is `<del>` rather than `<s>`, table cells carry no newlines between
them, and a raw HTML block is escaped text with **no** paragraph around it
(there is no `rehype-raw` over there).

**Two surfaces, one parse.** Question text renders into a `<div>` and may emit
anything. An option label renders inside the `<label>` around a radio, which
admits phrasing content only, so the live survey's option-label component
remaps paragraphs to spans and gives links and inline code classes of their own:

| | question text | option text |
| --- | --- | --- |
| `p` | `<p>` | `<span>` |
| `a` | `<a href>` | `+ class`, `target="_blank"`, `rel="noreferrer"` |
| inline `code` | `<code>` | `+ class` |
| a list, a heading | as written | as written — a block in a label is how an author learns it doesn't belong there |

A **dropdown shows its options literally**, markers and all. A `<select>` holds
text and nothing else, and quietly changing the layout to render markup would
hide the fact that the two settings don't combine.

One rule is invisible in the reference JSX and worth knowing: the component
writes `<code className="…" {...props}/>` with the spread **last**, so a fenced
block — whose props carry `className="language-py"` — keeps the language class
and loses the styled one, while inline code keeps the styled one. A fence with
no language takes the styled class. Both branches are recorded.

**Not handled: GFM footnotes.** `remark-gfm` implements them and markdown-it's
`gfm-like` preset does not, and the markup is deeply remark-specific
(`user-content-fn-1`, `data-footnote-ref`, a screen-reader heading, a `↩`
backref). A footnote previews as its literal source.
`test_footnotes_are_the_known_gap` pins that so it is not mistaken for a bug in
a survey.

`examples/markdown_survey.json` exercises the lot in one page: emphasis and a
link in question text, styled links and inline code in options, a heading, a
list, a blockquote and an aligned table, markdown inside linear-scale labels, a
dropdown keeping its options literal, text that only looks like markdown, an
undrawn type whose wording still renders, and the footnote gap.

## Design constraints

These are the rules that make the output trustworthy. Please read them before
changing a template.

**The markup is copied, not invented.** Class strings in the templates are
verbatim from the live survey's components. Both the semantic `edsl-…` classes
and the Tailwind utilities matter: the utilities are what actually paint the
control, and `assets/questions.css` is compiled from those same components. If
you change a class string, change it because the reference component changed.

**Byte parity is the contract.** Tests assert exact string equality with
recorded output from the reference components, not a normalized or
tree-compared approximation. It is strict enough to catch whitespace and
attribute changes, and it is worth some awkwardness in the templates. If a
template becomes hard to read as a result, make the template uglier rather than
the assertion weaker.

That is why the templates are dotted with `{#- -#}` separator lines. JSX
discards whitespace between elements, so the reference output has none; Jinja
emits every newline and indent it sees. `trim_blocks` and `lstrip_blocks` (set
in `templating.py`) handle whitespace around `{% %}` tags, but boundaries
between two *literal* elements need the explicit empty comment. One trap worth
knowing: **Jinja comments do not nest**, so a `{#` … `#}` block that quotes a
whitespace-control comment inside it terminates early and leaks its remaining
text into the page.

**Escaping must match the reference, not MarkupSafe.** The reference escapes
`"` as `&quot;` and `'` as `&#x27;`, *including in text content*. MarkupSafe
emits `&#34;` and `&#39;`. Python's `html.escape(s, quote=True)` is an exact
match, so `templating.py` routes every interpolation through `html.escape` via
Jinja's `finalize` hook and marks the result safe; `autoescape` stays on purely
as a backstop. Do not disable `finalize` — an option like `Don't know` will
silently stop matching.

**Light mode.** Every `dark:` variant is inert unless a `.dark` ancestor
exists, and previews never emit one.

**The shell is the respondent page.** `renderer.py` reproduces the page someone
taking the survey sees — containers, progress bar, Next button, footer — not
the authoring-side preview. Two values in it cannot be derived by reading the
reference source and were captured from its runtime output instead: the merged
container class list (a class-merging helper resolves conflicting Tailwind
utilities, so it is not a concatenation), and the progress bar's ARIA and
`data-…` attributes (generated by Radix).

## Tests

```bash
uv run pytest                       # everything
uv run python tests/test_choice.py  # or a standalone runner, which needs no pytest
```

The standalone runners exist so a single file can be run and read on its own;
they need `runway` importable, so run them through `uv run` or with the package
installed.

`test_choice` holds the question byte-parity tests and the goldens' own
contract; `test_progress` covers the indicator — its markup against the
recording, and the resolver that decides which rendering a config draws at a
position; `test_survey` covers the survey level — page naming, progress
advancing, and drawn and undrawn question types side by side via
`examples/mixed_survey.json`; `test_background` covers the questions no
respondent is shown — compute, image generation and the `thinking_question()`
wrapper, which keeps the type it wrapped and so has to be intercepted ahead of
the type registry — via `examples/background_survey.json`; `test_markdown`
covers the two markdown surfaces — question text and option labels, which
serialize differently — and what is deliberately not rendered.

### The goldens

The markup the tests compare against is **recorded, not transcribed**. The live
survey's own React components are rendered with `renderToStaticMarkup` and the
output is committed here as two files:

| file | role |
| --- | --- |
| `tests/react_cases.json` | what was rendered — question dicts, progress values |
| `tests/react_goldens.json` | the recorded markup, keyed by the same names |

`tests/goldens.py` reads them and nothing else, which is the point: the contract
is checkable on any checkout with Python alone — no node, no copy of the web
application. `test_every_case_has_a_golden` holds the two files to being a
matched pair, and `test_every_recorded_question_case_matches` compares *every*
recorded question case against this package — so a case that is recorded is
always a case that is checked, and there is no need to hand-write an assertion
per case.

**Recording happens in the repository that owns those components, not here.**
When they change, the re-recorded pair lands in this repo as an ordinary
commit, and the diff says exactly what the templates have to be updated to
match. Two conventions over there make that work: every recorded component is
*imported* by the recorder rather than transcribed into it — a transcription is
a second copy of the markup, and a copy drifts silently — and every case
includes an option with an apostrophe. React escapes `'` as `&#x27;` and `"` as
`&quot;`, including in text content, where MarkupSafe would emit
`&#39;`/`&#34;`; a golden with no quotes in it passes while the escaping path is
silently broken. That happened once already.

`react_goldens.json` also holds one shell case, recorded around a literal
content marker so the markup before and after a question can be checked without
the recording knowing what a question looks like.

## Regenerating the stylesheet

`assets/questions.css` is vendored, generated output — ~50 KB, ~9 KB gzipped.
It covers the whole respondent component tree, so adding most question types
needs no regeneration. A *template* that starts emitting utilities nothing
emitted before does; the stepped progress markers were one.

`assets/tailwind.config.cjs` extends the live application's own Tailwind config
rather than redeclaring a theme, so fonts, colors, screens and the
`darkMode: ['selector', '.dark']` setting are identical by construction. It
therefore needs a checkout of that application:

```bash
RUNWAY_REFERENCE_APP=/path/to/the/web/app \
npx tailwindcss \
  -c src/runway/assets/tailwind.config.cjs \
  -i src/runway/assets/base.css \
  -o src/runway/assets/questions.css --minify
```

`RUNWAY_REFERENCE_COMPONENTS` narrows the component glob if the default
(`src/components/**/*.{ts,tsx}` under that checkout) is wider than you want.
The content globs point at the templates — where class strings actually live —
and at the reference components; never at rendered output, which would keep
dead classes alive in the stylesheet after a template changed.

## Adding a question type

1. Record the reference component's output for the type, with a representative
   question — include one option containing an apostrophe, so the escaping path
   is covered. Recording happens in the repository that owns the components; a
   new `react_cases.json` / `react_goldens.json` pair lands here.
2. Add `src/runway/templates/questions/<type>.html`, transcribing the reference
   markup. Class strings go inline so the template can be diffed against it.
3. Add `src/runway/question_types/<type>.py` exposing
   `render(question, humanize_schema)` that prepares context and renders the
   template.
4. Register it in `src/runway/question_types/__init__.py`. Anything
   unregistered falls through to the stand-in, so an unregistered type is never
   an error.
5. Add a test asserting equality with the recording.
6. Mark it available in the table above.
7. Regenerate `assets/questions.css`.

Where the reference implements several types as one thing, follow it rather
than the file naming: `choice.html` serves multiple choice, Likert five, yes/no
and the linear scale because over there they are four components with one body
and four wrapper classes, and four transcriptions of one component would be
four copies to keep in step by hand. Record each type separately even so — the
sharing is the reference's to undo, and the recordings are how that would be
noticed.

A type that is not in the table above needs no work here — it needs a humanize
configuration first, and the warning says so on the page. The set of types that
have one lives in `question_types/unsupported.py`; extend it when the schema
does, or a newly supported type will keep reading as unsupportable.

## Known gaps

- **Fonts.** The page links Plus Jakarta Sans from Google Fonts, matching the
  live survey. This is the one external request it makes, so the page is not
  truly self-contained and renders with fallback metrics offline. Embedding the
  woff2 as base64 would fix both.
- **Rich question text and option labels.** Images, video and PDFs referenced
  from question text or from an option are resolved server-side during a live
  run; only the plain text path is handled here. An option that references a
  file previews as the reference text it was written as. The label markup is
  the live one either way — the wrapper spans an option label carries do not
  depend on whether it resolved to media — so only the innermost text differs.
- **Option randomization.** Not applied. A survey that randomizes options shows
  the authored order.
- **The Next button does nothing.** The `<form>` is rendered for layout parity
  but has no `action`, so submitting reloads the page. Kept as-is because the
  button's classes and position are part of what the preview shows; use the
  toolbar to move between questions.
- **Piped values are not resolved.** `{{ agent.x }}`, `{{ scenario.x }}` and
  `{{ q_name.answer }}` render as written. Resolving them means binding a
  survey to agent and scenario data, which would be a per-binding rendering —
  the reason to do that substitution in the page rather than by multiplying out
  files.
- **Position is inferred.** Every page is placed by where it sits in the
  authored item list: the bar fills to the share of items before it, and a
  stepper's markers advance on the same reading. The live page resolves position
  from survey flow, so a survey with skip logic will differ — the further a
  respondent skips, the more it differs. The renderings themselves are exact;
  only the position feeding them is inferred.
- **Settings that govern submission, not markup.** `optional`,
  `custom_validation`, `submitting_indicator` and attention checks are all
  accepted in the schema and ignored in the output — each governs validation or
  what happens on submit, none of which a static page can show. The schema's
  `comment` and `progress` *are* rendered — they are the settings that put
  something visible on the page.

## Layout

```
runway/
├── pyproject.toml
├── uv.lock
├── examples/                     surveys to render
│   ├── one_question_survey.json  one multiple choice question
│   ├── mixed_survey.json         one of every type, drawn and undrawn
│   ├── background_survey.json    questions answered without a respondent
│   ├── markdown_survey.json      markdown in question and option text
│   └── styled_survey.json        a survey with custom_css
├── tests/
│   ├── goldens.py                reads the two recorded files
│   ├── react_cases.json          what was rendered
│   ├── react_goldens.json        what came out
│   └── test_*.py
└── src/runway/
    ├── __init__.py               public API
    ├── cli.py                    the `runway` command
    ├── __main__.py               `python -m runway`
    ├── renderer.py               page/body/progress composition
    ├── progress.py               which indicator a config draws at a position
    ├── survey.py                 input parsing, one-page-per-question output
    ├── templating.py             the Jinja environment (escaping + whitespace)
    ├── html.py                   escaping matched to the reference
    ├── markdown.py               question and option text, serialized as React does
    ├── icons.py                  inline lucide SVGs
    ├── question_types/           context preparation only; markup lives in templates/
    │   ├── __init__.py           RENDERERS registry
    │   ├── choice.py             multiple_choice, likert_five, yes_no, linear_scale
    │   ├── background.py         compute/image_generation/thinking: never shown
    │   └── unsupported.py        the stand-in: a note, or a warning
    ├── templates/
    │   ├── page.html             document shell + toolbar script
    │   ├── toolbar.html          preview chrome: jump between questions
    │   ├── panel.html            one question's page inside a bundle
    │   ├── body.html             the respondent page
    │   ├── progress.html         the bar and the stepped indicator
    │   └── questions/
    │       ├── choice.html
    │       ├── background.html
    │       └── unsupported.html
    └── assets/
        ├── questions.css         generated, vendored — what ships
        ├── base.css              build input
        └── tailwind.config.cjs   build config
```

## License

MIT — see [LICENSE](LICENSE). Third-party notices for vendored icon geometry,
reproduced attribute names and generated CSS are in [LICENSES.md](LICENSES.md).
