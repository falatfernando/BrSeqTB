#!/usr/bin/env bash
# ============================================================
# Run Trimmomatic for all paired reads of a given biosample
# Usage: ./trimmomatic.sh <biosample ID>
# Input: reads/<biosample ID>_SX_L00X_RX_00X.fastq.gz
# Input files must use the Illumina read naming convention:
# 1827-22_S1_L001_R1_001.fastq.gz
# ││││││││││││││││││││││││││
# └─── biosample ID (1827-22)
#        └── biosample number (S1)
#           └── lane (L002)
#                └── read direction (R1/R2)
#                   └── file index (_001)
# ============================================================

export LC_ALL=C
set -euo pipefail

BIOSAMPLE="${1:-}"
THREADS="${NXF_TASK_CPUS:-1}"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Reads and per-sample results roots (defaults: projectDir/reads, projectDir)
READS_DIR="${BRSEQTB_READS:-${PROJECT_DIR}/reads}"
OUT_ROOT="${BRSEQTB_OUT:-$PROJECT_DIR}"
OUTPUT_DIR="${OUT_ROOT}/trimmomatic/${BIOSAMPLE}"
SUMMARY_CSV="${OUTPUT_DIR}/${BIOSAMPLE}_trimmomatic_summary.csv"
MIN_BOTH_SURVIVING=75.0

# JVM heap cap, only when the pipeline passes one; Trimmomatic runs alone in
# its task, so the larger BRSEQTB_JAVA_XMX_SOLO applies when set (the conda
# wrapper's default -Xmx1g ran out with -threads 4)
JAVA_XMX="${BRSEQTB_JAVA_XMX_SOLO:-${BRSEQTB_JAVA_XMX:-}}"
JAVA_OPTS=()
[[ -n "$JAVA_XMX" ]] && JAVA_OPTS=("-Xmx${JAVA_XMX}")

# ================== CHECK INPUT ==================
if [[ -z "$BIOSAMPLE" ]]; then
    >&2 echo "Usage: ./trimmomatic.sh <biosample ID>"
    exit 1
fi

if [[ ! -d "$READS_DIR" ]]; then
    >&2 echo "[ERROR] Reads directory not found: $READS_DIR"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# ===================== SKIP IF ALREADY DONE =====================
if [[ -s "$SUMMARY_CSV" ]]; then
    >&2 echo "[SKIP] Trimmomatic already completed for ${BIOSAMPLE}"
    >&2 echo "[OUT] ${SUMMARY_CSV}"
    exit 0
fi
# ===============================================================


>&2 echo "[RUN] Running Trimmomatic for biosample: $BIOSAMPLE"
>&2 echo "[DIR] Searching files in: $READS_DIR"
>&2 echo "[OUT] Output directory: $OUTPUT_DIR"
>&2 echo "---------------------------------------------"

# ================== FIND PAIRED READS (SAFE) ==================
# Illumina naming (<id>_S*_L*_R1_001.fastq.gz, one pair per lane) or
# simplified ENA/SRA naming (<id>_1.fastq.gz / <id>_2.fastq.gz, one pair)
mapfile -t R1_FILES < <(
    find -L "$READS_DIR" -maxdepth 1 -type f \
        \( -name "${BIOSAMPLE}_S*_L*_R1_001.fastq.gz" -o -name "${BIOSAMPLE}_1.fastq.gz" \) | sort
)

if [[ ${#R1_FILES[@]} -eq 0 ]]; then
    >&2 echo "[ERROR] No R1 FASTQs found for biosample '${BIOSAMPLE}'."
    exit 1
fi

# R2 path for an R1 path, for either naming convention
r2_of() {
    case "$1" in
        *_R1_001.fastq.gz) echo "${1/_R1_001.fastq.gz/_R2_001.fastq.gz}" ;;
        *) echo "${1%_1.fastq.gz}_2.fastq.gz" ;;
    esac
}

# Read-pair base name (log / summary key) for an R1 path
base_of() {
    case "$1" in
        *_R1_001.fastq.gz) basename "${1/_R1_001.fastq.gz/}" ;;
        *) basename "${1%_1.fastq.gz}" ;;
    esac
}

echo "[INFO] Found ${#R1_FILES[@]} read pairs:"
for R1 in "${R1_FILES[@]}"; do
    R2="$(r2_of "$R1")"

    if [[ ! -f "$R2" ]]; then
        >&2 echo "[ERROR] Missing paired R2 for:"
        >&2 echo "        $(basename "$R1")"
        exit 1
    fi

    echo "   • $(basename "$R1") ↔ $(basename "$R2")"
