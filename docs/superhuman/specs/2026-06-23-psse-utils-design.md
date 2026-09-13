# Design: `psse-utils` — a shared home for small PSS/E scripts

**Date:** 2026-06-23
**Status:** Approved, pending implementation

---

## Overview

Create **`psse-utils`** — a single PyPI-published package that collects small
PSS/E utility scripts built on top of [`psse-model-util`](https://pypi.org/project/psse-model-util/).
The goal is to **avoid standing up a new GitHub repo + PyPI project for every
small script**: new scripts are added as modules here and published as part of
one package.

This is implemented by **repurposing the brand-new `flowgate_key_facilities`
repo** (a beta nobody has installed) rather than creating a third repo — reusing
its GitHub environments, `publish.yml`, and CI. The existing flowgate CLI becomes
the first script in the collection.

PyPI publishing is required (not GitHub-only): the package must `pip install`
cleanly on networks where `pip install git+https://…` is burdensome (e.g. an
employer network).

---

## Decisions (locked)

- **Repurpose, don't recreate:** rename repo `flowgate_key_facilities` → `psse_utils`.
- **Per-script console commands** (one `[project.scripts]` entry per script) — not
  an umbrella subcommand CLI. Lowest friction to "drop a script in."
- **Separate logic from CLI** in each script: importable functions + a thin
  `main(argv)`. This keeps a future **TUI or small web UI** (TBD, out of scope
  now) able to call the logic without going through argparse.
- **src layout** (`src/psse_utils/`), matching `psse-model-util`.
- **CalVer** `YYYY.M.micro` (matches `psse-model-util` and the publishing runbook).
- **Keep names:** the flowgate command stays **`flowgate-key-facilities`**; its
  module stays **`flowgate_key_facilities.py`** (now `psse_utils.flowgate_key_facilities`).
- **First release:** a pre-release (`…b1`), consistent with the family.

---

## Architecture / layout

```
src/psse_utils/
    __init__.py                  # exposes __version__
    __about__.py                 # version — single source of truth
    flowgate_key_facilities.py   # first script (moved from the old repo root)
    # <future scripts>.py
tests/
    test_flowgate_key_facilities_args.py
    test_flowgate_key_facilities_main.py
    conftest.py
    data/   (Model_1.raw, synthetic_flowgates.mon)
pyproject.toml  README.md  LICENSE
.github/workflows/ci.yml  publish.yml
```

### Per-script convention

Each script module under `psse_utils/`:
- exposes its **core logic as importable functions** (no `argparse` inside them);
- provides a thin **`main(argv: list[str] | None = None) -> int`** that parses
  args and calls those functions;
- is registered as a **console command** in `[project.scripts]`;
- has **no intra-package imports** — it may depend on stdlib and third-party
  packages, but never on another `psse_utils.<script>` module, so it stays
  copy-paste portable as a single file (see README's "Adding a script").

Example (`pyproject.toml`):
```toml
[project.scripts]
flowgate-key-facilities = "psse_utils.flowgate_key_facilities:main"
# future:
# psse-something = "psse_utils.something:main"
```

Adding a script = drop `psse_utils/<name>.py` (logic + `main`), add one
`[project.scripts]` line, add tests named **`tests/test_<name>_*.py`** (script-
prefixed so they stay unambiguous as the collection grows). No other wiring.

### Dependencies

- **Base:** `psse-model-util>=2026.4.5b1` (the engine; also pulls pandas/numpy/networkx).
  `pandas` / `networkx` listed explicitly since scripts use them directly.
- **Heavy / per-script deps go behind extras** in `[project.optional-dependencies]`
  (e.g. a future `psse-utils[web]` for a web UI), so the base install stays lean.

---

## Packaging / distribution

- PyPI distribution name **`psse-utils`**; import package `psse_utils`.
- **Wheel:** `[tool.hatch.build.targets.wheel] packages = ["src/psse_utils"]`;
  version from `src/psse_utils/__about__.py`.
- **`publish.yml`:** reuse the existing Trusted-Publishing workflow; retarget the
  TestPyPI/PyPI environment URLs to `psse-utils`.
- **`ci.yml`:** reuse the pip-based CI (`pip install --pre -e .` then `pytest`).
- **GitHub environments** (`pypi` with reviewer, `testpypi`) already exist on the
  repo and carry over the rename.
- **PyPI-side (human, one-time):** add a `psse-utils` pending publisher on PyPI
  and TestPyPI (Owner `ppsyOps`, Repo `psse_utils`, Workflow `publish.yml`,
  Env `pypi`/`testpypi`) — per `OneDrive/Trapezia/PyPI-and-TestPyPI-setup-runbook.md`.
- **Yank** the orphaned `flowgate-key-facilities 0.1.0b1` on PyPI (unused beta).

---

## Migration (high level — detailed steps belong in the implementation plan)

1. Rename GitHub repo `flowgate_key_facilities` → `psse_utils`; re-point remote;
   rename local clone; recreate the in-project `.venv` (stdlib `python -m venv`).
2. Restructure to `src/psse_utils/`: move `flowgate_key_facilities.py` →
   `src/psse_utils/flowgate_key_facilities.py`; add `__init__.py` (+`__version__`)
   and `__about__.py`.
3. Update `pyproject.toml`: name `psse-utils`, CalVer version `…b1`, wheel/version
   paths, `[project.scripts]` (`flowgate-key-facilities = "psse_utils.flowgate_key_facilities:main"`),
   deps, URLs, description/keywords.
4. Rename test files to script-prefixed names (`test_cli_args.py` →
   `test_flowgate_key_facilities_args.py`, `test_cli_main.py` →
   `test_flowgate_key_facilities_main.py`); update imports to
   `psse_utils.flowgate_key_facilities`; fix the coverage target.
5. Update `publish.yml` URLs and `ci.yml` (already pip-based) for the new name.
6. Verify: `build` (wheel has `psse_utils/…`, console script), `twine check`,
   `pytest` against the published `psse-model-util` beta, clean-venv install.
7. PyPI: add the `psse-utils` pending publisher (human); publish a `…b1`
   pre-release via `publish.yml`; yank the flowgate-key-facilities beta.

(Optionally split the flowgate logic/CLI within its module to match the
"separate logic from CLI" convention, so it's the template for future scripts.)

---

## Testing

- Keep the existing flowgate tests, renamed to script-prefixed files
  (`test_cli_args.py` → `test_flowgate_key_facilities_args.py`,
  `test_cli_main.py` → `test_flowgate_key_facilities_main.py`) with imports
  updated to `psse_utils.flowgate_key_facilities`; enforce the current coverage gate.
- Each new script ships with its own `tests/test_<name>_*.py`.
- CI runs `pytest` against the **published** `psse-model-util` (real dependency
  resolution), as the flowgate repo already does.

## Out of scope (now)

- TUI / web UI front-ends (future; the logic/CLI separation leaves the door open).
- An umbrella subcommand CLI (can be added later without breaking per-script commands).
- Migrating any non-flowgate scripts (none exist yet).
