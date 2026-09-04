"""Regenerate the example surveys from their EDSL sources.

Each module in ``examples/src`` builds a ``Survey`` the way an author would, and
names a ``humanize_schema`` beside it when the survey needs one. This writes the
two files that pair produces, and can drive the CLI over them::

    uv run python examples/build.py            # rewrite the JSON
    uv run python examples/build.py --render   # and previews/*.html
    uv run python examples/build.py --check    # write nothing; fail if stale

**The survey JSON is ``Survey.to_dict()`` verbatim** -- not a shape invented
here. That is what an author actually has on disk after dumping a survey, so an
example that differed from it would be demonstrating a format nobody produces.
Its keys about flow are along for the ride; a preview ignores them.

**The schema is a file of its own**, under ``schemas/``, and only exists where a
survey needs one -- ``Survey.to_dict()`` has no room for it, because the two are
configured separately. A sidecar lives in a subdirectory rather than beside its
survey as ``<name>.schema.json`` so that ``examples/*.json`` still means "the
surveys" and nothing has to filter the list.

Rendering goes through the CLI rather than calling ``render_survey`` directly,
so what produces the committed previews is the same command a reader would type.

The JSON is generated but **committed**, because it is what the tests read: a
suite that had to build its own fixtures would need edsl installed and working
to tell you anything at all, including that edsl had broken something.
Committing it is also what makes a change reviewable -- a diff here is a change
to what every parity and survey test is held against. `edsl_version` rides along
as part of `to_dict()` output, so an edsl upgrade will show up here as a diff.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "src"
SCHEMAS = HERE / "schemas"
SCENARIOS = HERE / "scenarios"
REPO = HERE.parent
PREVIEWS = REPO / "previews"


def load_module(path: Path):
    """Import a source module by path, without it needing to be a package.

    ``src`` goes on the import path so one source can import another: an example
    that is another example under a different schema imports its survey rather
    than restating it, and the two cannot then drift apart.
    """
    if str(SOURCES) not in sys.path:
        sys.path.insert(0, str(SOURCES))
    spec = importlib.util.spec_from_file_location(f"examples_src_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dump(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def wanted(source: Path) -> dict[Path, str]:
    """The files a source module describes: its survey, its schema, its scenarios.

    Three files because they are three separately held things. A survey carries
    no humanize schema, and it carries no scenario list either -- a scenario list
    is uploaded beside a survey and bound to it rather than stored in it, which
    is why each reaches a preview through a flag of its own.
    """
    module = load_module(source)
    files = {HERE / f"{source.stem}.json": dump(module.survey.to_dict())}
    schema = getattr(module, "humanize_schema", None)
    if schema:
        files[SCHEMAS / f"{source.stem}.json"] = dump(schema)
    scenarios = getattr(module, "scenarios", None)
    if scenarios is not None:
        files[SCENARIOS / f"{source.stem}.json"] = dump(scenarios.to_dict())
    return files


def build(render: bool = False, check: bool = False) -> int:
    """Rewrite every example, or with ``check`` report whether any is stale.

    ``check`` is what keeps a generated-but-committed file honest: it is easy to
    edit the JSON directly, never notice that the source no longer describes it,
    and have the next build silently revert the edit.
    """
    sources = sorted(SOURCES.glob("*.py"))
    if not sources:
        print(f"no sources in {SOURCES}", file=sys.stderr)
        return 1

    expected: dict[Path, str] = {}
    for source in sources:
        expected.update(wanted(source))

    # A schema or scenario list whose source stopped naming one, left behind.
    # Surveys are not swept the same way: a .json in examples/ with no source is
    # somebody's own file, where these two directories hold nothing but
    # generated output.
    orphans = [
        path
        for directory in (SCHEMAS, SCENARIOS)
        for path in sorted(directory.glob("*.json"))
        if path not in expected
    ]

    stale = []
    for path, content in sorted(expected.items()):
        before = path.read_text(encoding="utf-8") if path.is_file() else None
        state = "unchanged" if before == content else ("new" if before is None else "changed")
        if state != "unchanged":
            stale.append(path)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        print(f"{state:>9}  {path.relative_to(REPO)}")
    for path in orphans:
        stale.append(path)
        if not check:
            path.unlink()
        print(f"{'orphan' if check else 'removed':>9}  {path.relative_to(REPO)}")

    if check:
        if stale:
            print(
                f"\n{len(stale)} file(s) no longer match their source. "
                "Run: python examples/build.py",
                file=sys.stderr,
            )
            return 1
        return 0

    if render:
        for source in sources:
            survey = HERE / f"{source.stem}.json"
            schema = SCHEMAS / f"{source.stem}.json"
            scenarios = SCENARIOS / f"{source.stem}.json"
            command = [sys.executable, "-m", "runway", "render", str(survey)]
            if schema.is_file():
                command += ["--schema", str(schema)]
            if scenarios.is_file():
                command += ["--scenarios", str(scenarios)]
            command += ["-o", str(PREVIEWS)]
            result = subprocess.run(command, capture_output=True, text=True, cwd=REPO)
            if result.returncode != 0:
                print(result.stdout + result.stderr, file=sys.stderr)
                return result.returncode
            print(f" rendered  {(PREVIEWS / f'{source.stem}.html').relative_to(REPO)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate examples/*.json, examples/schemas/*.json and "
        "examples/scenarios/*.json from examples/src/*.py."
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Also write previews/*.html, by running the runway CLI over each.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; exit non-zero if any file is out of date.",
    )
    args = parser.parse_args(argv)
    return build(args.render, args.check)


if __name__ == "__main__":
    raise SystemExit(main())
