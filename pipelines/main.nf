params {
    input: Path
    quality_threshold: Float = 20.0
}

process FASTQ_QC {
    input:
    path fastq
    path agent_source
    val quality_threshold

    output:
    path 'qc.json'

    script:
    """
    python3 -m bioagent.qc_command \
        --input ${fastq} \
        --output qc.json \
        --quality-threshold ${quality_threshold}
    """
}

workflow {
    main:
    fastq_ch = channel.fromPath(params.input, checkIfExists: true)
    agent_source_ch = channel.fromPath("${projectDir}/../bioagent", checkIfExists: true)
    FASTQ_QC(fastq_ch, agent_source_ch, params.quality_threshold)

    publish:
    qc_json = FASTQ_QC.out
}

output {
    qc_json {
        path '.'
        mode 'copy'
    }
}
