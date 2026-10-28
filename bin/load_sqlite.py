#!/usr/bin/env python3
# ============================================================
# Load bulk.nf results into SQLite (schema: docs/database_schema.md)
#
# Usage:
#   python load_sqlite.py <outdir> <database.db>
#       [--metadata-db warehouse.db --metadata-table bdq_metadata --metadata-key accession]
#       [--prefix ""]
#
# Reads:  <outdir>/samples/<id>/  main task (sample.json | failed.json)
#         <outdir>/is6110/<id>/   IS Sentinel task (issentinel.json | failed.json)
#
# Tables: isolate_metadata, samples, variant_calls, resistance_hits,
#         resistance_profile, quality_control, oxidative_damage,
#         is6110_status, is6110_candidates, is6110_junctions, failures
# Views:  v_profile, v_qc, v_pass_calls (rebuilt after every load)
#
# Idempotent: a result already loaded with the same finished_utc is
# skipped; a re-run sample replaces its rows. Each sample and task is
# one transaction, so an interrupted load never leaves a partial
# sample. Safe to run while bulk.nf is still running (only published
# directories are read).
# ============================================================

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

# Main task: table -> file in <outdir>/samples/<id>/
MAIN_FILES = {
    "variant_calls": "{s}.calls.tsv.gz",
    "resistance_hits": "{s}.resistance_hits.tsv",
    "resistance_profile": "{s}.resistance_profile.tsv",
    "quality_control": "{s}.qc.tsv",
    "oxidative_damage": "{s}.oxidative_damage.tsv",
}

# IS Sentinel task: table -> file in <outdir>/is6110/<id>/
IS_FILES = {
    "is6110_candidates": "{s}_is_candidates.csv",
    "is6110_junctions": "{s}_is_formatted.csv",
}

INDEXES = {
    "variant_calls": [("sample",), ("pos", "ref", "alt"), ("caller", "filter_status"), ("gene",)],
    "resistance_hits": [("sample",), ("drug", "variant")],
    "resistance_profile": [("sample", "drug"), ("drug", "phenotype")],
    "quality_control": [("sample",), ("section", "metric")],
    "oxidative_damage": [("sample",)],
    "is6110_candidates": [("sample",), ("chrom", "pos")],
    "is6110_junctions": [("sample",), ("chrom", "dsb_breakpoint_a")],
}

# Text columns that look numeric in some rows but must stay text
KEEP_TEXT = {"sample", "value", "ref", "alt", "variant", "info"}

# QC metrics in v_qc: (column, section, metric)
QC_VIEW = [
    ("mean_depth", "bwa", "mean_depth"),
    ("coverage_pct", "bwa", "coverage_pct"),
    ("mapped_pct", "bwa", "mapped_pct"),
    ("duplicates_pct", "bwa", "duplicates_pct"),
    ("n_low_cov_resistance_positions", "tbdr_rcov", "n_low_cov_positions"),
    ("lineage", "lineage", "LINEAGE"),
    ("bwa_status", "bwa", "status"),
    ("trimmomatic_status", "trimmomatic", "status"),
    ("fastqc_r1_status", "fastqc", "R1.status"),
    ("fastqc_r2_status", "fastqc", "R2.status"),
    ("ntm_status", "ntm", "status"),
    ("mix_infection_status", "mix_infection", "status"),
    ("mix_het_proportion", "mix_infection", "proportion"),
    ("oxidative_damage_status", "oxidative_damage", "status"),
]


def snake(col):
    """IS Sentinel headers ('DSB Breakpoint A', 'Dist. to Nearest') -> SQL names."""
    return re.sub(r"[^0-9a-z]+", "_", col.strip().lower()).strip("_")


def table_exists(con, name):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()


def ensure_schema(con, p):
    con.execute(f"""CREATE TABLE IF NOT EXISTS {p}samples (
        sample TEXT PRIMARY KEY, status TEXT, finished_utc TEXT, pipeline_commit TEXT,
        filter_mode TEXT, lofreq_min_af TEXT, who_catalogue TEXT, n_pass_hits INTEGER,
        meta_json TEXT)""")
    con.execute(f"""CREATE TABLE IF NOT EXISTS {p}is6110_status (
        sample TEXT PRIMARY KEY, status TEXT, finished_utc TEXT, method TEXT,
        n_candidates INTEGER, n_junctions INTEGER, meta_json TEXT)""")
    con.execute(f"""CREATE TABLE IF NOT EXISTS {p}failures (
        sample TEXT, task TEXT, status TEXT, step TEXT, exit_code INTEGER, reason TEXT,
        finished_utc TEXT, meta_json TEXT, PRIMARY KEY (sample, task))""")


