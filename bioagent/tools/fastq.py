"""Read and validate FASTQ files.

A FASTQ record contains four lines:
1. a name beginning with @
2. a DNA sequence
3. a separator beginning with +
4. one quality character for each DNA base
"""

from collections.abc import Iterator
from pathlib import Path


FastqRecord = tuple[str, str, str]


def read_fastq(path: Path) -> Iterator[FastqRecord]:
    with path.open(encoding="utf-8") as fastq_file:
        record_number = 0

        while True:
            name = fastq_file.readline().rstrip("\n")
            if not name:
                break

            sequence = fastq_file.readline().rstrip("\n").upper()
            separator = fastq_file.readline().rstrip("\n")
            quality = fastq_file.readline().rstrip("\n")
            record_number += 1

            if not sequence or not separator or not quality:
                raise ValueError(f"Record {record_number} is incomplete")
            if not name.startswith("@"):
                raise ValueError(f"Record {record_number} name must start with @")
            if not separator.startswith("+"):
                raise ValueError(f"Record {record_number} separator must start with +")
            if len(sequence) != len(quality):
                raise ValueError(
                    f"Record {record_number} has {len(sequence)} bases but "
                    f"{len(quality)} quality characters"
                )
            if set(sequence) - set("ACGTN"):
                raise ValueError(f"Record {record_number} contains an unexpected DNA base")

            yield name[1:], sequence, quality


def validate_fastq(path: Path) -> dict[str, int | str]:
    if not path.exists():
        raise ValueError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    read_count = sum(1 for _ in read_fastq(path))
    if read_count == 0:
        raise ValueError("FASTQ file contains no reads")

    return {
        "status": "valid",
        "read_count": read_count,
        "file_size_bytes": path.stat().st_size,
    }

