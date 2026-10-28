#!/usr/bin/env bash
# ============================================================
# IS6110 insertion sites for one biosample (bulk mode)
# IS Sentinel method, nf-core-issentinel aa4cb6e, unchanged:
#   raw reads (no trimming, no duplicate marking)
#   -> bwa mem to H37Rv with the 16 IS6110 copies masked + IS6110 decoy
#   -> delly call -q 0 (all SV types)
#   -> extract_is_candidates.py (genome <-> decoy junctions, PE/SR gates)
#   -> compile_results.py (junctions within 10 bp collapsed)
# Usage: ./issentinel_sample.sh <biosample ID> <results dir>
#
# Output in <results dir>:
#   <id>_is_candidates.csv       per-junction candidates (extract)
#   <id>_is_formatted.csv        collapsed junctions (compile)
#   <id>_issentinel_delly.vcf.gz Delly calls on the masked reference
#   <id>.issentinel.json         status, settings, counts, timings
#   logs/
# The BAM stays in ./scratch and is deleted.
#
# Environment (set by bulk.nf): BRSEQTB_READS, NXF_TASK_CPUS,
# ISSENTINEL_{MAX_DIST,MIN_PE_ISO,MIN_SR_ISO,MIN_TOTAL_CLUST,MIN_SR_ONLY}
# Exit 65: bad input reads (check_reads.sh).
# ============================================================

# Bash reads a script while it runs it: the braces below make bash parse
# the whole file first, so editing it cannot break a running task.
{

export LC_ALL=C
set -euo pipefail

BIOSAMPLE="${1:-}"
RESULTS="${2:-}"

if [[ -z "$BIOSAMPLE" || -z "$RESULTS" ]]; then
    >&2 echo "Usage: ./issentinel_sample.sh <biosample ID> <results dir>"
    exit 1
fi

BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${BIN}/.." && pwd)"
THREADS="${NXF_TASK_CPUS:-1}"
READS_DIR="${BRSEQTB_READS:-${PROJECT_DIR}/reads}"

REF="${PROJECT_DIR}/database/issentinel/masked_reference.fasta"
GBK="${PROJECT_DIR}/database/issentinel/H37RV_REF.gb"

# Gates (nf-core-issentinel nextflow.config defaults)
MAX_DIST="${ISSENTINEL_MAX_DIST:-10}"
MIN_PE_ISO="${ISSENTINEL_MIN_PE_ISO:-10}"
MIN_SR_ISO="${ISSENTINEL_MIN_SR_ISO:-5}"
MIN_TOTAL_CLUST="${ISSENTINEL_MIN_TOTAL_CLUST:-15}"
MIN_SR_ONLY="${ISSENTINEL_MIN_SR_ONLY:-20}"

# The validated runs used bwa mem -t 8 without -K, i.e. batches of
# 10M bases x 8 threads; -K 80000000 reproduces them at any -t
BWA_BATCH_BASES=80000000

export BRSEQTB_OUT="${PWD}/scratch"
W="${BRSEQTB_OUT}/issentinel"
LOGS="${RESULTS}/logs"
TIMINGS="${W}/timings.tsv"
mkdir -p "$W" "$LOGS"
echo -e "step\tseconds" > "$TIMINGS"

step() {
    local name="$1"; shift
    local t0=$SECONDS rc=0
    "$@" > "${LOGS}/${name}.log" 2>&1 || rc=$?
    echo -e "${name}\t$((SECONDS - t0))" >> "$TIMINGS"
    if (( rc != 0 )); then
        >&2 echo "[FAIL] ${BIOSAMPLE}: step ${name} exited ${rc}; last lines of ${name}.log:"
        tail -n 20 "${LOGS}/${name}.log" >&2
        exit "$rc"
    fi
}

[[ -s "${REF}.bwt" ]] || { >&2 echo "[ERROR] IS Sentinel reference not built: ${REF}"; exit 1; }

step check_reads bash "${BIN}/check_reads.sh" "$BIOSAMPLE"

# Raw read pairs (several lanes are concatenated; gzip members concatenate)
mapfile -t R1_FILES < <(find -L "$READS_DIR" -maxdepth 1 -type f \
    \( -name "${BIOSAMPLE}_S*_L*_R1_001.fastq.gz" -o -name "${BIOSAMPLE}_1.fastq.gz" \) | sort)
R2_FILES=()
for R1 in "${R1_FILES[@]}"; do
    case "$R1" in
        *_R1_001.fastq.gz) R2_FILES+=("${R1/_R1_001.fastq.gz/_R2_001.fastq.gz}") ;;
        *) R2_FILES+=("${R1%_1.fastq.gz}_2.fastq.gz") ;;
    esac