def typed(df):
    """Numeric columns as numbers, everything else as text."""
    for col in df.columns:
        if col in KEEP_TEXT:
            continue
        filled = df[col] != ""
        num = pd.to_numeric(df[col].where(filled), errors="coerce")
        if filled.any() and num[filled].notna().all():
            df[col] = num
    return df


def append(con, table, path, sample, sep):
    if not path.exists():
        return
    df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
    if df.empty:
        return
    df.columns = [snake(c) for c in df.columns]
    if "sample" not in df.columns:
        df.insert(0, "sample", sample)
    if table.endswith("variant_calls"):
        # gene = everything before the HGVS type prefix (_c. _n. _p. _g. _m.)
        df.insert(df.columns.get_loc("nt_change"), "gene",
                  df["nt_change"].str.extract(r"^(.+?)_[cnpgm]\.", expand=False).fillna(""))
    typed(df).to_sql(table, con, if_exists="append", index=False)


def delete_rows(con, p, sample, tables):
    for t in tables:
        if table_exists(con, p + t):
            con.execute(f"DELETE FROM {p}{t} WHERE sample = ?", (sample,))


def record_failure(con, p, sample, task, meta):
    con.execute(f"INSERT OR REPLACE INTO {p}failures VALUES (?,?,?,?,?,?,?,?)",
                (sample, task, meta.get("status"), meta.get("step"), meta.get("exit_code"),
                 meta.get("reason"), meta.get("finished_utc"), json.dumps(meta)))


def load_main(con, p, d, s, meta):
    for t, pattern in MAIN_FILES.items():
        append(con, p + t, d / pattern.format(s=s), s, "\t")
    con.execute(f"INSERT INTO {p}samples VALUES (?,?,?,?,?,?,?,?,?)",
                (s, meta.get("status"), meta.get("finished_utc"), meta.get("pipeline_commit"),
                 meta.get("filter_mode"), meta.get("lofreq_min_af"), meta.get("who_catalogue"),
                 meta.get("n_pass_hits"), json.dumps(meta)))


def load_is(con, p, d, s, meta):
    for t, pattern in IS_FILES.items():
        append(con, p + t, d / pattern.format(s=s), s, ",")
    con.execute(f"INSERT INTO {p}is6110_status VALUES (?,?,?,?,?,?,?)",
                (s, meta.get("status"), meta.get("finished_utc"), meta.get("method"),
                 meta.get("n_candidates"), meta.get("n_junctions"), json.dumps(meta)))


# task -> (results subdir, done marker suffix, status table, data tables, loader)
TASKS = {
    "bulk": ("samples", "sample.json", "samples", list(MAIN_FILES), load_main),
    "issentinel": ("is6110", "issentinel.json", "is6110_status", list(IS_FILES), load_is),
}


def load_task(con, p, outdir, task):
    subdir, done_suffix, status_table, data_tables, loader = TASKS[task]
    root = outdir / subdir
    if not root.is_dir():
        return 0, 0, 0

    loaded = dict(con.execute(f"SELECT sample, finished_utc FROM {p}{status_table}"))
    loaded.update({s: t for s, t in con.execute(
        f"SELECT sample, finished_utc FROM {p}failures WHERE task = ?", (task,))})

    n_new = n_fail = n_skip = 0
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.endswith(".partial"):
            continue
        s = d.name
        done, failed = d / f"{s}.{done_suffix}", d / f"{s}.failed.json"
        if not done.exists() and not failed.exists():
            continue
        meta = json.loads((done if done.exists() else failed).read_text())
        if loaded.get(s) == meta.get("finished_utc"):
            n_skip += 1
            continue
        try:
            with con:
                delete_rows(con, p, s, data_tables + [status_table])
                con.execute(f"DELETE FROM {p}failures WHERE sample = ? AND task = ?", (s, task))
                if done.exists():
                    loader(con, p, d, s, meta)
                    n_new += 1
                else:
                    record_failure(con, p, s, task, meta)
                    n_fail += 1
        except Exception as e:
            print(f"[ERROR] {task} {s}: {e}", file=sys.stderr)
    return n_new, n_fail, n_skip


