"""Shared fixtures for the psse_utils CLI tests.

Fixtures live in tests/data/:
- Model_1.raw, synthetic_flowgates.mon: copies of the psse_model_util test
  fixtures, used by flowgate_key_facilities tests. The .mon defines four
  flowgates: three under security coordinator ``SCA`` and one under ``SCB``.
  Model_1.raw spans PSS/E areas 1-5.
- taralog_sample.txt, sample_a.con, sample_b.con: synthetic (anonymized,
  shortened) PowerGEM/TARA log and PSS/E .con fixtures used by
  filter_taralog_notcnv tests. None of these contain real system data.
- log_min_sample.txt: a synthetic, CSV-formatted TARA "mini log" with two
  snapshots, used by log_min_to_con tests. Fabricated bus/gen/branch/xfrmr
  names; not real system data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# src/ layout: make psse_utils importable even without an editable install
# (fallback for fresh checkouts; the editable install normally handles it).
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

DATA_DIR = Path(__file__).resolve().parent / "data"


@pytest.fixture(scope="session")
def mon_file() -> Path:
    return DATA_DIR / "synthetic_flowgates.mon"


@pytest.fixture(scope="session")
def raw_file() -> Path:
    return DATA_DIR / "Model_1.raw"


@pytest.fixture(scope="session")
def taralog_file() -> Path:
    return DATA_DIR / "taralog_sample.txt"


@pytest.fixture(scope="session")
def con_file_a() -> Path:
    return DATA_DIR / "sample_a.con"


@pytest.fixture(scope="session")
def con_file_b() -> Path:
    return DATA_DIR / "sample_b.con"


@pytest.fixture(scope="session")
def log_min_file() -> Path:
    return DATA_DIR / "log_min_sample.txt"
