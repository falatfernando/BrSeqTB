/*
 * ============================================================
 * TASK ENVIRONMENT FOR bin/ SCRIPTS
 * Nextflow does not export task.cpus / task.memory: the scripts
 * read their thread count (NXF_TASK_CPUS), JVM heap cap
 * (BRSEQTB_JAVA_XMX) and reads directory (BRSEQTB_READS) from
 * these variables.
 *
 * javaShare: fraction of task.memory per JVM for tools that may run
 * in parallel inside one task (GATK in bulk mode); tools that always
 * run alone (Trimmomatic, Picard, snpEff) use BRSEQTB_JAVA_XMX_SOLO,
 * 80% of task.memory
 * ============================================================
 */

def taskEnv(task, readsDir, javaShare = 0.8) {
    def xmx = task.memory ? "${Math.round(task.memory.toMega() * javaShare)}m" : ''
    def xmxSolo = task.memory ? "${Math.round(task.memory.toMega() * 0.8)}m" : ''
    return """\
    export NXF_TASK_CPUS=${task.cpus}
    export BRSEQTB_JAVA_XMX=${xmx}
    export BRSEQTB_JAVA_XMX_SOLO=${xmxSolo}
    export BRSEQTB_READS="${file(readsDir)}"
    """.stripIndent()
}
