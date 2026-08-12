"""Download and verify approved public ENA FASTQ datasets."""

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from bioagent.tools.fastq import validate_fastq


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
MANIFEST_DIRECTORY = PROJECT_DIRECTORY / "data" / "public"
MANIFEST_PATH = MANIFEST_DIRECTORY / "DRR002057.manifest.json"


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def available_accessions() -> list[str]:
    return sorted(
        path.name.removesuffix(".manifest.json")
        for path in MANIFEST_DIRECTORY.glob("*.manifest.json")
    )


def manifest_path_for(accession: str) -> Path:
    if not accession.isalnum():
        raise ValueError(f"Unsafe ENA accession: {accession}")
    path = MANIFEST_DIRECTORY / f"{accession}.manifest.json"
    if not path.is_file():
        raise ValueError(
            f"Unknown approved accession: {accession}. "
            f"Available: {', '.join(available_accessions())}"
        )
    return path


def md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_compressed_file(path: Path, expected_bytes: int, expected_md5: str) -> None:
    if path.stat().st_size != expected_bytes:
        raise ValueError(
            f"Downloaded size mismatch: expected {expected_bytes}, got {path.stat().st_size}"
        )
    actual_md5 = md5_file(path)
    if actual_md5 != expected_md5:
        raise ValueError(
            f"Downloaded MD5 mismatch: expected {expected_md5}, got {actual_md5}"
        )


def download_verified_file(
    url: str,
    destination: Path,
    expected_bytes: int,
    expected_md5: str,
) -> None:
    if destination.exists():
        verify_compressed_file(destination, expected_bytes, expected_md5)
        print(f"Verified existing download: {destination}")
        return

    temporary_path = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": "bioinformatics-pipeline-agent/1"})
    try:
        with urlopen(request, timeout=60) as response:
            with temporary_path.open("wb") as output:
                shutil.copyfileobj(response, output, length=1024 * 1024)
        verify_compressed_file(temporary_path, expected_bytes, expected_md5)
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def decompress_fastq(source: Path, destination: Path) -> None:
    temporary_path = destination.with_suffix(destination.suffix + ".part")
    try:
        with gzip.open(source, "rb") as compressed:
            with temporary_path.open("wb") as output:
                shutil.copyfileobj(compressed, output, length=1024 * 1024)
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def prepare_public_dataset(manifest_path: Path = MANIFEST_PATH) -> Path:
    manifest = load_manifest(manifest_path)
    compressed = manifest["compressed_file"]
    data_directory = manifest_path.parent
    data_directory.mkdir(parents=True, exist_ok=True)
    compressed_path = data_directory / compressed["name"]
    fastq_path = PROJECT_DIRECTORY / manifest["local_fastq"]

    download_verified_file(
        compressed["url"],
        compressed_path,
        compressed["bytes"],
        compressed["md5"],
    )
    if not fastq_path.exists():
        decompress_fastq(compressed_path, fastq_path)
    validation = validate_fastq(fastq_path)
    if validation["read_count"] != manifest["expected_read_count"]:
        raise ValueError(
            "FASTQ read count does not match the authoritative ENA metadata"
        )
    print(f"Verified MD5: {compressed['md5']}")
    print(f"Validated {validation['read_count']} reads")
    print(f"Ready: {fastq_path}")
    return fastq_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and verify one or all approved public ENA datasets."
    )
    parser.add_argument(
        "accessions",
        nargs="*",
        default=["DRR002057"],
        help="ENA accessions, or 'all'. Default: DRR002057",
    )
    return parser.parse_args()


def main() -> None:
    requested = parse_args().accessions
    try:
        if "all" in requested:
            if requested != ["all"]:
                raise ValueError("Use 'all' by itself")
            requested = available_accessions()
        for accession in requested:
            print(f"\nPreparing {accession}")
            prepare_public_dataset(manifest_path_for(accession))
    except (OSError, ValueError) as error:
        print(f"Dataset preparation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
