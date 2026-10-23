/*
 * ============================================================
 * BrSeqTB — BULK MODE
 *
 * One task per biosample, no cross-sample steps: resistance
 * profile, all variant calls (WHO catalogue and non-catalogue)
 * and QC, written as TSV/JSON for loading into a database.
 *
 * Differences from main.nf (full mode):
 *   - GATK/norm calls use per-sample filters only
 *     (BRSEQTB_FILTER_MODE=per_sample): no cohort genotyping, a
 *     sample's result does not depend on the other samples
 *   - no kaiju, cohort, SNP matrix, transmission, IQ-TREE,
 *     xlsx/docx reports
 *   - intermediates (BAM, gVCF, trimmed reads) stay in the task
 *     directory and are deleted when the sample finishes
 *
 * Usage:
 *   nextflow run bulk.nf -profile bulk \
 *     --manifest manifest.tsv --readsDir /path/reads --outdir /path/results
 *
 * Re-running the same command continues where it stopped:
 * samples with <outdir>/samples/<id>/<id>.sample.json are skipped
 * (and those with <id>.failed.json, unless --retryFailed).
 * ============================================================
 */

nextflow.enable.dsl = 2

params.manifest    = null   // TSV with a 'biosample' header (make_manifest_validate.py)
params.readsDir    = null
params.outdir      = null
params.lofreqMinAf = 0.00
params.retryFailed = false  // re-run samples that have a <id>.failed.json
params.limit       = 0      // run at most this many pending samples (0 = all)

include { taskEnv } from './modules/common'

/*
 * Reference indexes, snpEff DB and WHO catalogue tables in
 * projectDir/database (each script skips work already done)
 */
process PREPARE_DB {

    tag "database"

    input:
        val token

    output:
        val true

    script:
    """
    cd "${projectDir}"
    python bin/omsCatalog.py
    bash bin/bwaref.sh
    bash bin/gatkdict.sh
    bash bin/snpeffdb.sh
    """
}

process SAMPLE {

    tag { biosample }

    // The task publishes its own results (bulk_task.sh: copy, then an
    // atomic rename into <outdir>/samples/<id>) and keeps nothing in
    // the work directory; finished samples are skipped through the
    // published sample.json
    input:
        val biosample
        val db_ready

    output:
        path "published.txt"

    script:
    // Two GATK JVMs run at once inside the task: 0.35 of task.memory each
    def finalAttempt = task.attempt >= (task.maxRetries ?: 0) + 1
    """
    ${taskEnv(task, params.readsDir, 0.35)}
    export BRSEQTB_LOFREQ_MIN_AF=${params.lofreqMinAf}
    bash "${projectDir}/bin/bulk_task.sh" ${biosample} "results/${biosample}" ${finalAttempt} "${file(params.outdir)}/samples"
    """
}

workflow {

    if (!params.manifest || !params.readsDir || !params.outdir) {
        error "bulk.nf needs --manifest, --readsDir and --outdir"
    }

    def samplesDir = file("${params.outdir}/samples")

    pending_ch = channel.fromPath(params.manifest)
        .splitCsv(header: true, sep: '\t')
        .map { row -> row.biosample }
        .filter { s -> !file("${samplesDir}/${s}/${s}.sample.json").exists() }
        .filter { s -> params.retryFailed || !file("${samplesDir}/${s}/${s}.failed.json").exists() }

    if (params.limit > 0) {
        pending_ch = pending_ch.take(params.limit)
    }

    db_ready = PREPARE_DB(channel.value(true))

    SAMPLE(pending_ch, db_ready)
}
