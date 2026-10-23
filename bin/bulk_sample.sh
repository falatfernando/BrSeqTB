#!/usr/bin/env bash
# ============================================================
# Whole per-sample chain for one biosample (bulk mode)
# Usage: ./bulk_sample.sh <biosample ID> <results dir>
#
# Runs in the Nextflow task directory. Intermediates (trimmed
# reads, BAM, gVCF, xlsx) live in ./scratch and are deleted at
# the end; only <results dir> is kept:
#   <id>.{calls.tsv.gz,resistance_hits.tsv,resistance_profile.tsv,
#         qc.tsv,sample.json}  (+ <id>.oxidative_damage.tsv)
#   vcf/<id>_{gatk,norm,lofreq,delly}.vcf.gz(.tbi)   snpEff-annotated
#   logs/                                            one log per step
#
# The steps are the per-sample bin/ scripts, unchanged; GATK
# (VCF + gVCF), LoFreq and Delly run in parallel after BWA.
#
# Environment (set by bulk.nf):
#   BRSEQTB_READS        reads directory
#   NXF_TASK_CPUS        threads for FastQC / Trimmomatic / BWA
#   BRSEQTB_GATK_THREADS pair-HMM threads per HaplotypeCaller (default 2)
#   BRSEQTB_LOFREQ_THREADS LoFreq call-parallel threads (default 2, as v1)
#   BRSEQTB_LOFREQ_MIN_AF  LoFreq AF filter (default 0.00)
#   BRSEQTB_JAVA_XMX     heap per JVM (two GATK JVMs run at once)
#
# Exit 65: the input reads are bad (see check_reads.sh); do not retry.
# ============================================================

export LC_ALL=C
set -euo pipefail

BIOSAMPLE="${1:-}"
RESULTS="${2:-}"

if [[ -z "$BIOSAMPLE" || -z "$RESULTS" ]]; then
    >&2 echo "Usage: ./bulk_sample.sh <biosample ID> <results dir>"
    exit 1
fi

BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export BRSEQTB_OUT="${PWD}/scratch"
export BRSEQTB_FILTER_MODE=per_sample
GATK_THREADS="${BRSEQTB_GATK_THREADS:-2}"
LOFREQ_THREADS="${BRSEQTB_LOFREQ_THREADS:-2}"
export BRSEQTB_LOFREQ_MIN_AF="${BRSEQTB_LOFREQ_MIN_AF:-0.00}"

LOGS="${RESULTS}/logs"
TIMINGS="${BRSEQTB_OUT}/timings.tsv"
mkdir -p "$BRSEQTB_OUT" "$LOGS" "${RESULTS}/vcf"
echo -e "step\tseconds" > "$TIMINGS"

# step <name> <command...>: run, log to logs/<name>.log, record seconds.
# On failure the step's exit code is kept (65 = bad input).
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

# ================== READS ==================
step check_reads bash "${BIN}/check_reads.sh" "$BIOSAMPLE"
step fastqc      bash "${BIN}/fastqc.sh" "$BIOSAMPLE"
step trimmomatic bash "${BIN}/trimmomatic.sh" "$BIOSAMPLE"
step bwa         bash "${BIN}/bwa.sh" "$BIOSAMPLE"

# Trimmed reads are no longer needed once the BAM exists
rm -rf "${BRSEQTB_OUT}/trimmomatic/${BIOSAMPLE}"/*.fastq.gz

# ================== CALLERS (parallel) ==================
gatk_vcf_branch() {
    NXF_TASK_CPUS="$GATK_THREADS" step gatk_vcf bash "${BIN}/gatkVcf.sh" "$BIOSAMPLE"
    step norm bash "${BIN}/norm.sh" "$BIOSAMPLE"
}

declare -A PIDS
gatk_vcf_branch & PIDS[gatk_vcf]=$!
( NXF_TASK_CPUS="$GATK_THREADS" step gatk_gvcf bash "${BIN}/gatkGvcf.sh" "$BIOSAMPLE" ) & PIDS[gatk_gvcf]=$!
( step lofreq bash "${BIN}/lofreq.sh" "$BIOSAMPLE" "$LOFREQ_THREADS" "$BRSEQTB_LOFREQ_MIN_AF" ) & PIDS[lofreq]=$!
( step delly bash "${BIN}/delly.sh" "$BIOSAMPLE" ) & PIDS[delly]=$!

FAILED=()
for name in "${!PIDS[@]}"; do
    wait "${PIDS[$name]}" || FAILED+=("$name")
done
if (( ${#FAILED[@]} > 0 )); then
    >&2 echo "[FAIL] ${BIOSAMPLE}: caller branch(es) failed: ${FAILED[*]}"
    exit 1
fi

# ================== ANNOTATION + PER-SAMPLE ANALYSES ==================
step snpeff        bash "${BIN}/snpeff.sh" "$BIOSAMPLE"
step ntm_filter    bash "${BIN}/ntmFilter.sh" "$BIOSAMPLE"
step tbdr_rcov     python "${BIN}/tbdrRCov.py" "$BIOSAMPLE"
step lineage       python "${BIN}/lineage.py" "$BIOSAMPLE"
step mix_table     python "${BIN}/mix_snp_table.py" "$BIOSAMPLE"
step mix_infection python "${BIN}/mixInfection.py" "$BIOSAMPLE"
step resistance_target python "${BIN}/resistanceTarget.py" "$BIOSAMPLE"
step resistance_report python "${BIN}/resistanceReport.py" "$BIOSAMPLE"

# ================== KEEP ==================
cp "${BRSEQTB_OUT}/snpeff/${BIOSAMPLE}/"*.vcf.gz "${BRSEQTB_OUT}/snpeff/${BIOSAMPLE}/"*.vcf.gz.tbi "${RESULTS}/vcf/"
cp "${BRSEQTB_OUT}/readCheck/${BIOSAMPLE}/${BIOSAMPLE}_read_check.tsv" "${RESULTS}/"
step export python "${BIN}/export_sample.py" "$BIOSAMPLE" "$RESULTS" "$TIMINGS"

# ================== CLEAN ==================
rm -rf "$BRSEQTB_OUT"
>&2 echo "[DONE] ${BIOSAMPLE}"
