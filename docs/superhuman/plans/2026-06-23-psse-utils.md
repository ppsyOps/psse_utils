# psse-utils Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repurpose the `flowgate_key_facilities` repo into **`psse-utils`** — a PyPI package that collects small PSS/E scripts built on `psse-model-util`, with the existing flowgate CLI as its first script.

**Architecture:** Restructure the single-module repo into a `src/psse_utils/` package (src layout, matching `psse-model-util`). Each script is a module with importable logic + a thin `main()`, exposed as its own console command. Reuse the repo's existing Trusted-Publishing `publish.yml`, pip-based `ci.yml`, and GitHub environments. Code changes land first on a branch; the GitHub-repo rename + PyPI pending-publisher (human/owner steps) and the publish happen after merge.

**Tech Stack:** Python 3.11+, Hatchling (build + CalVer version from `__about__.py`), pytest + pytest-cov, Trusted Publishing (OIDC) via GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-06-23-psse-utils-design.md`.

**Baseline (current repo, branch `feat/psse-utils`):** single module `flowgate_key_facilities.py` at root; tests `tests/test_cli_args.py`, `tests/test_cli_main.py`, `tests/conftest.py`, `tests/data/`; `pyproject.toml` (name `flowgate-key-facilities`, static `version = "0.1.0b1"`); `.github/workflows/{ci,publish}.yml`; the flowgate CLI imports `psse_model_util` and is published as `flowgate-key-facilities 0.1.0b1` (a beta, to be yanked).

**Locked decisions:** repurpose (don't recreate); src layout; per-script console commands; logic separated from CLI; CalVer `YYYY.M.micro` (first release `2026.6.0b1`); keep the `flowgate-key-facilities` command and `flowgate_key_facilities.py` module name; script-prefixed test files; base dep `psse-model-util>=2026.4.5b1`.

---

## File structure (end state)

```
src/psse_utils/
    __init__.py                  # from psse_utils.__about__ import __version__
    __about__.py                 # __version__ = "2026.6.0b1"
    flowgate_key_facilities.py   # moved from repo root (imports unchanged)
tests/
    conftest.py                          # adds src/ to sys.path fallback
    test_flowgate_key_facilities_args.py # was test_cli_args.py
    test_flowgate_key_facilities_main.py # was test_cli_main.py
    data/  Model_1.raw  synthetic_flowgates.mon
pyproject.toml   README.md   LICENSE   pdm.lock   pdm.toml
.github/workflows/ci.yml   publish.yml
docs/superpowers/{specs,plans}/...
```

---

## Phase 0 — Baseline

Work on the existing `feat/psse-utils` branch (already has the spec + this plan).

- [ ] **Step 0.1: Confirm the current suite is green before restructuring**

Run (from the repo root, using the project venv's python — `python -m pip install --pre -e .` first if needed):
```
python -m pytest -q
```
Expected: the existing flowgate tests pass (16 passed, ~100% coverage). If red, stop and fix before continuing.

---

## Phase 1 — Restructure into `src/psse_utils/`

**Files:** move `flowgate_key_facilities.py`; create `src/psse_utils/__init__.py`, `src/psse_utils/__about__.py`.

- [ ] **Step 1.1: Move the module into the package**

```bash
mkdir -p src/psse_utils
git mv flowgate_key_facilities.py src/psse_utils/flowgate_key_facilities.py
```
No code edits inside the file — its imports are `from psse_model_util... import`, unaffected by the move.

- [ ] **Step 1.2: Create the version source `src/psse_utils/__about__.py`**

```python
"""Package version — single source of truth for psse_utils versioning."""

__version__ = "2026.6.0b1"
```

- [ ] **Step 1.3: Create `src/psse_utils/__init__.py`**

```python
"""psse_utils — a collection of small PSS/E utility scripts built on psse-model-util."""

from psse_utils.__about__ import __version__

