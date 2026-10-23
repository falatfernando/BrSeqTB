#!/usr/bin/env python3
# ============================================================
# Load bulk.nf results into SQLite
#
# Usage: python load_sqlite.py <outdir> <database.db> [--prefix brseqtb_]
# Reads:  <outdir>/samples/<id>/  (written by bulk.nf)
#
# Tables (prefix + name):
#   samples             one row per finished sample (sample.json)
#   calls               every call of every caller, catalogue or not
#   resistance_hits     final per-isolate table (catalogue matches)
#   resistance_profile  phenotype + annotation per sample x drug
#   qc                  QC metrics, long format
#   oxidative_damage    calls removed by the damage guard
#   failures            samples recorded as failed / bad input
#
# Idempotent: a sample already loaded with the same finished_utc is
# skipped; a re-run sample replaces all of its rows. Each sample is
# one transaction, so an interrupted load never leaves a partial
# sample. Safe to run repeatedly while bulk.nf is still running
# (only published directories are read).
# ============================================================

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

TABLE_FILES = {
    "calls": "{s}.calls.tsv.gz",
    "resistance_hits": "{s}.resistance_hits.tsv",
    "resistance_profile": "{s}.resistance_profile.tsv",
    "qc": "{s}.qc.tsv",
    "oxidative_damage": "{s}.oxidative_damage.tsv",
}

INDEXES = {
    "calls": [("sample",), ("pos", "ref", "alt"), ("caller", "filter_status")],
    "resistance_hits": [("sample",), ("drug", "variant")],
    "resistance_profile": [("sample", "drug"), ("drug", "phenotype")],
    "qc": [("sample",), ("section", "metric")],
    "oxidative_damage": [("sample",)],
}


def ensure_schema(con, p):
    con.execute(f"""CREATE TABLE IF NOT EXISTS {p}samples (
        sample TEXT PRIMARY KEY, status TEXT, finished_utc TEXT, pipeline_commit TEXT,
        filter_mode TEXT, lofreq_min_af TEXT, who_catalogue TEXT, n_pass_hits INTEGER,
        meta_json TEXT)""")
    con.execute(f"""CREATE TABLE IF NOT EXISTS {p}failures (
        sample TEXT PRIMARY KEY, status TEXT, step TEXT, exit_code INTEGER, reason TEXT,
        finished_utc TEXT, meta_json TEXT)""")


def table_exists(con, name):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()


def add_indexes(con, p):
    for t, idx in INDEXES.items():
        if not table_exists(con, p + t):
            continue
        for cols in idx:
            name = f"idx_{p}{t}_{'_'.join(cols)}"
            con.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {p}{t} ({', '.join(cols)})")


def delete_sample(con, p, sample):
    for t in list(TABLE_FILES) + ["samples", "failures"]:
        if table_exists(con, p + t):
            con.execute(f"DELETE FROM {p}{t} WHERE sample = ?", (sample,))


def load_done(con, p, d, sample, meta):
    for t, pattern in TABLE_FILES.items():
        f = d / pattern.format(s=sample)
        if not f.exists():
            continue
        df = pd.read_csv(f, sep="\t", dtype=str, keep_default_na=False)
        if df.empty:
            continue
        # numeric columns as numbers, everything else as text
        for col in df.columns:
            num = pd.to_numeric(df[col].replace("", None), errors="coerce")
            if num.notna().sum() == (df[col] != "").sum() and col not in ("sample", "value", "ref", "alt"):
                df[col] = num
        df.to_sql(p + t, con, if_exists="append", index=False)
    con.execute(
        f"INSERT INTO {p}samples VALUES (?,?,?,?,?,?,?,?,?)",
        (sample, meta.get("status"), meta.get("finished_utc"), meta.get("pipeline_commit"),
         meta.get("filter_mode"), meta.get("lofreq_min_af"), meta.get("who_catalogue"),
         meta.get("n_pass_hits"), json.dumps(meta)))


def main():
    ap = argparse.ArgumentParser(description="Load bulk.nf results into SQLite")
    ap.add_argument("outdir", type=Path)
    ap.add_argument("database", type=Path)
    ap.add_argument("--prefix", default="brseqtb_", help="table name prefix (default: brseqtb_)")
    args = ap.parse_args()
    p = args.prefix

    con = sqlite3.connect(args.database)
    con.execute("PRAGMA journal_mode=WAL")
    ensure_schema(con, p)

    loaded = {s: t for s, t in con.execute(f"SELECT sample, finished_utc FROM {p}samples")}
    loaded.update({s: t for s, t in con.execute(f"SELECT sample, finished_utc FROM {p}failures")})

    n_new = n_fail = n_skip = 0
    for d in sorted((args.outdir / "samples").iterdir()):
        if not d.is_dir() or d.name.endswith(".partial"):
            continue
        s = d.name
        done, failed = d / f"{s}.sample.json", d / f"{s}.failed.json"
        if not done.exists() and not failed.exists():
            continue
        meta = json.loads((done if done.exists() else failed).read_text())
        if loaded.get(s) == meta.get("finished_utc"):
            n_skip += 1
            continue
        try:
            with con:
                delete_sample(con, p, s)
                if done.exists():
                    load_done(con, p, d, s, meta)
                    n_new += 1
                else:
                    con.execute(f"INSERT INTO {p}failures VALUES (?,?,?,?,?,?,?)",
                                (s, meta.get("status"), meta.get("step"), meta.get("exit_code"),
                                 meta.get("reason"), meta.get("finished_utc"), json.dumps(meta)))
                    n_fail += 1
        except Exception as e:
            print(f"[ERROR] {s}: {e}", file=sys.stderr)

    with con:
        add_indexes(con, p)
    con.close()
    print(f"[OK] loaded {n_new} samples, {n_fail} failures; {n_skip} already up to date -> {args.database}")


if __name__ == "__main__":
    main()
