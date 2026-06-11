# ADR 0002: Src-Layout Installable Package as the Single Import Contract

Date: 2026-06-11

## Status

Accepted.

## Context

The repository has no packaging manifest at all: `git ls-files` has zero hits for
`pyproject.toml`, `setup.py`, `setup.cfg`, or `requirements.txt`. The package root
`src/werewolf_eval/__init__.py` is a clean src-layout package, but it has never been
declared installable, so the import path is hand-threaded as `PYTHONPATH=src` through
at least five places: `.github/workflows/tests.yml:23`, `AGENTS.md:85`,
`live-check.bat:4`, `launch-theater.py:97`, and `tools/live_check_deepseek.py:57`.

The 2026-06-08 health check ranked this as Top-10 item #2
(`docs/HEALTH_CHECK_2026-06-08.md`; details in
`docs/health-check/03-architecture-optimization.md` P-1, P-2, P-5) and identified it
as the common root cause for the packaging/entrypoint debt cluster: two inconsistent
test import strategies (26 test files with `sys.path.insert` boilerplate vs ~27
env-only files), no `requires-python` declaration despite a CI pin to 3.12, and an
undocumented "pure stdlib, zero third-party runtime dependencies" invariant.

The health check also flagged an ADR numbering conflict: both packaging (P-1) and the
single `werewolf` CLI (E-1) were drafted as "ADR 0002" candidates.

## Decision

Adopt a minimal PEP 621 `pyproject.toml` as the single package/import contract:

- `name = "werewolf-eval"`, package root `src/werewolf_eval` (src-layout, unchanged).
- `requires-python = ">=3.12"` — a lower bound aligned with the existing CI pin,
  deliberately not `==3.12`.
- `dependencies = []` — this writes the currently implicit "pure stdlib" invariant
  onto paper. Adding the first real runtime dependency must be a deliberate edit to
  this list, not an ambient `import requests` that works on one machine.
- Build backend: **hatchling**. Rationale: an editable install (`pip install -e .`)
  builds entirely in a temporary directory and does not drop `*.egg-info/` into the
  source tree, whereas setuptools does. The repository's `.gitignore` has no
  egg-info/dist/build rules (health check P-5), so the setuptools choice would force
  a `.gitignore` change in the same slice; hatchling makes that unnecessary.
  Hatchling is also PEP 621-native and needs only a two-line explicit src-layout
  declaration. Setuptools (`[tool.setuptools]` + `package-dir`) remains a documented
  fallback if build-backend resolution is ever a problem in a constrained
  environment.

This ADR takes the 0002 number for the packaging contract and explicitly defers the
CLI taxonomy: a single `werewolf` console-script entrypoint surface (health check
E-1, `[project.scripts]`) is a separate, larger decision and requires its own ADR.

## Transition Policy

`PYTHONPATH=src` remains supported during the transition. The canonical test command
(`PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`) keeps working
unchanged whether or not the package is installed. This is the deliberate
"defer the switch" mitigation for the half-migration risk named in P-1: two import
mechanisms coexist temporarily, with the editable install as the declared end state.

TODO (future slices, not this ADR):

- Switch CI (`tests.yml`) and launchers (`live-check.bat`, `launch-theater.py`,
  `tools/live_check_deepseek.py`) to rely on the editable install instead of
  `PYTHONPATH=src`.
- Delete the 26 per-test-file `sys.path.insert` boilerplate blocks and unify the
  test import strategy (health check P-3; needs ADR 0003, including the
  unittest-vs-pytest runner decision before any `conftest.py` is introduced).
- `[project.scripts]` entrypoints / `werewolf` CLI (health check P-4 / E-1; needs
  its own ADR).

## Consequences

- `pip install -e .` makes `werewolf_eval` importable everywhere (any cwd, no env
  vars), for tests, launchers, and downstream consumers alike.
- The package identity (name, version, supported Python, dependency policy) has a
  single source of truth.
- `python -m build` / wheel distribution becomes possible later (relevant to the
  Qt-bundle distribution story) without further groundwork.
- Until CI/launchers are switched (TODO above), a broken editable install can be
  masked by the still-present `PYTHONPATH=src` paths; reviewers of packaging changes
  must test the no-PYTHONPATH path explicitly.
