#!/usr/bin/env bash
# ============================================================
# Integrity gate for the FASTQs of one biosample (bulk mode)
# Usage: ./check_reads.sh <biosample ID>
# Input: $BRSEQTB_READS/<id>_S*_L*_R{1,2}_001.fastq.gz (Illumina)
#        or $BRSEQTB_READS/<id>_{1,2}.fastq.gz (ENA/SRA)
# Output: $BRSEQTB_OUT/readCheck/<id>/<id>_read_check.tsv
#
# Each file is decompressed once in full: a corrupt gzip stream
# fails the pipe. Then, per pair: line count a multiple of 4,
# more than zero reads, and R1/R2 with the same number of reads.
#
# Exit 65 (EX_DATAERR) when the input itself is bad, so the
# pipeline can skip the sample instead of retrying it.
# Exit 75 (EX_TEMPFAIL) when the reads directory itself is not
# reachable (e.g. a USB disk dropped): not the sample's fault, so it
# must not be recorded as bad input.
# ============================================================

# Bash reads a script while it runs it: the braces below make bash parse
# the whole file first, so editing it cannot break a running task.
{

export LC_ALL=C
set -euo pipefail

BIOSAMPLE="${1:-}"
THREADS="${NXF_TASK_CPUS:-1}"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
READS_DIR="${BRSEQTB_READS:-${PROJECT_DIR}/reads}"
OUT_ROOT="${BRSEQTB_OUT:-$PROJECT_DIR}"
OUTPUT_DIR="${OUT_ROOT}/readCheck/${BIOSAMPLE}"
REPORT="${OUTPUT_DIR}/${BIOSAMPLE}_read_check.tsv"

EX_DATAERR=65
EX_TEMPFAIL=75

if [[ -z "$BIOSAMPLE" ]]; then
    >&2 echo "Usage: ./check_reads.sh <biosample ID>"
    exit 1
fi

if [[ ! -d "$READS_DIR" || ! -r "$READS_DIR" || ! -x "$READS_DIR" ]]; then
    >&2 echo "[STORAGE_UNAVAILABLE] ${BIOSAMPLE}: reads directory not reachable: ${READS_DIR}"
    exit "$EX_TEMPFAIL"
fi

mkdir -p "$OUTPUT_DIR"
echo -e "biosample\tfile\treads\tstatus" > "$REPORT"

bad() {
    >&2 echo "[READ_CHECK_FAIL] ${BIOSAMPLE}: $1"
    echo -e "${BIOSAMPLE}\t${2:-.}\t.\tFAIL: $1" >> "$REPORT"
    exit "$EX_DATAERR"
}

mapfile -t R1_FILES < <(
    find -L "$READS_DIR" -maxdepth 1 -type f \
        \( -name "${BIOSAMPLE}_S*_L*_R1_001.fastq.gz" -o -name "${BIOSAMPLE}_1.fastq.gz" \) | sort
)

[[ ${#R1_FILES[@]} -gt 0 ]] || bad "no R1 FASTQ in ${READS_DIR}"

# Reads in one gzipped FASTQ; fails (non-zero) on a corrupt stream
count_reads() {
    local lines
    lines=$(pigz -dc -p "$THREADS" "$1" | wc -l) || return 1
    (( lines % 4 == 0 )) || { echo "truncated:${lines}"; return 0; }
    echo $(( lines / 4 ))
}

for R1 in "${R1_FILES[@]}"; do
    case "$R1" in
        *_R1_001.fastq.gz) R2="${R1/_R1_001.fastq.gz/_R2_001.fastq.gz}" ;;
        *) R2="${R1%_1.fastq.gz}_2.fastq.gz" ;;
    esac
    [[ -f "$R2" ]] || bad "missing R2 for $(basename "$R1")" "$(basename "$R2")"

    for F in "$R1" "$R2"; do
        n=$(count_reads "$F") || bad "corrupt gzip stream" "$(basename "$F")"
        [[ "$n" == truncated:* ]] && bad "line count ${n#truncated:} is not a multiple of 4" "$(basename "$F")"
        (( n > 0 )) || bad "no reads" "$(basename "$F")"
        echo -e "${BIOSAMPLE}\t$(basename "$F")\t${n}\tPASS" >> "$REPORT"
        if [[ "$F" == "$R1" ]]; then n1=$n; else n2=$n; fi
    done

    (( n1 == n2 )) || bad "R1/R2 read counts differ (${n1} vs ${n2})" "$(basename "$R1")"
done

>&2 echo "[OK] Reads intact for ${BIOSAMPLE}: ${#R1_FILES[@]} pair(s)"

exit
}
