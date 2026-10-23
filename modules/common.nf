/*
 * ============================================================
 * TASK ENVIRONMENT FOR bin/ SCRIPTS
 * Nextflow does not export task.cpus / task.memory: the scripts
 * read their thread count (NXF_TASK_CPUS), JVM heap cap
 * (BRSEQTB_JAVA_XMX) and reads directory (BRSEQTB_READS) from
 * these variables.
 *
 * javaShare: fraction of task.memory per JVM (0.8 when one JVM
 * runs at a time; lower when several run in parallel in one task)
 * ============================================================
 */

def taskEnv(task, readsDir, javaShare = 0.8) {
    def xmx = task.memory ? "${Math.round(task.memory.toMega() * javaShare)}m" : ''
    return """\
    export NXF_TASK_CPUS=${task.cpus}
    export BRSEQTB_JAVA_XMX=${xmx}
    export BRSEQTB_READS="${file(readsDir)}"
    """.stripIndent()
}
