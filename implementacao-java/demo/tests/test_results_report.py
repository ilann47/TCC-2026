"""The unified UI reads exactly the same verified scientific datasets as Vite."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import results_report


class ResultsReportTests(unittest.TestCase):
    def test_exploratory_appendix_does_not_mutate_canonical_report(self):
        canonical = {"catalog": {"complete_original_evidence": 64, "partial_commit_timing": 1}}
        appendix = {"original_observed": 1, "exploratory_observed": 5, "runs": [
            {"block": 1, "dlq_terminal": 3, "original": {"observed": False},
             "exploratory": {"observed": True, "timing": {"confirmed_after_restore_s": 38.77}}}
        ]}
        with patch.object(results_report, "campaign_report", return_value=canonical), \
             patch.object(results_report, "load_index", return_value={"recuperacao-exploratoria.json": "verified-hash"}), \
             patch.object(results_report, "read_verified", return_value=appendix) as verify:
            report = results_report.build_report()
        self.assertNotIn("exploratory_recovery", canonical)
        self.assertEqual(report["catalog"], canonical["catalog"])
        self.assertEqual(report["exploratory_recovery"]["original"], 1)
        self.assertEqual(report["exploratory_recovery"]["exploratory"], 5)
        self.assertEqual(report["exploratory_recovery"]["runs"][0]["dlq_terminal"], 3)
        self.assertEqual(report["exploratory_recovery"]["sha256"], "verified-hash")
        verify.assert_called_once()

    def test_bad_exploratory_checksum_is_not_ignored(self):
        with patch.object(results_report, "campaign_report", return_value={}), \
             patch.object(results_report, "load_index", return_value={}), \
             patch.object(results_report, "read_verified", side_effect=ValueError("checksum")):
            with self.assertRaisesRegex(ValueError, "checksum"):
                results_report.build_report()
