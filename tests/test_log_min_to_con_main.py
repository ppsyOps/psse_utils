"""End-to-end tests for psse_utils.log_min_to_con.main().

main() runs the full pipeline in-process (read the mini log -> aggregate
outages across snapshots -> write the .con file and, unless disabled, the
CSV tables) and returns an exit code. Uses tests/data/log_min_sample.txt
(see conftest.py / test_log_min_to_con_logic.py for its contents).
"""
from __future__ import annotations

import psse_utils.log_min_to_con as log_min_to_con
from psse_utils.log_min_to_con import main


def _run(log_file, out_dir, *extra_args):
    argv = ["--log-filepath", str(log_file), "--out-dir", str(out_dir), "--no-open-con-file", *extra_args]
    return main(argv)


def test_main_happy_path_writes_con_file(log_min_file, tmp_path):
    rc = _run(log_min_file, tmp_path)
    assert rc == 0
    con_file = tmp_path / "log_min_contingencies.con"
    assert con_file.exists()
    text = con_file.read_text()
    assert "FAKEGEN A1" in text
    assert "FAKEGEN B1" in text
    assert "FAKEBUS A" in text
    assert "FAKEXFMR_3W" in text


def test_main_writes_cumulative_csvs(log_min_file, tmp_path):
    rc = _run(log_min_file, tmp_path)
    assert rc == 0
    assert (tmp_path / "log_min_gen_cons.csv").exists()
    assert (tmp_path / "log_min_branch_cons.csv").exists()
    assert (tmp_path / "log_min_3-winding_cons.csv").exists()

    gen_csv = (tmp_path / "log_min_gen_cons.csv").read_text()
    assert "FAKEGEN A1" in gen_csv
    assert "FAKEGEN B1" in gen_csv


def test_main_writes_diff_csvs_between_snapshots(log_min_file, tmp_path):
    rc = _run(log_min_file, tmp_path)
    assert rc == 0
    gen_diff = tmp_path / "gen_outage_diffs_000-001.csv"
    assert gen_diff.exists()
    diff_text = gen_diff.read_text()
    # Only the gen outage newly added in snapshot 2 should appear in the diff.
    assert "FAKEGEN B1" in diff_text
    assert "FAKEGEN A1" not in diff_text

    assert (tmp_path / "branch_outage_diffs_000-001.csv").exists()
    assert (tmp_path / "3winding_outage_diffs_000-001.csv").exists()


def test_main_no_csv_skips_csv_files(log_min_file, tmp_path):
    rc = _run(log_min_file, tmp_path, "--no-csv")
    assert rc == 0
    assert (tmp_path / "log_min_contingencies.con").exists()
    assert not (tmp_path / "log_min_gen_cons.csv").exists()
    assert not (tmp_path / "gen_outage_diffs_000-001.csv").exists()


def test_main_missing_log_file_returns_nonzero(tmp_path, capsys):
    rc = _run(tmp_path / "does_not_exist.txt", tmp_path)
    assert rc != 0
    assert "not found" in capsys.readouterr().err


def test_main_empty_log_returns_nonzero(tmp_path, capsys):
    empty_log = tmp_path / "empty.txt"
    empty_log.write_text("no snapshot markers here\n")
    rc = _run(empty_log, tmp_path)
    assert rc != 0
    assert "No snapshots found" in capsys.readouterr().err


def test_main_default_out_dir_is_alongside_log_file(log_min_file, tmp_path):
    copy = tmp_path / "log_min_sample.txt"
    copy.write_text(log_min_file.read_text(encoding="utf-8"), encoding="utf-8")
    rc = main(["--log-filepath", str(copy), "--no-open-con-file"])
    assert rc == 0
    assert (tmp_path / "log_min_contingencies.con").exists()


def test_main_open_con_file_calls_the_platform_opener(log_min_file, tmp_path, monkeypatch):
    """Default behavior (no --no-open-con-file) opens the .con file; verify
    the call without actually launching a program."""
    opened = []
    monkeypatch.setattr(log_min_to_con.os, "startfile", lambda p: opened.append(p), raising=False)
    argv = ["--log-filepath", str(log_min_file), "--out-dir", str(tmp_path)]
    rc = main(argv)
    assert rc == 0
    assert opened == [str(tmp_path / "log_min_contingencies.con")]


def test_open_file_prints_notice_when_startfile_unsupported(tmp_path, monkeypatch, capsys):
    monkeypatch.delattr(log_min_to_con.os, "startfile", raising=False)
    log_min_to_con._open_file(tmp_path / "some.con")
    assert "unsupported on this platform" in capsys.readouterr().out
