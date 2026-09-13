# psse-utils

A collection of small PSS/E utility scripts built on
[`psse-model-util`](https://pypi.org/project/psse-model-util/). Instead of a new
repo + PyPI project per script, scripts live here and ship as one package.

## Installation

~~~
pip install --pre psse-utils
~~~

`--pre` is required while this package (and `psse-model-util`) are pre-releases.

## Scripts

### `flowgate-key-facilities`

Identify the **key facilities** for a set of PSS/E flowgates — the equipment
whose outage would most likely have a high impact on those flowgates. For each
flowgate in a `.mon` file, it keeps AC lines in a kV range and generators above a
PMax, all within `n` buses (hops) of the flowgate's elements, and writes the
results to CSVs.

~~~
flowgate-key-facilities \
  --mon flowgates.mon --raw Model.raw \
  --areas 1 2 3 --sc SCA --out-dir outputs/
~~~

Full options: `flowgate-key-facilities --help`. Outputs `branches.csv`,
`generators.csv`, `transformers_3w.csv`, `unresolved.csv` in `--out-dir`.

### `filter-taralog-notcnv`

Filter PSS/E `.con` contingency files down to only the contingencies a TARA/
PowerGEM `taralog.txt` reports as non-convergent (`NotCnv`).

~~~
filter-taralog-notcnv --taralog taralog.txt --con "*.con" --out-dir out/
~~~

`--con` accepts one or more files or glob patterns (globs are expanded by the
script itself, so `*.con` works the same on Windows and Linux/macOS). Each
matched `.con` file is written to `<out-dir>/<stem>-NotCnv<suffix>` (or
alongside the input if `--out-dir` is omitted), containing only the
contingency blocks whose name matches a NotCnv contingency found anywhere in
`taralog.txt` (pooled across all repeated report sections in the log).

Full options: `filter-taralog-notcnv --help`.

### `log-min-to-con`

Build a PSS/E contingency (`.con`) file from the outages reported in a TARA/
PowerGEM "mini log" file (e.g. `log_hourly-min.txt`). Every generator, branch,
or 3-winding transformer outage found in any snapshot becomes one
contingency; duplicates across snapshots are merged.

~~~
log-min-to-con --log-filepath log_hourly-min.txt --out-dir out/ --no-open-con-file
~~~

Writes `log_min_contingencies.con` plus (unless `--no-csv`) cumulative outage
tables (`log_min_gen_cons.csv`, `log_min_branch_cons.csv`,
`log_min_3-winding_cons.csv`) and, for each pair of consecutive snapshots, a
diff CSV showing which outages appeared or disappeared between them
(`gen_outage_diffs_<i-1>-<i>.csv`, etc.).

Full options: `log-min-to-con --help`.

## Adding a script

1. Create `src/psse_utils/<name>.py` with the **logic as importable functions**
   plus a thin `main(argv=None) -> int` that parses args and calls them (keeping
   logic separate from the CLI leaves room for a future TUI/web UI).
2. **No intra-package imports.** A script module may depend on stdlib and
   third-party packages (e.g. `pandas`, `psse_model_util`) but must never
   import another `psse_utils.<script>` module. This keeps every script
   copy-paste portable: install its declared third-party dependencies and the
   single `.py` file runs standalone, without the rest of this repo.
3. Add a console command in `pyproject.toml`:
   `[project.scripts]` → `your-command = "psse_utils.<name>:main"`.
4. Add tests `tests/test_<name>_*.py` (script-prefixed).
5. Put any heavy/extra dependencies behind an extra in `[project.optional-dependencies]`.

## Development

~~~
python -m venv .venv
.venv\Scripts\python -m pip install --pre -e .
.venv\Scripts\python -m pip install pytest pytest-cov
.venv\Scripts\python -m pytest
~~~

Versioning is CalVer (`YYYY.M.micro`) from `src/psse_utils/__about__.py`.
Releases publish to PyPI via Trusted Publishing — see the team setup runbook and
`psse-model-util`'s `docs/PUBLISHING.md`.
