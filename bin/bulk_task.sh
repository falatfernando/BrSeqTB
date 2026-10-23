#!/usr/bin/env bash
# ============================================================
# Nextflow task wrapper around bulk_sample.sh (bulk mode)
# Usage: ./bulk_task.sh <biosample ID> <results dir> <final attempt: true|false> <publish dir>
#
# - success: results dir holds <id>.sample.json and the tables
# - failure, not final attempt and not bad input: exit non-zero
#   so Nextflow retries the task
# - failure, final attempt or bad input (exit 65): write
#   <id>.failed.json (step, exit code, last log lines) into the
#   results dir and exit 0, so the failure is published with
#   its logs instead of disappearing
#
# Publishing: the results dir is copied to <publish dir>/<id>.partial
# and renamed to <publish dir>/<id> (same filesystem, atomic), so a
# sample directory with <id>.sample.json is always complete. The
# local copy is then removed (publishDir 'move' cannot move a
# directory across filesystems).
# ============================================================

export LC_ALL=C
set -uo pipefail

BIOSAMPLE="$1"
RESULTS="$2"
FINAL="$3"
PUBLISH_DIR="$4"

# Copy RESULTS to PUBLISH_DIR/BIOSAMPLE atomically, then drop the local copy
publish() {
    local dest="${PUBLISH_DIR}/${BIOSAMPLE}"
    local tmp="${dest}.partial"
    mkdir -p "$PUBLISH_DIR" || return 1
    rm -rf "$tmp" || return 1
    cp -r "$RESULTS" "$tmp" || return 1
    # A re-run (--retryFailed) replaces the earlier record
    if [[ -d "$dest" ]]; then rm -rf "$dest" || return 1; fi
    mv "$tmp" "$dest" || return 1
    rm -rf "$RESULTS"
    echo "${dest}" > published.txt
}

BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EX_DATAERR=65

mkdir -p "$RESULTS"
ERR_LOG="${PWD}/driver.err"

bash "${BIN}/bulk_sample.sh" "$BIOSAMPLE" "$RESULTS" 2> >(tee "$ERR_LOG" >&2)
rc=$?
wait  # let tee finish writing driver.err

if (( rc == 0 )); then
    publish || { >&2 echo "[FAIL] ${BIOSAMPLE}: publishing to ${PUBLISH_DIR} failed"; exit 1; }
    exit 0
fi

if (( rc != EX_DATAERR )) && [[ "$FINAL" != "true" ]]; then
    >&2 echo "[RETRY] ${BIOSAMPLE}: exit ${rc}, Nextflow will retry"
    exit "$rc"
fi

# Final failure: record it next to the logs and finish the task
step=$(grep -oE 'step [A-Za-z_]+ exited' "$ERR_LOG" | tail -n 1 | awk '{print $2}')
[[ -z "$step" ]] && step=$(grep -oE 'caller branch\(es\) failed: .*' "$ERR_LOG" | tail -n 1 | sed 's/.*failed: //')
reason=$(grep -oE '\[READ_CHECK_FAIL\] .*' "$ERR_LOG" | tail -n 1 | sed 's/^\[READ_CHECK_FAIL\] [^:]*: //')

python - "$BIOSAMPLE" "$rc" "${step:-unknown}" "$reason" "$ERR_LOG" "${RESULTS}/${BIOSAMPLE}.failed.json" <<'PY'
import json, sys
from datetime import datetime, timezone
sample, rc, step, reason, err_log, out = sys.argv[1:]
tail = open(err_log, errors="replace").read().splitlines()[-30:]
json.dump({
    "sample": sample,
    "status": "bad_input" if rc == "65" else "failed",
    "exit_code": int(rc),
    "step": step,
    "reason": reason,
    "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "stderr_tail": tail,
}, open(out, "w"), indent=2)
PY

rm -rf "${PWD}/scratch"
publish || { >&2 echo "[FAIL] ${BIOSAMPLE}: publishing to ${PUBLISH_DIR} failed"; exit 1; }
>&2 echo "[RECORDED] ${BIOSAMPLE}: ${step:-unknown} failed (exit ${rc}) -> ${BIOSAMPLE}.failed.json"
exit 0