done
echo "---------------------------------------------"

# ================== RUN TRIMMOMATIC ==================
for R1 in "${R1_FILES[@]}"; do
    R2="$(r2_of "$R1")"
    BASE="$(base_of "$R1")"

    OUT_R1_PAIRED="${OUTPUT_DIR}/$(basename "$R1")"
    OUT_R2_PAIRED="${OUTPUT_DIR}/$(basename "$R2")"
    OUT_R1_UNPAIRED="${OUTPUT_DIR}/${BASE}_R1_unpaired.fastq.gz"
    OUT_R2_UNPAIRED="${OUTPUT_DIR}/${BASE}_R2_unpaired.fastq.gz"
    LOG_FILE="${OUTPUT_DIR}/${BASE}_trimmomatic.log"

    >&2 echo "[RUN] Trimming: $(basename "$R1") and $(basename "$R2")"

    trimmomatic "${JAVA_OPTS[@]}" PE -threads "$THREADS" \
        "$R1" "$R2" \
        "$OUT_R1_PAIRED" "$OUT_R1_UNPAIRED" \
        "$OUT_R2_PAIRED" "$OUT_R2_UNPAIRED" \
        SLIDINGWINDOW:4:20 MINLEN:50 \
        2>&1 | tee "$LOG_FILE"

    rm -f "$OUT_R1_UNPAIRED" "$OUT_R2_UNPAIRED"
done

# ================== SUMMARY ==================
>&2 echo "[INFO] Parsing trimming statistics..."
echo "biosample,filename,input_read_pairs,both_surviving,both_surviving_pct,forward_only,forward_only_pct,reverse_only,reverse_only_pct,dropped,dropped_pct,status" \
    > "$SUMMARY_CSV"

for LOG_FILE in "${OUTPUT_DIR}"/*_trimmomatic.log; do
    FILE=$(basename "$LOG_FILE" | sed 's/_trimmomatic\.log//')

    CLEAN_LINE=$(grep "Input Read Pairs:" "$LOG_FILE" | \
        sed 's/,/./g; s/[()%]//g')

    if [[ -n "$CLEAN_LINE" ]]; then
        input=$(echo "$CLEAN_LINE" | awk '{for(i=1;i<=NF;i++) if($i=="Pairs:") print $(i+1)}')
        both=$(echo "$CLEAN_LINE" | awk '{for(i=1;i<=NF;i++) if($i=="Surviving:" && $(i-1)=="Both") print $(i+1)}')
        both_pct=$(echo "$CLEAN_LINE" | awk '{for(i=1;i<=NF;i++) if($i=="Surviving:" && $(i-1)=="Both") print $(i+2)}')
        forward=$(echo "$CLEAN_LINE" | awk '{for(i=1;i<=NF;i++) if($i=="Surviving:" && $(i-2)=="Forward") print $(i+1)}')
        forward_pct=$(echo "$CLEAN_LINE" | awk '{for(i=1;i<=NF;i++) if($i=="Surviving:" && $(i-2)=="Forward") print $(i+2)}')
        reverse=$(echo "$CLEAN_LINE" | awk '{for(i=1;i<=NF;i++) if($i=="Surviving:" && $(i-2)=="Reverse") print $(i+1)}')
        reverse_pct=$(echo "$CLEAN_LINE" | awk '{for(i=1;i<=NF;i++) if($i=="Surviving:" && $(i-2)=="Reverse") print $(i+2)}')
        dropped=$(echo "$CLEAN_LINE" | awk '{for(i=1;i<=NF;i++) if($i=="Dropped:") print $(i+1)}')
        dropped_pct=$(echo "$CLEAN_LINE" | awk '{for(i=1;i<=NF;i++) if($i=="Dropped:") print $(i+2)}')

        status="PASS"
        if [[ -z "$both_pct" || $(echo "$both_pct < $MIN_BOTH_SURVIVING" | bc -l) -eq 1 ]]; then
            status="FAIL"
        fi

        echo "${BIOSAMPLE},${FILE},${input},${both},${both_pct},${forward},${forward_pct},${reverse},${reverse_pct},${dropped},${dropped_pct},${status}" \
            >> "$SUMMARY_CSV"
    fi
done

>&2 echo "[OK] Summary table generated: $SUMMARY_CSV"
>&2 echo "[DONE] Trimmomatic completed for biosample: $BIOSAMPLE"