def load_metadata(con, p, db, table, key):
    """Snapshot of the isolate metadata table (replaced on every load)."""
    src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    df = pd.read_sql_query(f'SELECT * FROM "{table}"', src)
    src.close()
    df.insert(0, "sample", df[key])
    with con:
        con.execute(f"DROP TABLE IF EXISTS {p}isolate_metadata")
        df.to_sql(p + "isolate_metadata", con, index=False)
        con.execute(f"CREATE UNIQUE INDEX idx_{p}isolate_metadata_sample ON {p}isolate_metadata (sample)")
    return len(df)


def add_indexes(con, p):
    for t, idx in INDEXES.items():
        if not table_exists(con, p + t):
            continue
        for cols in idx:
            name = f"idx_{p}{t}_{'_'.join(cols)}"
            con.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {p}{t} ({', '.join(cols)})")


def rebuild_views(con, p):
    for v in ("v_profile", "v_qc", "v_pass_calls"):
        con.execute(f"DROP VIEW IF EXISTS {p}{v}")

    def qc_value(column):
        # numeric metrics are stored as text, some with a trailing "%"
        if column.endswith(("_pct", "_depth", "_positions", "_proportion")):
            return "CAST(REPLACE(value, '%', '') AS REAL)"
        return "value"

    if table_exists(con, p + "quality_control"):
        cols = ",\n  ".join(
            f"MAX(CASE WHEN section = '{s}' AND metric = '{m}' THEN {qc_value(c)} END) AS {c}"
            for c, s, m in QC_VIEW)
        con.execute(f"CREATE VIEW {p}v_qc AS SELECT sample,\n  {cols}\nFROM {p}quality_control GROUP BY sample")

    if table_exists(con, p + "resistance_profile"):
        drugs = [r[0] for r in con.execute(f"SELECT DISTINCT drug FROM {p}resistance_profile ORDER BY drug")]
        cols = ",\n  ".join(f"MAX(CASE WHEN drug = '{d}' THEN phenotype END) AS \"{d}\"" for d in drugs)
        con.execute(f"CREATE VIEW {p}v_profile AS SELECT sample,\n  {cols}\nFROM {p}resistance_profile GROUP BY sample")

    if table_exists(con, p + "variant_calls") and table_exists(con, p + "quality_control"):
        con.execute(f"""CREATE VIEW {p}v_pass_calls AS
            SELECT c.*, q.mean_depth, q.coverage_pct, q.lineage
            FROM {p}variant_calls c LEFT JOIN {p}v_qc q USING (sample)
            WHERE c.filter_status = 'PASS'""")


def main():
    ap = argparse.ArgumentParser(description="Load bulk.nf results into SQLite")
    ap.add_argument("outdir", type=Path)
    ap.add_argument("database", type=Path)
    ap.add_argument("--metadata-db", type=Path, help="SQLite file with the isolate metadata table")
    ap.add_argument("--metadata-table", default="bdq_metadata")
    ap.add_argument("--metadata-key", default="accession", help="column that matches the sample ID")
    ap.add_argument("--prefix", default="", help="table name prefix, e.g. brseqtb_ when loading into a shared database")
    args = ap.parse_args()
    p = args.prefix

    con = sqlite3.connect(args.database)
    con.execute("PRAGMA journal_mode=WAL")
    ensure_schema(con, p)

    if args.metadata_db:
        n = load_metadata(con, p, args.metadata_db, args.metadata_table, args.metadata_key)
        print(f"[OK] isolate_metadata: {n} rows from {args.metadata_db}:{args.metadata_table}")

    for task in TASKS:
        n_new, n_fail, n_skip = load_task(con, p, args.outdir, task)
        print(f"[OK] {task}: loaded {n_new}, failures {n_fail}, already up to date {n_skip}")

    with con:
        add_indexes(con, p)
        rebuild_views(con, p)
    con.close()


if __name__ == "__main__":
    main()
