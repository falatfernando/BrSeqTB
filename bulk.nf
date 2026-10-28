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
 * IS6110 insertion sites (IS Sentinel, --issentinel, on by default)
 * run as a separate task per sample with its own env and its own
 * alignment of the raw reads to the masked reference + IS6110 decoy;
 * results in <outdir>/is6110/<id>.
 *
 * Re-running the same command continues where it stopped:
 * samples with <outdir>/samples/<id>/<id>.sample.json (and
 * <outdir>/is6110/<id>/<id>.issentinel.json) are skipped, as are
 * those with <id>.failed.json, unless --retryFailed.
 * ============================================================
 */

nextflow.enable.dsl = 2

params.manifest    = null   // TSV with a 'biosample' header (make_manifest_validate.py)
params.readsDir    = null
params.outdir      = null
params.lofreqMinAf = 0.00
params.retryFailed = false  // re-run samples that have a <id>.failed.json
params.limit       = 0      // run at most this many pending samples (0 = all)
params.issentinel  = true   // IS6110 insertion sites (IS Sentinel), own env and alignment

// IS Sentinel gates (nf-core-issentinel defaults)
params.isMaxDist       = 10
params.isMinPeIso      = 10
params.isMinSrIso      = 5
params.isMinTotalClust = 15
params.isMinSrOnly     = 20

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

/*
 * IS Sentinel masked reference (16 IS6110 copies -> N, + IS6110 decoy)
 */
process PREPARE_IS {

    tag "issentinel-db"

    input:
        val token

    output:
        val true

    script:
    """
    bash "${projectDir}/bin/issentinel/prepare_issentinel_db.sh"
    """
}

/*
 * IS6110 insertion sites: raw reads -> masked reference -> Delly ->
 * candidates; independent of SAMPLE, published to <outdir>/is6110/<id>
 */
process ISSENTINEL {

    tag { biosample }

    input:
        val biosample
        val db_ready

    output:
        path "published.txt"

    script:
    def finalAttempt = task.attempt >= (task.maxRetries ?: 0) + 1
    """
    ${taskEnv(task, params.readsDir)}
    export ISSENTINEL_MAX_DIST=${params.isMaxDist}
    export ISSENTINEL_MIN_PE_ISO=${params.isMinPeIso}
    export ISSENTINEL_MIN_SR_ISO=${params.isMinSrIso}
    export ISSENTINEL_MIN_TOTAL_CLUST=${params.isMinTotalClust}
    export ISSENTINEL_MIN_SR_ONLY=${params.isMinSrOnly}
    bash "${projectDir}/bin/bulk_task.sh" ${biosample} "results/${biosample}" ${finalAttempt} "${file(params.outdir)}/is6110" issentinel_sample.sh
    """
}

/*
 * Samples of the manifest without a finished result in <outdir>/<subdir>
 * (done marker <id>.<doneSuffix>; <id>.failed.json unless --retryFailed)
 */
def pending(manifest_ch, subdir, doneSuffix) {
    def dir = file("${params.outdir}/${subdir}")
    def ch = manifest_ch
        .filter { s -> !file("${dir}/${s}/${s}.${doneSuffix}").exists() }
        .filter { s -> params.retryFailed || !file("${dir}/${s}/${s}.failed.json").exists() }
    return params.limit > 0 ? ch.take(params.limit) : ch
}

workflow {

    if (!params.manifest || !params.readsDir || !params.outdir) {
        error "bulk.nf needs --manifest, --readsDir and --outdir"
    }

    manifest_ch = channel.fromPath(params.manifest)
        .splitCsv(header: true, sep: '\t')
        .map { row -> row.biosample }

    db_ready = PREPARE_DB(channel.value(true))
    SAMPLE(pending(manifest_ch, 'samples', 'sample.json'), db_ready)

    if (params.issentinel) {
        is_ready = PREPARE_IS(channel.value(true))
        ISSENTINEL(pending(manifest_ch, 'is6110', 'issentinel.json'), is_ready)
    }
}