done

align() {
    bwa mem -t "$THREADS" -K "$BWA_BATCH_BASES" "$REF" \
        <(cat "${R1_FILES[@]}") <(cat "${R2_FILES[@]}") \
    | samtools view -Sb - \
    | samtools sort -@ "$THREADS" -o "${W}/${BIOSAMPLE}.sorted.bam" -
    samtools index "${W}/${BIOSAMPLE}.sorted.bam"
}

call_sv() {
    delly call -q 0 -g "$REF" -o "${W}/${BIOSAMPLE}.bcf" "${W}/${BIOSAMPLE}.sorted.bam"
    bcftools view "${W}/${BIOSAMPLE}.bcf" > "${W}/${BIOSAMPLE}.vcf"
}

compile() {
    # compile_results.py globs <results>/*/*_is_candidates.csv; it collapses
    # per sample and chromosome, so one sample alone gives that sample's rows
    mkdir -p "${W}/compile/sample"
    cp "${RESULTS}/${BIOSAMPLE}_is_candidates.csv" "${W}/compile/sample/"
    python "${BIN}/issentinel/compile_results.py" \
        --results "${W}/compile" \
        --raw-out "${W}/compiled_raw.csv" \
        --formatted-out "${W}/${BIOSAMPLE}_is_formatted.csv" \
        --max-dist "$MAX_DIST"
    if [[ -s "${W}/${BIOSAMPLE}_is_formatted.csv" ]]; then
        cp "${W}/${BIOSAMPLE}_is_formatted.csv" "$RESULTS/"
    else
        # No candidates: compile_results.py writes nothing; keep a header
        echo "Sample,Chrom,DSB Breakpoint A,DSB Breakpoint B,Orientation,Overlapping Genes,Nearest Gene,Dist. to Nearest,PE A,PE B,SR A,SR B,DV,RV,DR,RR,VAF,Is Heteroresistant,Precision A,Precision B,Detection Method" \
            > "${RESULTS}/${BIOSAMPLE}_is_formatted.csv"
    fi
}

step align   align
step delly   call_sv
step extract python "${BIN}/issentinel/extract_is_candidates.py" \
    --vcf "${W}/${BIOSAMPLE}.vcf" \
    --gbk "$GBK" \
    --out "${RESULTS}/${BIOSAMPLE}_is_candidates.csv" \
    --max-dist "$MAX_DIST" \
    --min-pe-iso "$MIN_PE_ISO" \
    --min-sr-iso "$MIN_SR_ISO" \
    --min-total-clust "$MIN_TOTAL_CLUST" \
    --min-sr-only "$MIN_SR_ONLY" \
    --decoy IS6110
step compile compile

bgzip -c "${W}/${BIOSAMPLE}.vcf" > "${RESULTS}/${BIOSAMPLE}_issentinel_delly.vcf.gz"
cp "${BRSEQTB_OUT}/readCheck/${BIOSAMPLE}/${BIOSAMPLE}_read_check.tsv" "$RESULTS/"

python - "$BIOSAMPLE" "$RESULTS" "$TIMINGS" "$MAX_DIST" "$MIN_PE_ISO" "$MIN_SR_ISO" "$MIN_TOTAL_CLUST" "$MIN_SR_ONLY" <<'PY'
import csv, json, sys
from datetime import datetime, timezone
sample, results, timings, *gates = sys.argv[1:]
rows = lambda f: sum(1 for _ in csv.DictReader(open(f"{results}/{sample}_{f}.csv")))
t = list(csv.DictReader(open(timings), delimiter="\t"))
json.dump({
    "sample": sample,
    "status": "done",
    "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "method": "IS Sentinel (nf-core-issentinel aa4cb6e)",
    "gates": dict(zip(["max_dist", "min_pe_iso", "min_sr_iso", "min_total_clust", "min_sr_only"], map(int, gates))),
    "n_candidates": rows("is_candidates"),
    "n_junctions": rows("is_formatted"),
    "step_seconds": {r["step"]: int(r["seconds"]) for r in t},
}, open(f"{results}/{sample}.issentinel.json", "w"), indent=2)
PY

rm -rf "$BRSEQTB_OUT"
>&2 echo "[DONE] ${BIOSAMPLE} (IS Sentinel)"

exit
}
