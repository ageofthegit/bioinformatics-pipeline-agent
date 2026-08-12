import tempfile
import unittest
from pathlib import Path

from bioagent.tools.fastq import validate_fastq
from bioagent.tools.qc import analyse_fastq, make_recommendation


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
SAMPLE_FASTQ = PROJECT_DIRECTORY / "data" / "sample.fastq"


class FastqTests(unittest.TestCase):
    def write_fastq(self, directory: str, contents: str) -> Path:
        path = Path(directory) / "test.fastq"
        path.write_text(contents, encoding="utf-8")
        return path

    def test_sample_file_is_valid(self) -> None:
        validation = validate_fastq(SAMPLE_FASTQ)
        self.assertEqual(validation["read_count"], 4)

    def test_quality_control_measurements(self) -> None:
        result = analyse_fastq(SAMPLE_FASTQ, quality_threshold=20)
        self.assertEqual(result["read_count"], 4)
        self.assertEqual(result["total_bases"], 48)
        self.assertEqual(result["low_quality_reads"], 0)
        self.assertEqual(result["mean_read_length"], 12)
        self.assertEqual(result["median_read_length"], 12)
        self.assertEqual(len(result["quality_by_position"]), 12)
        self.assertFalse(result["unusual_read_length_variation"])

    def test_unknown_bases_are_measured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_fastq(directory, "@read-1\nANNT\n+\nIIII\n")
            result = analyse_fastq(path, quality_threshold=20)

        self.assertEqual(result["n_bases"], 2)
        self.assertEqual(result["n_percent"], 50)
        self.assertIn("50%", make_recommendation(result))

    def test_small_unknown_base_count_is_not_hidden_by_rounding(self) -> None:
        recommendation = make_recommendation(
            {
                "low_quality_percent": 3.78,
                "n_bases": 21,
                "n_percent": 0.0,
                "read_length_warning": "Lengths are consistent.",
                "trimming_recommendation": "No trimming suggested.",
            }
        )

        self.assertIn("21 bases detected", recommendation)
        self.assertNotIn("No unknown", recommendation)

    def test_low_quality_tail_produces_trimming_guidance_without_modifying_input(self) -> None:
        contents = "@read-1\nACGTACGT\n+\nII!!!!!!\n"
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_fastq(directory, contents)
            result = analyse_fastq(path, quality_threshold=20)
            recommendation = make_recommendation(result)
            unchanged_contents = path.read_text(encoding="utf-8")

        self.assertEqual(result["low_quality_reads"], 1)
        self.assertEqual(result["quality_by_position"][0]["mean_quality"], 40)
        self.assertEqual(result["quality_by_position"][2]["mean_quality"], 0)
        self.assertIn("base position 3", result["trimming_recommendation"])
        self.assertIn("No reads were modified", result["trimming_recommendation"])
        self.assertIn("Many reads are below", recommendation)
        self.assertEqual(unchanged_contents, contents)

    def test_variable_read_lengths_produce_clear_warning(self) -> None:
        contents = "@short\nACGT\n+\nIIII\n@long\nACGTACGT\n+\nIIIIIIII\n"
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_fastq(directory, contents)
            result = analyse_fastq(path, quality_threshold=20)

        self.assertEqual(result["shortest_read"], 4)
        self.assertEqual(result["longest_read"], 8)
        self.assertEqual(result["median_read_length"], 6)
        self.assertTrue(result["unusual_read_length_variation"])
        self.assertIn("vary from 4 to 8", result["read_length_warning"])
        self.assertEqual(result["quality_by_position"][7]["bases_observed"], 1)

    def test_incomplete_record_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_fastq(directory, "@read-1\nACGT\n+\n")
            with self.assertRaisesRegex(ValueError, "Record 1 is incomplete"):
                validate_fastq(path)

    def test_sequence_quality_length_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_fastq(directory, "@read-1\nACGT\n+\nIII\n")
            with self.assertRaisesRegex(ValueError, "4 bases but 3 quality"):
                validate_fastq(path)

    def test_unexpected_base_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_fastq(directory, "@read-1\nACXT\n+\nIIII\n")
            with self.assertRaisesRegex(ValueError, "unexpected DNA base"):
                validate_fastq(path)


if __name__ == "__main__":
    unittest.main()