__all__ = ["__version__"]
```

- [ ] **Step 1.4: Commit**

```bash
git add -A
git commit -m "refactor: move flowgate module into src/psse_utils package"
```

---

## Phase 2 — pyproject + workflows retarget

**Files:** `pyproject.toml`, `.github/workflows/publish.yml`. (`ci.yml` already does `pip install --pre -e .` and needs no change.)

- [ ] **Step 2.1: Rewrite the `pyproject.toml` `[project]` + tool tables**

Replace the existing `[project]` name/version/description/urls/scripts and the
`[tool.*]` packaging/test/coverage tables so the file reads:

```toml
[project]
name = "psse-utils"
dynamic = ["version"]
description = "A collection of small PSS/E utility scripts built on psse-model-util."
readme = "README.md"
requires-python = ">=3.11,!=3.14.1,<3.15"
license = "MIT"
license-files = ["LICENSE"]
authors = [
    { name = "cadvena" }
]
keywords = ["psse", "power systems", "PSS/E", "scripts", "flowgate"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering",
]
dependencies = [
    "psse-model-util>=2026.4.5b1",
    "pandas",
    "networkx",
]

[project.urls]
Homepage = "https://github.com/ppsyOps/psse_utils"
Repository = "https://github.com/ppsyOps/psse_utils"
Issues = "https://github.com/ppsyOps/psse_utils/issues"

[project.scripts]
flowgate-key-facilities = "psse_utils.flowgate_key_facilities:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.version]
path = "src/psse_utils/__about__.py"
pattern = "__version__ = ['\"](?P<version>[^'\"]+)['\"]"

[tool.hatch.build.targets.wheel]
packages = ["src/psse_utils"]

