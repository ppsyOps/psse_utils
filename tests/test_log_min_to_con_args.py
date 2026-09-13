"""Unit tests for psse_utils.log_min_to_con._parse_args (the CLI contract).

Fast and fixture-free: assert required/optional arguments, defaults, and the
store_true/store_false toggle pairs.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from psse_utils.log_min_to_con import _parse_args


def test_required_arg_parses_into_expected_type():
    ns = _parse_args(["--log-filepath", "log_hourly-min.txt"])
    assert ns.log_filepath == Path("log_hourly-min.txt")
    assert ns.out_dir is None
    assert ns.write_csv_files is True
    assert ns.open_con_file is True


def test_missing_log_filepath_is_enforced():
    with pytest.raises(SystemExit):
        _parse_args([])


def test_out_dir_optional_override():
    ns = _parse_args(["--log-filepath", "log.txt", "--out-dir", "out"])
    assert ns.out_dir == Path("out")


def test_no_csv_disables_write_csv_files():
    ns = _parse_args(["--log-filepath", "log.txt", "--no-csv"])
    assert ns.write_csv_files is False


def test_no_open_con_file_disables_open_con_file():
    ns = _parse_args(["--log-filepath", "log.txt", "--no-open-con-file"])
    assert ns.open_con_file is False
