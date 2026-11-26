/**
 * Build-time only -- generates questions.css, which is what the Python package
 * actually ships. Not needed at runtime, and not needed to use this package at
 * all; it is here so the stylesheet can be rebuilt rather than only inherited.
 *
 * It does not declare a theme. It *extends* the Tailwind config of the
 * reference web survey this package renders previews of, so fonts, colors,
 * screens and the `darkMode: ['selector', '.dark']` setting are identical to
 * the live application by construction rather than by transcription. A preview
 * page never adds a `.dark` ancestor, so every `dark:` variant stays inert and
 * the page renders light.
 *
 * Point RUNWAY_REFERENCE_APP at a checkout of that application -- the directory
 * holding its `tailwind.config.js` -- RUNWAY_REFERENCE_COMPONENTS at the glob
 * for its respondent-facing components, and RUNWAY_REFERENCE_STYLESHEETS at the
 * plain stylesheets those components import, separated by the platform's path
 * delimiter (`:`, or `;` on Windows). All three are required and none has a
 * default; that is intentional, since a theme, a component set or a stylesheet
 * guessed here would be a second source of truth. Guessing the components is
 * the most dangerous, because it fails quietly: a stylesheet built from the
 * whole component tree draws every page correctly and is several times the
 * size. The survey assistant's chat is not drawn here, so its components are
 * left out of the glob.
 *
 * The stylesheets are the rules no utility class carries -- a markdown table's
 * frame, which the reference styles by its `edsl-table` hooks. They are read
 * from the reference at build time and added to the base layer as written, so
 * nothing in questions.css is transcribed by hand; see `referenceStylesheets`.
 *
 * Content globs cover both sources of class strings:
 *   1. the reference components, which the templates transcribe classes from
 *   2. the templates themselves, which are what actually gets emitted
 *
 * Generated pages are deliberately NOT globbed: they would keep classes alive
 * in the stylesheet long after the template that produced them changed.
 *
 * From the reference application's directory:
 *
 *   RUNWAY_REFERENCE_APP=. \
 *   RUNWAY_REFERENCE_COMPONENTS='./<respondent components>/{*.tsx,!(<assistant>)/**\/*.tsx}' \
 *   RUNWAY_REFERENCE_STYLESHEETS='./<respondent components>/<table stylesheet>.css' \
 *   npx tailwindcss \
 *     -c /path/to/runway/src/runway/assets/tailwind.config.cjs \
 *     -i /path/to/runway/src/runway/assets/base.css \
 *     -o /path/to/runway/src/runway/assets/questions.css --minify
 *
 * Check the result before committing it: the vendored stylesheet is ~70 KB, and
 * a glob that reached too far shows up as a much larger one rather than as an
 * error. `tests/test_packaging.py` holds it to a band for that reason.
 */
const path = require('path');

const APP = process.env.RUNWAY_REFERENCE_APP;
if (!APP) {
    throw new Error(
        'RUNWAY_REFERENCE_APP is not set. It must point at the directory ' +
        'holding the reference web survey\'s tailwind.config.js -- this file ' +
        'extends that theme rather than redeclaring one.',
    );
}

const base = require(path.resolve(APP, 'tailwind.config.js'));

const components = process.env.RUNWAY_REFERENCE_COMPONENTS;
if (!components) {
    throw new Error(
        'RUNWAY_REFERENCE_COMPONENTS is not set. It must be the glob for the ' +
        'reference application\'s respondent-facing components. There is no ' +
        'default on purpose: a guess wide enough to be safe sweeps that ' +
        'application\'s whole component tree, which builds a stylesheet ' +
        'several times the size of the vendored one -- and builds it quietly, ' +
        'since a bloated stylesheet renders every page correctly.',
    );
}

const stylesheets = process.env.RUNWAY_REFERENCE_STYLESHEETS;
if (!stylesheets) {
    throw new Error(
        'RUNWAY_REFERENCE_STYLESHEETS is not set. It must list the plain ' +
        'stylesheets the reference application\'s respondent-facing components ' +
        'import, separated by ' + JSON.stringify(path.delimiter) + '. Left out, ' +
        'the build succeeds and every rule they hold is missing -- a markdown ' +
        'table previews with no frame and no scroll.',
    );
}

/**
 * The reference's own stylesheets, added to the base layer as written.
 *
 * Its rules sit in `:where()`, so they weigh nothing against a survey's custom
 * CSS or a utility -- the order they land in changes nothing. postcss is the
 * reference application's copy, resolved from there, because this package has
 * no node_modules of its own.
 */
function referenceStylesheets({ addBase }) {
    const fs = require('fs');
    const postcss = require(require.resolve('postcss', { paths: [APP] }));
    for (const file of stylesheets.split(path.delimiter).filter(Boolean)) {
        const css = fs.readFileSync(path.resolve(APP, file), 'utf8');
        addBase(postcss.parse(css, { from: file }).nodes);
    }
}

module.exports = {
    ...base,
    plugins: [...(base.plugins || []), referenceStylesheets],
    content: [
        components,
        path.join(__dirname, '../templates/**/*.html'),
        path.join(__dirname, '../**/*.py'),
    ],
};
