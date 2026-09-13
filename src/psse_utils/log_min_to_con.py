"""Build a PSS/E contingency (.con) file from the outages reported in a TARA/
PowerGEM "mini log" file (e.g. log_hourly-min.txt, log_monthly-min.txt).

The log records one or more snapshots, each containing up to three sections:
generator status/dispatch changes, branch status changes, and 3-winding
transformer status changes. Every "Outage" (gen) or "Open" (branch/3-winding)
record found in any snapshot becomes one contingency; duplicates across
snapshots are merged.

Usage:
    python -m psse_utils.log_min_to_con --log-filepath log_hourly-min.txt
    log-min-to-con --log-filepath log_hourly-min.txt --out-dir out/ --no-open-con-file

Outputs (written to --out-dir, default: alongside the log file):
    log_min_contingencies.con        contingency definitions (PSS/E format)
    log_min_gen_cons.csv              final cumulative generator outage table
    log_min_branch_cons.csv           final cumulative branch outage table
    log_min_3-winding_cons.csv        final cumulative 3-winding outage table
    gen_outage_diffs_<i-1>-<i>.csv    outages that appeared/disappeared between
    branch_outage_diffs_<i-1>-<i>.csv  consecutive snapshots (one file per
    3winding_outage_diffs_<i-1>-<i>.csv snapshot boundary, omitted with 1 snapshot)

Sample conversion from log to contingency file (values below are illustrative,
not real system data):

     ========= Report on generator status/dispatch changes for the period 2025-09-07 06:00 to 2025-09-07 07:00(EST)
     From the Base Case
      Bus# Bus Name     Volt Area Zone  ID  BasCasMW     BasCsSta      PMin      PMax     Type  newSetPn  YYYY-MM-DD HH:MM  YYYY-MM-DD HH:MM
    200642 FAKEGEN#1    13.8  225 1733  1P       0.1            0    -210.0    -210.0   Outage       0.0  2025-04-24 00:00  2063-12-01 23:00
     ========= Total 1 Generators changed status

    // Contingency definition for generation
    Contingency 'FAKEGEN#1 13.8 kV 1P Gen'
        REMOVE UNIT 1P FROM BUS 200642    / Gen 200642  FAKEGEN#1  13.8 1P
    END

The log file uses two formats: the first interval is fixed-width text, and
every subsequent interval is CSV. Each section is auto-detected and parsed
using whichever format it's in.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import List, Tuple, Union

import pandas as pd

GEN_COLUMNS = ["bus_num", "bus_name", "voltage", "gen_id"]
BRANCH_COLUMNS = ["from_bus_num", "from_bus_name", "from_v", "to_bus_num", "to_bus_name", "to_v", "ckt"]
THREE_W_COLUMNS = ["xfrmr_name", "i_num", "i_name", "i_v", "j_num", "j_name", "j_v", "k_num", "k_name", "k_v", "ckt"]

SNAPSHOT_MARKER = "------------------ Creating snapshot "


def find_unique_records(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """Return the rows that appear in only one of df1/df2 (a symmetric diff)."""
    merged = pd.merge(df1, df2, how="outer", indicator=True)
    unique = merged[merged["_merge"] != "both"]
    return unique.drop(columns=["_merge"])


def read_log(filepath_or_content: Union[Path, str]) -> List[List[str]]:
    """Split a mini log file (or its already-read content) into one list of
    lines per snapshot."""
    if isinstance(filepath_or_content, Path) or "\n" not in filepath_or_content:
        with open(filepath_or_content, "r") as f:
            content = f.read()
    else:
        content = filepath_or_content

    snapshots = content.split(SNAPSHOT_MARKER)
    return [snapshot.split("\n") for snapshot in snapshots[1:]]


def get_lines_between_markers(log: List[str], marker1: str, marker2: str) -> List[str]:
    """Return the lines strictly between the first line containing marker1
    and the first subsequent line containing marker2. Returns [] if either
    marker is absent."""
    start_index = -1
    end_index = -1

    for i, line in enumerate(log):
        if marker1 in line:
            start_index = i
            break

    if start_index != -1:
        for i, line in enumerate(log[start_index + 1:]):
            if marker2 in line:
                end_index = start_index + 1 + i
                break

    if start_index != -1 and end_index != -1:
        return log[start_index + 1:end_index]
    return []


def parse_csv(log: List[str]) -> List[List[str]]:
    """Parse a list of CSV-formatted lines into a list of field lists."""
    return list(csv.reader(log))


def parse_gen_outages(log_lines: List[str]) -> Tuple[set, pd.DataFrame]:
    lines = get_lines_between_markers(
        log_lines,
        marker1="========= Report on generator status/dispatch changes for the period",
        marker2="Generators changed status",
    )
    contingencies = set()
    raw: List[List[str]] = []
    if len(lines) < 3:
        return contingencies, pd.DataFrame(columns=GEN_COLUMNS)
    if "," in lines[2]:
        lines = parse_csv(lines)

    for line in lines:
        if not line:
            continue
        if isinstance(line, list):
            try:
                outage_type = line[10].strip().lower()
            except IndexError:
                outage_type = ""
        else:
            outage_type = line[82:91].strip().lower()
        if outage_type != "outage":
            continue
        if isinstance(line, list):
            bus_num = line[0].strip()
            bus_name = line[1].strip()
            voltage = line[2].strip()
            gen_id = line[5].strip()
        else:
            bus_num = line[0:6].strip()
            bus_name = line[7:19].strip()
            voltage = line[19:25].strip()
            gen_id = line[35:39].strip()
        contingency = (
            f"Contingency '{bus_name} {voltage} kV {gen_id} Gen'"
            f"\n    REMOVE UNIT {gen_id} FROM BUS {bus_num}    "
            f"/ Gen {bus_num}  {bus_name}  {voltage} {gen_id}"
            f"\nEND"
        )
        contingencies.add(contingency)
        raw.append([bus_num, bus_name, voltage, gen_id])

    return contingencies, pd.DataFrame(raw, columns=GEN_COLUMNS)


def parse_branch_outages(log_lines: List[str]) -> Tuple[set, pd.DataFrame]:
    lines = get_lines_between_markers(
        log_lines,
        marker1="========= Report on branch status changes for the period",
        marker2="Branches changed status",
    )
    contingencies = set()
    raw: List[List[str]] = []
    if len(lines) < 3:
        return contingencies, pd.DataFrame(columns=BRANCH_COLUMNS)
    if "," in lines[2]:
        lines = parse_csv(lines)

    for line in lines:
        if not line:
            continue
        if isinstance(line, list):
            try:
                outage_type = line[16].strip().lower()
            except IndexError:
                outage_type = ""
        else:
            outage_type = line[109:117].strip().lower()
        if outage_type != "open":
            continue
        if isinstance(line, list):
            from_bus_num = line[0].strip()
            from_bus_name = line[1].strip()
            from_v = line[3].strip()
            to_bus_num = line[5].strip()
            to_bus_name = line[6].strip()
            to_v = line[7].strip()
            ckt = line[10].strip()
        else:
            from_bus_num = line[0:7].strip()
            from_bus_name = line[7:20].strip()
            from_v = line[20:25].strip()
            to_bus_num = line[35:41].strip()
            to_bus_name = line[42:55].strip()
            to_v = line[55:60].strip()
            ckt = line[71:75].strip()
        contingency = (
            f"Contingency '{from_bus_name} {from_v} kV - {to_bus_name} {to_v} kV {ckt} Branch'"
            f"\n    OPEN BRANCH FROM BUS {from_bus_num} TO BUS {to_bus_num}  CKT {ckt}  "
            f"/ Branch {from_bus_num} {from_bus_name} {from_v} kV to {to_bus_num} "
            f"{to_bus_name} {to_v} kV {ckt}"
            f"\nEND"
        )
        contingencies.add(contingency)
        raw.append([from_bus_num, from_bus_name, from_v, to_bus_num, to_bus_name, to_v, ckt])

    return contingencies, pd.DataFrame(raw, columns=BRANCH_COLUMNS)


def parse_3w_outages(log_lines: List[str]) -> Tuple[set, pd.DataFrame]:
    lines = get_lines_between_markers(
        log_lines,
        marker1="========= Report on 3-winding transformers status changes for the period",
        marker2="3-winding transformers changed statu",
    )
    contingencies = set()
    raw: List[List[str]] = []
    if len(lines) < 3:
        return contingencies, pd.DataFrame(columns=THREE_W_COLUMNS)
    if "," in lines[2]:
        lines = parse_csv(lines)

    for line in lines:
        if not line:
            continue
        if isinstance(line, list):
            try:
                outage_type = line[14].strip().lower()
            except IndexError:
                outage_type = ""
        else:
            outage_type = line[150:159].strip().lower()
        if outage_type != "open":
            continue
        if isinstance(line, list):
            xfrmr_name = line[0].strip()
            i_num = line[1].strip()
            i_name = line[2].strip()
            i_v = line[3].strip()
            j_num = line[4].strip()
            j_name = line[5].strip()
            j_v = line[6].strip()
            k_num = line[7].strip()
            k_name = line[8].strip()
            k_v = line[9].strip()
            ckt = line[13].strip()
        else:
            xfrmr_name = line[:43].strip()
            i_num = line[43:50].strip()
            i_name = line[50:64].strip()
            i_v = line[64:68].strip()
            j_num = line[69:75].strip()
            j_name = line[75:88].strip()
            j_v = line[89:93].strip()
            k_num = line[93:100].strip()
            k_name = line[100:113].strip()
            k_v = line[113:118].strip()
            ckt = line[144:147].strip()
        contingency = (
            f"Contingency '{xfrmr_name} 3-winding'"
            f"\n    OPEN BRANCH FROM BUS {i_num} TO BUS {j_num} TO BUS {k_num}  CKT {ckt}  "
            f"/ 3-winding: {i_num} {i_name} {i_v} kV "
            f"| {j_num} {j_name} {j_v} kV "
            f"| {k_num} {k_name} {k_v} kV, CKT: {ckt}"
            f"\nEND"
        )
        contingencies.add(contingency)
        raw.append([xfrmr_name, i_num, i_name, i_v, j_num, j_name, j_v, k_num, k_name, k_v, ckt])

    return contingencies, pd.DataFrame(raw, columns=THREE_W_COLUMNS)


def build_contingency_data(
    log: List[List[str]],
) -> Tuple[set, set, set, List[pd.DataFrame], List[pd.DataFrame], List[pd.DataFrame]]:
    """Parse every snapshot once, returning the merged (deduplicated)
    contingency sets plus, for each snapshot, the cumulative outage table up
    to and including that snapshot (used both for the final CSVs and to
    diff consecutive snapshots)."""
    gen_contingencies: set = set()
    branch_contingencies: set = set()
    three_w_contingencies: set = set()
    gen_df = pd.DataFrame(columns=GEN_COLUMNS)
    branch_df = pd.DataFrame(columns=BRANCH_COLUMNS)
    three_w_df = pd.DataFrame(columns=THREE_W_COLUMNS)
    gen_dfs: List[pd.DataFrame] = []
    branch_dfs: List[pd.DataFrame] = []
    three_w_dfs: List[pd.DataFrame] = []

    for snapshot_log in log:
        cons, df = parse_gen_outages(snapshot_log)
        gen_contingencies |= cons
        gen_df = pd.concat([gen_df, df], ignore_index=True).drop_duplicates().reset_index(drop=True)
        gen_dfs.append(gen_df)

        cons, df = parse_branch_outages(snapshot_log)
        branch_contingencies |= cons
        branch_df = pd.concat([branch_df, df], ignore_index=True).drop_duplicates().reset_index(drop=True)
        branch_dfs.append(branch_df)

        cons, df = parse_3w_outages(snapshot_log)
        three_w_contingencies |= cons
        three_w_df = pd.concat([three_w_df, df], ignore_index=True).drop_duplicates().reset_index(drop=True)
        three_w_dfs.append(three_w_df)

    return gen_contingencies, branch_contingencies, three_w_contingencies, gen_dfs, branch_dfs, three_w_dfs


def write_con_file(
    filepath: Union[Path, str],
    gen_contingencies: set,
    branch_contingencies: set,
    three_w_contingencies: set,
) -> Path:
    """Write sorted contingency definitions (PSS/E .con format) to filepath."""
    filepath = filepath if isinstance(filepath, Path) else Path(filepath)

    gen_contingencies = sorted(gen_contingencies)
    branch_contingencies = sorted(branch_contingencies)
    three_w_contingencies = sorted(three_w_contingencies)

    with open(filepath, "w") as f:
        f.write("// ========= Generator Contingencies\n")
        f.write("\n".join(gen_contingencies))
        f.write("\n\n// ========= Branch Contingencies\n")
        f.write("\n".join(branch_contingencies))
        f.write("\n\n// ========= 3-Winding Xfrmr Contingencies\n")
        f.write("\n".join(three_w_contingencies))

    return filepath


def write_cumulative_csvs(
    out_dir: Path, gen_df: pd.DataFrame, branch_df: pd.DataFrame, three_w_df: pd.DataFrame
) -> List[Path]:
    """Write the final (all-snapshots) outage tables to CSV. Returns the
    written paths."""
    written = []
    for df, name in (
        (gen_df, "log_min_gen_cons.csv"),
        (branch_df, "log_min_branch_cons.csv"),
        (three_w_df, "log_min_3-winding_cons.csv"),
    ):
        if not df.empty:
            df = df.sort_values(by=df.columns[0])
        fp = out_dir / name
        df.to_csv(fp, index=False)
        print(f"Wrote {fp}")
        written.append(fp)
    return written


def write_diff_csvs(
    out_dir: Path,
    gen_dfs: List[pd.DataFrame],
    branch_dfs: List[pd.DataFrame],
    three_w_dfs: List[pd.DataFrame],
) -> List[Path]:
    """Write one CSV per snapshot boundary showing outages that
    appeared/disappeared between consecutive (cumulative) snapshots. Returns
    the written paths."""
    written = []
    for i in range(1, len(gen_dfs)):
        for dfs, prefix in (
            (gen_dfs, "gen_outage_diffs"),
            (branch_dfs, "branch_outage_diffs"),
            (three_w_dfs, "3winding_outage_diffs"),
        ):
            diff = find_unique_records(dfs[i - 1], dfs[i])
            fp = out_dir / f"{prefix}_{i - 1:03d}-{i:03d}.csv"
            diff.to_csv(fp, index=False)
            print(f"Wrote {fp}")
            written.append(fp)
    return written


def _open_file(path: Path) -> None:
    """Open path in its default program, if the platform supports it."""
    opener = getattr(os, "startfile", None)
    if opener is None:
        print(f"(Not opening {path} automatically; unsupported on this platform.)")
        return
    opener(str(path))


def _parse_args(argv: List[str] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--log-filepath", required=True, type=Path,
        help="Path to the TARA mini log file (e.g. log_hourly-min.txt).",
    )
    p.add_argument(
        "--out-dir", type=Path, default=None,
        help="Output directory (default: alongside the log file).",
    )
    p.add_argument(
        "--write-csv-files", action="store_true", default=True,
        help="Write contingency and diff data to CSV files, in addition to the .con file (default: on).",
    )
    p.add_argument(
        "--no-csv", action="store_false", dest="write_csv_files",
        help="Do not write CSV files (only write the .con file).",
    )
    p.add_argument(
        "--open-con-file", action="store_true", default=True,
        help="Open the .con file in the default program after writing it (default: on).",
    )
    p.add_argument(
        "--no-open-con-file", action="store_false", dest="open_con_file",
        help="Do not open the .con file after writing it.",
    )
    return p.parse_args(argv)


def main(argv: List[str] = None) -> int:
    args = _parse_args(argv)
    log_filepath: Path = args.log_filepath

    if not log_filepath.is_file():
        print(f'Log file not found: "{log_filepath}"', file=sys.stderr)
        return 1

    out_dir: Path = args.out_dir or log_filepath.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    log = read_log(log_filepath)
    if not log:
        print(f'No snapshots found in "{log_filepath}" (expected "{SNAPSHOT_MARKER.strip()}" markers).',
              file=sys.stderr)
        return 1

    (gen_contingencies, branch_contingencies, three_w_contingencies,
     gen_dfs, branch_dfs, three_w_dfs) = build_contingency_data(log)

    con_filepath = out_dir / "log_min_contingencies.con"
    write_con_file(con_filepath, gen_contingencies, branch_contingencies, three_w_contingencies)
    print(
        f"Wrote {len(gen_contingencies)} gen, {len(branch_contingencies)} branch, "
        f"{len(three_w_contingencies)} 3-winding contingencies to {con_filepath}"
    )

    if args.write_csv_files:
        write_cumulative_csvs(out_dir, gen_dfs[-1], branch_dfs[-1], three_w_dfs[-1])
        write_diff_csvs(out_dir, gen_dfs, branch_dfs, three_w_dfs)

    if args.open_con_file:
        _open_file(con_filepath)

    return 0


if __name__ == "__main__":
    sys.exit(main())
