"""Pick a stratified 60-isolate validation set from bdq_metadata (deterministic, seed 20261023)."""
import os
import random
import sqlite3
import sys

DB = os.path.expanduser("~/Repositories/bdq_warehouse/production/bdq_warehouse.db")
READS = "/mnt/mgd_storage/reads_bdq/illumina_reads"
OUT = sys.argv[1]

rng = random.Random(20261023)
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
meta = {r["accession"]: dict(r) for r in con.execute("select * from bdq_metadata")}

def size(acc):
    return sum(os.stat(f"{READS}/{acc}_{i}.fastq.gz").st_size for i in (1, 2))

is_rv0678 = {r[0] for r in con.execute('select distinct "Sample" from is_sentinel_mmpL5_Rv0678')} & set(meta)

picked = {}  # accession -> reason

def take(pool, n, reason):
    pool = sorted(a for a in pool if a not in picked)
    for a in rng.sample(pool, min(n, len(pool))):
        picked[a] = reason

def where(**kw):
    return [a for a, m in meta.items() if all(m[k] == v for k, v in kw.items())]

# Rare species / lineages: one each
for sp in ["M. bovis", "M. bovis subsp. BCG", "M. africanum", "M. orgyis", "M. caprae"]:
    take(where(species=sp), 1, f"species:{sp}")
take(where(lineage="lineage6"), 1, "lineage6")
take(where(lineage="lineage1"), 2, "lineage1")
take(where(lineage="lineage3"), 2, "lineage3")
take(where(lineage="mixed"), 3, "lineage:mixed")

# IS6110 in mmpL5-Rv0678 (validates the IS Sentinel module)
take(is_rv0678, 4, "IS6110_in_Rv0678")

# BDQ phenotype
take(where(source="CRyPTIC", pDST_phenotype="R"), 6, "BDQ_R:CRyPTIC")
take(where(source="NICD", pDST_phenotype="R"), 6, "BDQ_R:NICD")
take(where(source="SEQTREAT2020", pDST_phenotype="R"), 2, "BDQ_R:SEQTREAT2020")
take(where(pDST_consensus="borderline"), 3, "BDQ_borderline")
take([a for a, m in meta.items() if m["pDST_discordant"] == 1], 2, "pDST_discordant")
take(where(source="CRyPTIC", pDST_phenotype="S", lineage="lineage2"), 3, "BDQ_S:CRyPTIC:L2")
take(where(source="CRyPTIC", pDST_phenotype="S", lineage="lineage4"), 3, "BDQ_S:CRyPTIC:L4")
take(where(source="NICD", pDST_phenotype="S"), 2, "BDQ_S:NICD")

# Sources without consensus phenotype
for src, n in [("CABBAGE", 2), ("IAL", 2), ("NCBI_antibiogram", 2), ("PATRIC", 1)]:
    take(where(source=src), n, f"source:{src}")

take(where(quality="LOW"), 3, "quality:LOW")

# File-size extremes (coverage / runtime edge cases)
by_size = sorted(meta, key=size)
for a in [x for x in reversed(by_size) if x not in picked][:3]:
    picked[a] = "largest_files"
for a in [x for x in by_size if x not in picked][:3]:
    picked[a] = "smallest_files"

assert len(picked) == 60, len(picked)
with open(OUT, "w") as fh:
    cols = ["accession", "reason", "source", "species", "lineage", "pDST_phenotype", "pDST_consensus", "quality", "size_mb"]
    fh.write("\t".join(cols) + "\n")
    for a in sorted(picked, key=lambda x: (picked[x], x)):
        m = meta[a]
        row = [a, picked[a]] + [str(m[c]) for c in cols[2:-1]] + [f"{size(a) / 1e6:.0f}"]
        fh.write("\t".join(row) + "\n")
print(f"wrote {len(picked)} isolates, {sum(size(a) for a in picked) / 1e9:.1f} GB of reads")
