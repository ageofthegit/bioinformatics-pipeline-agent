import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.download_public_dataset import (
    MANIFEST_PATH,
    available_accessions,
    load_manifest,
    manifest_path_for,
    verify_compressed_file,
)
from scripts.check_public_dataset import independently_count_fastq


class PublicDatasetTests(unittest.TestCase):
    def test_approved_catalog_contains_four_public_datasets(self) -> None:
        accessions = available_accessions()

        self.assertEqual(
            accessions,
            ["DRR002057", "ERR1229325", "SRR12966849", "SRR29651967"],
        )
        for accession in accessions:
            manifest = load_manifest(manifest_path_for(accession))
            self.assertEqual(manifest["accession"], accession)
            self.assertIn("public non-human", manifest["data_classification"])
            self.assertLess(manifest["compressed_file"]["bytes"], 25_000_000)
            self.assertEqual(len(manifest["compressed_file"]["md5"]), 32)

    def test_manifest_lookup_rejects_unknown_or_unsafe_accession(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown approved accession"):
            manifest_path_for("SRR000000")
        with self.assertRaisesRegex(ValueError, "Unsafe ENA accession"):
            manifest_path_for("../manifest")

    def test_manifest_records_required_provenance(self) -> None:
        manifest = load_manifest()

        self.assertEqual(manifest["accession"], "DRR002057")
        self.assertEqual(manifest["scientific_name"], "Escherichia coli")
        self.assertIn("public non-human", manifest["data_classification"])
        self.assertLess(manifest["compressed_file"]["bytes"], 25_000_000)
        self.assertEqual(len(manifest["compressed_file"]["md5"]), 32)
        self.assertTrue(manifest["source_record"].startswith("https://www.ebi.ac.uk/"))
        self.assertTrue(MANIFEST_PATH.is_file())

    def test_compressed_verification_accepts_matching_file(self) -> None:
        content = b"small public test fixture"
        expected_md5 = hashlib.md5(content, usedforsecurity=False).hexdigest()
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "fixture.fastq.gz"
            path.write_bytes(content)

            verify_compressed_file(path, len(content), expected_md5)

    def test_compressed_verification_rejects_changed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "fixture.fastq.gz"
            path.write_bytes(b"changed")

            with self.assertRaisesRegex(ValueError, "MD5 mismatch"):
                verify_compressed_file(path, len(b"changed"), "0" * 32)

    def test_independent_fastq_count_uses_a_separate_code_path(self) -> None:
        fastq = "@one\nACGT\n+\nIIII\n@two\nNN\n+\n!!\n"
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "fixture.fastq"
            path.write_text(fastq, encoding="utf-8")

            self.assertEqual(independently_count_fastq(path), (2, 6))


if __name__ == "__main__":
    unittest.main()