[tool.pdm.dev-dependencies]
test = [
    "pytest>=8",
    "pytest-cov",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=psse_utils --cov-report=term-missing"

[tool.coverage.run]
source = ["src/psse_utils"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
fail_under = 95
```

Notes: `version` becomes **dynamic** (sourced from `__about__.py`); the old
`pythonpath = ["."]` is dropped — `conftest.py` (Step 3.3) handles import path.

- [ ] **Step 2.2: Retarget `publish.yml` environment URLs to the new project**

In `.github/workflows/publish.yml`, change the two `url:` lines:
- `https://test.pypi.org/p/flowgate-key-facilities` → `https://test.pypi.org/p/psse-utils`
- `https://pypi.org/p/flowgate-key-facilities` → `https://pypi.org/p/psse-utils`

- [ ] **Step 2.3: Commit**

```bash
git add pyproject.toml .github/workflows/publish.yml
git commit -m "build: rename distribution to psse-utils; CalVer dynamic version; src-layout packaging"
```

---

## Phase 3 — Tests: rename + fix imports

**Files:** rename the two test files; edit imports; update `tests/conftest.py`.

- [ ] **Step 3.1: Rename the test files (script-prefixed)**

```bash
git mv tests/test_cli_args.py tests/test_flowgate_key_facilities_args.py
git mv tests/test_cli_main.py tests/test_flowgate_key_facilities_main.py
```

- [ ] **Step 3.2: Update imports in the renamed tests**

In `tests/test_flowgate_key_facilities_args.py`: change
`from flowgate_key_facilities import _parse_args`
→ `from psse_utils.flowgate_key_facilities import _parse_args`.

In `tests/test_flowgate_key_facilities_main.py`: change
`from flowgate_key_facilities import main`
→ `from psse_utils.flowgate_key_facilities import main`.

(Also update the module-name references in their docstrings, `flowgate_key_facilities` →
`psse_utils.flowgate_key_facilities`, for accuracy.)

- [ ] **Step 3.3: Make `tests/conftest.py` add `src/` to `sys.path` (fallback when not installed)**

Replace `tests/conftest.py` with:
```python
"""Shared fixtures + import path for the psse_utils tests.

With the src/ layout the package is normally importable via the editable
install (`pip install -e .`). As a fallback for fresh checkouts, add src/ to
sys.path so `import psse_utils...` resolves.
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
```
(Keep any existing fixtures from the old conftest below this block.)

- [ ] **Step 3.4: Reinstall editable + run the suite**

```bash
python -m pip install --pre -e .
python -m pytest -q
```
Expected: same tests pass (now importing from `psse_utils.flowgate_key_facilities`),
coverage measured on `psse_utils`, gate ≥ 95% met.

- [ ] **Step 3.5: Commit**

```bash
git add -A
git commit -m "test: script-prefix flowgate test files; import from psse_utils; src/ conftest"
```

---

## Phase 4 — README for the collection

**Files:** `README.md`.

- [ ] **Step 4.1: Rewrite `README.md`** so it describes the *collection*, lists the
  flowgate script as the first entry, and documents install + how to add a script.

```markdown
# psse-utils

A collection of small PSS/E utility scripts built on
[`psse-model-util`](https://pypi.org/project/psse-model-util/). Instead of a new
repo + PyPI project per script, scripts live here and ship as one package.

## Installation

~~~
pip install --pre psse-utils
~~~

`--pre` is required while the package (and `psse-model-util`) are pre-releases.

## Scripts

### `flowgate-key-facilities`

Identify the key facilities for a set of PSS/E flowgates — equipment whose outage
would most impact those flowgates. For each flowgate in a `.mon` file it keeps AC
lines in a kV range and generators above a PMax, within `n` buses of the flowgate.

~~~
flowgate-key-facilities --mon flowgates.mon --raw Model.raw \
  --areas 1 2 3 --sc SCA --out-dir outputs/
~~~

(Full options: `flowgate-key-facilities --help`.)

## Adding a script

1. Create `src/psse_utils/<name>.py` with importable functions (the logic) plus
   a thin `main(argv=None) -> int` that parses args and calls them.
2. Add a console command: `[project.scripts]` → `your-command = "psse_utils.<name>:main"`.
3. Add tests `tests/test_<name>_*.py`.
4. Put any heavy/extra dependencies behind an extra in `[project.optional-dependencies]`.

## Development

~~~
pip install -e ../psse_model_util   # if developing the engine alongside
pip install --pre -e .
pytest
~~~
```

- [ ] **Step 4.2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for the psse-utils collection"
```

---

## Phase 5 — Verify the package

- [ ] **Step 5.1: Build + inspect the wheel**

```bash
python -m pip install --upgrade build
rm -rf dist && python -m build
python -c "import zipfile,glob; z=zipfile.ZipFile(sorted(glob.glob('dist/*.whl'))[-1]); print('\n'.join(n for n in z.namelist() if n.endswith(('.py','entry_points.txt','METADATA')))); print(z.read([n for n in z.namelist() if n.endswith('entry_points.txt')][0]).decode())"
```
Expected: files live under `psse_utils/` (e.g. `psse_utils/flowgate_key_facilities.py`),
metadata `Name: psse-utils`, version `2026.6.0b1`, `Requires-Dist: psse-model-util>=2026.4.5b1`,
and entry point `flowgate-key-facilities = psse_utils.flowgate_key_facilities:main`.

- [ ] **Step 5.2: twine check**

```bash
python -m pip install twine && python -m twine check dist/*
```
Expected: both `PASSED`.

- [ ] **Step 5.3: Clean-venv install smoke test**

```bash
python -m venv /tmp/psse-utils-verify
/tmp/psse-utils-verify/Scripts/python -m pip install --pre dist/psse_utils-*.whl
/tmp/psse-utils-verify/Scripts/python -c "import psse_utils; from psse_utils.flowgate_key_facilities import main; print('OK', psse_utils.__version__)"
/tmp/psse-utils-verify/Scripts/flowgate-key-facilities --help
```
Expected: `OK 2026.6.0b1`; the console command prints its usage. (Windows paths shown; adjust for OS.)

- [ ] **Step 5.4: Re-lock pdm (dependency set unchanged, but project metadata changed)**

```bash
python -m pdm lock
git add pdm.lock; git commit -m "build: refresh pdm.lock for psse-utils" || echo "no lock changes"
```

---

## Phase 6 — (Optional, recommended) split flowgate logic from CLI

Sets the convention for future scripts and enables a future TUI/web UI. Keep tests green.

- [ ] **Step 6.1: Extract a `run(...)` function**

In `src/psse_utils/flowgate_key_facilities.py`, factor the body of `main()` (after
arg parsing) into a pure function, e.g.:
```python
def run(*, mon, raw, areas, sc, out_dir, hops, kv_min, kv_max, gen_min_mw) -> dict:
    """Resolve flowgates -> collect key facilities -> write CSVs; return the result dict."""
    # (the existing pipeline body moves here)
```
`main(argv)` then parses args and calls `run(**kwargs)`.

- [ ] **Step 6.2: Add a focused test for `run()`** in
  `tests/test_flowgate_key_facilities_main.py` that calls `run(...)` directly with the
  fixtures and asserts the output CSVs / returned dict — independent of argparse.

- [ ] **Step 6.3: Run + commit**

```bash
python -m pytest -q
git add -A && git commit -m "refactor(flowgate): separate run() logic from main() CLI"
```

---

## Phase 7 — Human / owner steps (cannot be automated by the agent)

These require GitHub-admin and PyPI-account actions. See
`OneDrive/Trapezia/PyPI-and-TestPyPI-setup-runbook.md`.

- [ ] **Step 7.1: Merge the branch** — open a PR `feat/psse-utils` → `master`, let CI pass, merge.

- [ ] **Step 7.2: Rename the GitHub repo** `flowgate_key_facilities` → `psse_utils`
  (owner `cadvena`: GitHub Settings → Rename, or `gh repo rename psse_utils -R ppsyOps/flowgate_key_facilities`).
  Then locally: `git remote set-url origin https://github.com/ppsyOps/psse_utils.git`,
  rename the local clone folder, and recreate the venv with stdlib `python -m venv`.

- [ ] **Step 7.3: Add the `psse-utils` pending publishers** on PyPI and TestPyPI —
  Project `psse-utils`, Owner `ppsyOps`, **Repo `psse_utils`**, Workflow `publish.yml`,
  Env `pypi` / `testpypi`. (GitHub environments `pypi`/`testpypi` already exist on the repo.)

---

## Phase 8 — Publish

- [ ] **Step 8.1: Dispatch the publish workflow**

`gh workflow run publish.yml --ref master --repo ppsyOps/psse_utils`
(Manual dispatch — a `cd.yml`/token-created release can't trigger it.)

- [ ] **Step 8.2: TestPyPI → verify → approve PyPI gate**

Build → TestPyPI publishes automatically; verify
`pip install --pre --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ psse-utils`
in a clean venv. Then approve the `pypi` deployment (reviewer `cadvena`) to publish to real PyPI.

- [ ] **Step 8.3: Confirm + clean up**

`pip install --pre psse-utils` from real PyPI; `flowgate-key-facilities --help` works.
Then **yank** the orphaned `flowgate-key-facilities 0.1.0b1` on PyPI (project → Manage → yank),
since its functionality now ships in `psse-utils`.

---

## Self-review notes

- **Spec coverage:** repurpose (P1,P7.2) · src layout (P1,P2) · per-script command (P2.1 scripts) · logic/CLI split (P6) · CalVer `2026.6.0b1` (P1.2,P2.1) · keep flowgate command+module names (P2.1,P1.1) · script-prefixed tests (P3) · `psse-model-util` dep + extras note (P2.1, README P4) · reuse publish/ci/envs (P2.2, P7) · yank flowgate beta (P8.3) · PyPI publisher (P7.3). ✔
- **Placeholders:** none — every code/edit step shows the content. The only "optional" is Phase 6, explicitly marked.
- **Consistency:** distribution `psse-utils`, import `psse_utils`, module `psse_utils.flowgate_key_facilities`, command `flowgate-key-facilities`, version `2026.6.0b1`, repo `ppsyOps/psse_utils` — used uniformly across tasks.
