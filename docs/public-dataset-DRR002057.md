# Phase 8 Public Dataset — DRR002057

**Checked:** 11 August 2026  
**Source:** [European Nucleotide Archive run DRR002057](https://www.ebi.ac.uk/ena/browser/view/DRR002057)  
**Study:** [PRJDB2622](https://www.ebi.ac.uk/ena/browser/view/PRJDB2622)

## Provenance and permission

- Organism: *Escherichia coli* BW4005; non-human bacterial genomic data.
- Experiment: whole-genome resequencing using 454 GS FLX Titanium.
- Layout: single-read, archive-generated FASTQ.
- ENA/INSDC policy: public records have free and unrestricted access; the original submission should be cited as good scientific practice.
- File: `DRR002057.fastq.gz`, 14,215,821 bytes compressed and 82,557,231 bytes extracted.
- Published MD5: `8745076d647657792cd2cffbbe0a34e2` — verified locally.
- Downloaded data is ignored by Git. The small provenance manifest remains versioned.

## Demonstration result

Run: `run-20260811-061758-943169` (`accepted_for_demo`, not human approval)

| Measurement | Result |
|---|---:|
| Reads | 128,518 |
| Bases in archive-generated FASTQ | 38,828,067 |
| Mean base quality | 7.44 |
| Reads below Phred 20 | 113,085 (87.99%) |
| GC bases | 50.61% |
| Unknown bases | 22,494 (0.06%) |
| Read-length range | 27–568 |

The agent did not treat successful execution as good data. It warned that many
reads were below the threshold and said a person should not continue without
review.

## Independent checks

- ENA's published read count is 128,518. The agent and a separate streaming count both matched it.
- A separate streaming count found 38,828,067 bases, exactly matching the agent.
- Python and Nextflow produced identical QC results for this file.
- ENA's run-level `base_count` field is 73,997,626, which does not match the archive-generated FASTQ. This discrepancy is shown rather than treated as a pass; its cause was not established.

## Reproduce

```bash
cd "/path/to/bioinformatics-pipeline-agent"
source .venv/bin/activate
python -m scripts.download_public_dataset
python run.py data/public/DRR002057.fastq --explain-with offline-demo
```

The second command is interactive and records real human choices. Do not use
`--yes` if the purpose is human approval.
