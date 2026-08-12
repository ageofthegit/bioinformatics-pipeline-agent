# Approved Public Test Datasets

**Checked:** 11 August 2026  
**Source:** European Nucleotide Archive (ENA)

These public, non-human datasets were selected for separate quality-control
tests. The downloaded files are ignored by Git; each small manifest preserves
the ENA source, study, sample, size, read count, and published MD5.

| Test order | Accession | Description | Compressed | Extracted | Reads |
|---:|---|---|---:|---:|---:|
| 1 | `ERR1229325` | *S. cerevisiae* reduced-representation sequencing | 3,000,757 B | 12,849,560 B | 122,511 |
| 2 | `SRR29651967` | Rhizosphere *P. fluorescens* 16S-style sequencing | 4,404,739 B | 48,488,978 B | 53,841 |
| 3 | `SRR12966849` | Laboratory-evolved *E. coli* WGS | 23,595,520 B | 106,842,476 B | 629,082 |

ENA labels `SRR29651967` as WGS while its study and experiment titles describe
16S sequencing. Both facts are retained in its manifest. No result should be
assumed to pass before the report is reviewed.

## Test one sample

Start with the smallest learning case:

```bash
cd "/path/to/bioinformatics-pipeline-agent"
source .venv/bin/activate
python run.py data/public/ERR1229325.fastq --explain-with offline-demo
```

After reviewing the report, use its run folder in the independent check:

```bash
python -m scripts.check_public_dataset runs/run-... --accession ERR1229325
```

Then repeat with `SRR29651967`, followed by `SRR12966849`. Test and review one
before starting the next so each decision and report stays distinct.

## Verified downloads

| Accession | Published and verified MD5 |
|---|---|
| `ERR1229325` | `cb62373776eaa45fa49a744ac5cd4ae7` |
| `SRR29651967` | `58d2ea4c4b88363224785382c857e220` |
| `SRR12966849` | `c9253d16651675982d9f1908d5af8e36` |
