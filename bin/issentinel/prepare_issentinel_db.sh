#!/usr/bin/env bash
# ============================================================
# Masked H37Rv + IS6110 decoy reference for IS Sentinel
# Usage: ./prepare_issentinel_db.sh
# Input:  database/mtbRef/NC0009623.fasta   (same sequence and header
#                                            as IS Sentinel's H37RV.fna)
#         database/issentinel/H37RV_REF.gb   (IS6110 copy coordinates)
#         database/issentinel/IS6110.fasta   (X17348.1, decoy contig)
# Output: database/issentinel/masked_reference.fasta (+ .fai, bwa index)
#         the 16 annotated IS6110 copies replaced by N, plus contig IS6110
# Skips work already done.
# ============================================================

export LC_ALL=C
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DB="${PROJECT_DIR}/database/issentinel"
MASKED="${DB}/masked_reference.fasta"

if [[ ! -s "$MASKED" ]]; then
    python "${PROJECT_DIR}/bin/issentinel/prepare_masked_reference.py" \
        --gbk "${DB}/H37RV_REF.gb" \
        --fasta "${PROJECT_DIR}/database/mtbRef/NC0009623.fasta" \
        --is6110 "${DB}/IS6110.fasta" \
        --out "${MASKED}.tmp"
    mv "${MASKED}.tmp" "$MASKED"
fi

[[ -s "${MASKED}.fai" ]] || samtools faidx "$MASKED"
[[ -s "${MASKED}.bwt" ]] || bwa index "$MASKED"

echo "[OK] IS Sentinel reference: ${MASKED}"
