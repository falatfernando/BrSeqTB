#!/usr/bin/env python3
# ============================================================
# Per-sample SNP table for mixed-infection detection
#
# Usage: python mix_snp_table.py <biosample ID>
# Input:  snpeff/<biosample ID>/<biosample ID>_norm.vcf.gz
# Output: mixInfection/<biosample ID>/<biosample ID>.tsv
#         (chrom, pos, ref, alt, gt), read by mixInfection.py
#
# The functions below were moved verbatim out of snpMatrix.py,
# which imports them, so the cohort run (snpMatrix.py) and the
# per-sample run (this script) share one implementation:
#   - single-base records only (every allele of length 1)
#   - records in forbidden genes are removed (snpEff ANN
#     Gene_Name or Gene_ID in database/mtbRef/forbidden_genes.txt,
#     case-insensitive)
#   - hom-ref and missing GT are skipped
# ============================================================

import os
import sys
from pathlib import Path

import pysam

PROJECT_DIR = Path(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

# Per-sample results root (default: projectDir; bulk mode points it at task scratch)
OUT_ROOT = Path(os.environ.get("BRSEQTB_OUT", PROJECT_DIR))

FORBIDDEN_FILE = PROJECT_DIR / "database" / "mtbRef" / "forbidden_genes.txt"


# ============================================================
# LOAD FORBIDDEN GENES
# ============================================================
def load_forbidden_genes(path: Path):

    if not path.is_file():
        sys.exit(f"[ERROR] Forbidden genes file not found: {path}")

    forbidden = set()

    with open(path) as f:

        for line in f:

            line = line.strip()

            if not line or line.startswith("#"):
                continue

            forbidden.add(line.lower())

    return forbidden


# ============================================================
# ANN / FORBIDDEN LOGIC
# ============================================================
def extract_genes_from_ann(ann_tuple):

    genes = []

    for ann in ann_tuple:

        fields = ann.split("|")

        if len(fields) >= 5:

            gene_name = fields[3].strip().lower()
            gene_id   = fields[4].strip().lower()

            genes.append(
                (gene_name, gene_id)
            )

    return genes


def is_forbidden_ann(ann_tuple, forbidden):

    genes = extract_genes_from_ann(ann_tuple)

    for gene_name, gene_id in genes:

        if gene_name in forbidden:
            return True

        if gene_id in forbidden:
            return True

    return False


# ============================================================
# FULL SNP TABLE (MIXED INFECTION)
# ORIGINAL PIPELINE LOGIC UNCHANGED
# ============================================================
def extract_snp_table(vcf_path: Path, forbidden):

    rows = []

    vcf = pysam.VariantFile(
        str(vcf_path)
    )

    for rec in vcf.fetch():

        if any(
            len(a) != 1
            for a in rec.alleles
        ):
            continue

        ann = rec.info.get("ANN", ())

        if ann and is_forbidden_ann(ann, forbidden):
            continue

        sample = list(
            rec.samples.values()
        )[0]

        gt = sample.get("GT")

        if gt is None:
            continue

        if all(
            a == 0
            for a in gt
        ):
            continue

        gt_str = "/".join(
            "." if a is None else str(a)
            for a in gt
        )

        alt_idx = (
            gt[0]
            if gt[0] != 0
            else gt[1]
        )

        alt_base = rec.alleles[alt_idx]

        rows.append({
            "chrom": rec.chrom,
            "pos": rec.pos,
            "ref": rec.ref,
            "alt": alt_base,
            "gt": gt_str
        })

    return rows


def write_snp_table(rows, outfile: Path):

    with open(outfile, "w") as out:

        out.write(
            "chrom\tpos\tref\talt\tgt\n"
        )

        for r in rows:

            out.write(
                f"{r['chrom']}\t"
                f"{r['pos']}\t"
                f"{r['ref']}\t"
                f"{r['alt']}\t"
                f"{r['gt']}\n"
            )


# ============================================================
# MAIN (one biosample)
# ============================================================
def main():

    if len(sys.argv) != 2:
        sys.exit("Usage: python mix_snp_table.py <biosample ID>")

    biosample = sys.argv[1]

    vcf_path = OUT_ROOT / "snpeff" / biosample / f"{biosample}_norm.vcf.gz"

    if not vcf_path.is_file():
        sys.exit(f"[ERROR] Missing normalized snpEff VCF: {vcf_path}")

    rows = extract_snp_table(vcf_path, load_forbidden_genes(FORBIDDEN_FILE))

    outdir = OUT_ROOT / "mixInfection" / biosample
    outdir.mkdir(parents=True, exist_ok=True)

    outfile = outdir / f"{biosample}.tsv"
    write_snp_table(rows, outfile)

    print(f"[OK] mixInfection table written: {outfile}")


if __name__ == "__main__":
    main()
