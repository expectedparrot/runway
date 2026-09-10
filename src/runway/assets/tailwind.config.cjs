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
 * holding its `tailwind.config.js` -- and RUNWAY_REFERENCE_COMPONENTS at the
 * glob for its respondent-facing components. Both are required and neither has
 * a default; that is intentional, since a theme or a component set guessed here
 * would be a second source of truth. Guessing the second is the more dangerous
 * of the two, because it fails quietly: a stylesheet built from the whole
 * component tree draws every page correctly and is several times the size.
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
 *   RUNWAY_REFERENCE_COMPONENTS='./<respondent components>/**\/*.{ts,tsx}' \
 *   npx tailwindcss \
 *     -c /path/to/runway/src/runway/assets/tailwind.config.cjs \
 *     -i /path/to/runway/src/runway/assets/base.css \
 *     -o /path/to/runway/src/runway/assets/questions.css --minify
 *
 * Check the result before committing it: the vendored stylesheet is ~62 KB, and
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

module.exports = {
    ...base,
    content: [
        components,
        path.join(__dirname, '../templates/**/*.html'),
        path.join(__dirname, '../**/*.py'),
    ],
};
