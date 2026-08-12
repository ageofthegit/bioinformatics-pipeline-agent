"""Calculate transparent, deterministic FASTQ quality measurements."""

from pathlib import Path
from statistics import median
from typing import Any

from bioagent.tools.fastq import read_fastq


def phred_score(character: str) -> int:
    """Convert a standard Phred+33 quality character into a number."""
    return ord(character) - 33


def _quality_by_position(
    quality_totals: list[int], quality_counts: list[int]
) -> list[dict[str, float | int]]:
    return [
        {
            "position": index + 1,
            "mean_quality": round(total / quality_counts[index], 2),
            "bases_observed": quality_counts[index],
        }
        for index, total in enumerate(quality_totals)
    ]


def _trimming_recommendation(
    position_quality: list[dict[str, float | int]], quality_threshold: float
) -> str:
    """Recommend review of a low-quality tail without changing the input data."""
    first_low_tail_position: int | None = None

    for measurement in reversed(position_quality):
        if float(measurement["mean_quality"]) < quality_threshold:
            first_low_tail_position = int(measurement["position"])
        else:
            break

    if first_low_tail_position is None:
        return (
            "No trailing low-quality region was detected; no trimming is suggested "
            "by this check."
        )

    return (
        f"Review trimming from base position {first_low_tail_position}: the mean "
        f"quality of every remaining position is below Phred {quality_threshold:g}. "
        "No reads were modified."
    )


def analyse_fastq(path: Path, quality_threshold: float) -> dict[str, Any]:
    read_count = 0
    total_bases = 0
    gc_bases = 0
    n_bases = 0
    total_quality = 0
    low_quality_reads = 0
    read_lengths: list[int] = []
    quality_totals: list[int] = []
    quality_counts: list[int] = []

    for _, sequence, quality in read_fastq(path):
        scores = [phred_score(character) for character in quality]
        mean_read_quality = sum(scores) / len(scores)
        read_length = len(sequence)

        read_count += 1
        total_bases += read_length
        gc_bases += sequence.count("G") + sequence.count("C")
        n_bases += sequence.count("N")
        total_quality += sum(scores)
        read_lengths.append(read_length)

        while len(quality_totals) < read_length:
            quality_totals.append(0)
            quality_counts.append(0)
        for index, score in enumerate(scores):
            quality_totals[index] += score
            quality_counts[index] += 1

        if mean_read_quality < quality_threshold:
            low_quality_reads += 1

    minimum_read_length = min(read_lengths)
    maximum_read_length = max(read_lengths)
    median_read_length = float(median(read_lengths))
    read_length_range = maximum_read_length - minimum_read_length
    variation_percent = 100 * read_length_range / median_read_length
    unusual_length_variation = variation_percent > 10
    position_quality = _quality_by_position(quality_totals, quality_counts)

    if unusual_length_variation:
        length_warning = (
            f"Read lengths vary from {minimum_read_length} to {maximum_read_length} "
            f"bases ({variation_percent:.2f}% of the median length). Review whether "
            "this variation is expected before continuing."
        )
    else:
        length_warning = "Read lengths are consistent within the 10% variation limit."

    result: dict[str, Any] = {
        "read_count": read_count,
        "total_bases": total_bases,
        "mean_read_length": round(total_bases / read_count, 2),
        "median_read_length": round(median_read_length, 2),
        "shortest_read": minimum_read_length,
        "longest_read": maximum_read_length,
        "read_length_variation_percent": round(variation_percent, 2),
        "unusual_read_length_variation": unusual_length_variation,
        "read_length_warning": length_warning,
        "gc_percent": round(100 * gc_bases / total_bases, 2),
        "n_bases": n_bases,
        "n_percent": round(100 * n_bases / total_bases, 2),
        "mean_base_quality": round(total_quality / total_bases, 2),
        "quality_by_position": position_quality,
        "low_quality_reads": low_quality_reads,
        "low_quality_percent": round(100 * low_quality_reads / read_count, 2),
        "quality_threshold": quality_threshold,
    }
    result["trimming_recommendation"] = _trimming_recommendation(
        position_quality, quality_threshold
    )
    return result


def make_recommendation(result: dict[str, Any]) -> str:
    low_quality_percent = float(result["low_quality_percent"])

    if low_quality_percent == 0:
        quality_summary = "All reads meet the mean-quality threshold."
    elif low_quality_percent <= 10:
        quality_summary = (
            "A small number of reads are below the mean-quality threshold. "
            "Review them before continuing."
        )
    else:
        quality_summary = (
            "Many reads are below the mean-quality threshold. Do not continue until "
            "a human reviews the sample."
        )

    n_bases = int(result["n_bases"])
    n_percent = float(result["n_percent"])
    if n_bases:
        n_summary = (
            f"Unknown bases account for {n_percent:g}% of all bases "
            f"({n_bases} bases detected; percentage rounded)."
        )
    else:
        n_summary = "No unknown (N) bases were detected."

    return " ".join(
        [
            quality_summary,
            n_summary,
            str(result["read_length_warning"]),
            str(result["trimming_recommendation"]),
        ]
    )
