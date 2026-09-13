"""Unit tests for the parsing/aggregation logic in psse_utils.log_min_to_con.

Uses tests/data/log_min_sample.txt: a synthetic, CSV-formatted two-snapshot
TARA mini log (see conftest.py for details). Snapshot 1 has one gen outage,
one branch outage, and one 3-winding outage. Snapshot 2 repeats the same
branch outage, adds a second gen outage, and has no 3-winding outages.
"""
from __future__ import annotations

import pandas as pd

from psse_utils.log_min_to_con import (
    build_contingency_data,
    find_unique_records,
    get_lines_between_markers,
    parse_3w_outages,
    parse_branch_outages,
    parse_gen_outages,
    read_log,
    write_con_file,
)


def test_read_log_splits_into_two_snapshots(log_min_file):
    log = read_log(log_min_file)
    assert len(log) == 2


def test_get_lines_between_markers_returns_empty_when_marker_missing():
    assert get_lines_between_markers(["a", "b", "c"], "nope", "also nope") == []


def test_parse_gen_outages_finds_the_outage_row(log_min_file):
    log = read_log(log_min_file)
    contingencies, df = parse_gen_outages(log[0])
    assert len(contingencies) == 1
    assert "FAKEGEN A1" in next(iter(contingencies))
    assert list(df["bus_num"]) == ["100001"]


def test_parse_branch_outages_finds_the_open_row(log_min_file):
    log = read_log(log_min_file)
    contingencies, df = parse_branch_outages(log[0])
    assert len(contingencies) == 1
    assert "FAKEBUS A" in next(iter(contingencies))
    assert list(df["to_bus_num"]) == ["200002"]


def test_parse_3w_outages_finds_the_open_row(log_min_file):
    log = read_log(log_min_file)
    contingencies, df = parse_3w_outages(log[0])
    assert len(contingencies) == 1
    assert "FAKEXFMR_3W" in next(iter(contingencies))


def test_parse_3w_outages_empty_section_returns_nothing(log_min_file):
    """Snapshot 2 has no 3-winding changes; the section between markers is empty."""
    log = read_log(log_min_file)
    contingencies, df = parse_3w_outages(log[1])
    assert contingencies == set()
    assert df.empty


def test_find_unique_records_returns_symmetric_diff():
    df1 = pd.DataFrame({"a": [1, 2]})
    df2 = pd.DataFrame({"a": [2, 3]})
    diff = find_unique_records(df1, df2)
    assert sorted(diff["a"]) == [1, 3]


def test_build_contingency_data_merges_across_snapshots(log_min_file):
    log = read_log(log_min_file)
    gen_cons, branch_cons, three_w_cons, gen_dfs, branch_dfs, three_w_dfs = build_contingency_data(log)

    # Snapshot 1 has 1 gen outage, snapshot 2 adds a second -> 2 total.
    assert len(gen_cons) == 2
    # Same branch outage repeats in both snapshots -> deduplicated to 1.
    assert len(branch_cons) == 1
    # Only snapshot 1 has a 3-winding outage.
    assert len(three_w_cons) == 1

    assert len(gen_dfs) == len(branch_dfs) == len(three_w_dfs) == 2
    assert len(gen_dfs[0]) == 1
    assert len(gen_dfs[1]) == 2


def _fixed_width_line(length, **spans):
    """Build a fixed-width line: spans maps a name to (start_col, text)."""
    chars = [" "] * length
    for start, text in spans.values():
        chars[start:start + len(text)] = list(text)
    return "".join(chars)


def test_read_log_accepts_raw_string_content(log_min_file):
    """read_log also accepts already-read file content (not just a Path)."""
    content = log_min_file.read_text(encoding="utf-8")
    log = read_log(content)
    assert len(log) == 2


def test_parse_gen_outages_reads_fixed_width_format():
    line = _fixed_width_line(
        95,
        bus_num=(0, "300001"),
        bus_name=(7, "FAKEGEN C1"),
        voltage=(19, "13.8"),
        gen_id=(35, "3P"),
        outage_type=(82, "Outage"),
    )
    snapshot = [
        "0",
        "========= Report on generator status/dispatch changes for the period FAKE (EST)",
        "From the Base Case",
        " Bus# Bus Name     Volt Area Zone  ID  BasCasMW     BasCsSta      PMin      PMax     Type",
        line,
        "========= Total 1 Generators changed status",
    ]
    contingencies, df = parse_gen_outages(snapshot)
    assert len(contingencies) == 1
    assert list(df["bus_num"]) == ["300001"]
    assert list(df["gen_id"]) == ["3P"]


def test_parse_branch_outages_reads_fixed_width_format():
    line = _fixed_width_line(
        120,
        from_bus_num=(0, "400001"),
        from_bus_name=(7, "FAKEBUS C"),
        from_v=(20, "138"),
        to_bus_num=(35, "400002"),
        to_bus_name=(42, "FAKEBUS D"),
        to_v=(55, "138"),
        ckt=(71, "1"),
        outage_type=(109, "Open"),
    )
    snapshot = [
        "0",
        "========= Report on branch status changes for the period FAKE (EST)",
        "From the Base Case",
        " Fr Bus Fr Name      Volt FrAr FrZn  To Bus To Name      Volt ToAr ToZn CKT",
        line,
        "========= 1 Branches changed status",
    ]
    contingencies, df = parse_branch_outages(snapshot)
    assert len(contingencies) == 1
    assert list(df["from_bus_num"]) == ["400001"]
    assert list(df["to_bus_num"]) == ["400002"]


def test_parse_3w_outages_reads_fixed_width_format():
    line = _fixed_width_line(
        170,
        xfrmr_name=(0, "FAKEXFMR_3W_B"),
        i_num=(43, "500001"),
        i_name=(50, "FAKE W1B"),
        i_v=(64, "230"),
        j_num=(69, "500002"),
        j_name=(75, "FAKE W2B"),
        j_v=(89, "345"),
        k_num=(93, "500003"),
        k_name=(100, "FAKE W3B"),
        k_v=(113, "23.0"),
        ckt=(144, "1"),
        outage_type=(150, "Open"),
    )
    snapshot = [
        "0",
        "========= Report on 3-winding transformers status changes for the period FAKE (EST)",
        "From the Base Case",
        " TranName Bus# W1BusNam W1_V Bus# W2BusNam W2_V Bus# W3BusNam W3_V Bus# Star NmVl CKT Type",
        line,
        "========= 1 3-winding transformers changed status",
    ]
    contingencies, df = parse_3w_outages(snapshot)
    assert len(contingencies) == 1
    assert list(df["i_num"]) == ["500001"]
    assert list(df["k_num"]) == ["500003"]


def test_write_con_file_writes_sorted_sections(tmp_path):
    gen = {"Contingency 'B Gen'\nEND", "Contingency 'A Gen'\nEND"}
    branch = {"Contingency 'X Branch'\nEND"}
    three_w = {"Contingency 'Y 3-winding'\nEND"}

    fp = write_con_file(tmp_path / "out.con", gen, branch, three_w)
    text = fp.read_text()

    assert "// ========= Generator Contingencies" in text
    assert "// ========= Branch Contingencies" in text
    assert "// ========= 3-Winding Xfrmr Contingencies" in text
    # Gen contingencies are sorted alphabetically: 'A Gen' before 'B Gen'.
    assert text.index("'A Gen'") < text.index("'B Gen'")
