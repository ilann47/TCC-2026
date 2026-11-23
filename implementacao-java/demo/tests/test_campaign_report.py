"""Read-only regression against the canonical public campaign, no raw data or Docker."""
import json
import statistics
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import campaign_report as report


class CampaignReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=report.APP/report.RELATIVE
        cls.names=['group-summary.json','per-run.json','paired.json','strict-sensitivity.json','partial-latency-sensitivity.json','catalog.json','SHA256SUMS']
        cls.before={name:report.digest(cls.source/name) for name in cls.names}
        cls.data=report.build_report(full_verify=False)

    def group(self,profile,rate,variant,strict=False):
        return next(group for group in self.data['strict_groups' if strict else 'groups'] if group['profile']==profile and group['rate']==rate and group['variant']==variant)

    def test_classification_and_independent_units(self):
        self.assertEqual(len(self.data['runs']),65)
        self.assertEqual(len(self.data['groups']),13)
        self.assertEqual(self.data['catalog']['complete_original_evidence'],64)
        self.assertEqual(self.data['catalog']['partial_commit_timing'],1)
        self.assertEqual(self.data['method']['pairs'],30)
        self.assertEqual(self.data['method']['consumer_only_runs'],5)

    def test_primary_commit_excludes_both_members_of_pair(self):
        for variant in ('sync','async'):
            group=self.group('postgres-stop',12,variant)
            self.assertEqual(group['metrics']['commit_p95_ms']['n'],4)
            self.assertEqual(group['metrics']['commit_p99_ms']['n'],4)
            self.assertEqual(group['metrics']['http_success_p95_ms']['n'],5)

    def test_strict_sensitivity_excludes_pair_from_other_metrics(self):
        for variant in ('sync','async'):
            group=self.group('postgres-stop',12,variant,True)
            self.assertEqual(group['metrics']['http_success_p95_ms']['n'],4)
            self.assertEqual(group['metrics']['business_cpu_mean_percent']['n'],4)

    def test_qualified_run_does_not_become_valid(self):
        self.assertFalse(self.data['partial']['original_instrument_valid'])
        self.assertEqual(self.data['partial']['missing'],1)
        self.assertEqual((self.data['partial']['observed'],self.data['partial']['stored']),(1666,1667))
        self.assertAlmostEqual(self.data['partial']['throughput_lower'],1666/180)
        self.assertAlmostEqual(self.data['partial']['throughput_upper'],1667/180)

    def test_p99_is_derived_from_run_units_not_pooled_events(self):
        group=self.group('steady',48,'async')
        values=[run['http_success_p99_ms'] for run in self.data['runs'] if run['profile']=='steady' and run['rate']==48 and run['variant']=='async']
        self.assertEqual(group['metrics']['http_success_p99_ms']['n'],5)
        self.assertAlmostEqual(group['metrics']['http_success_p99_ms']['mean'],statistics.mean(values))

    def test_original_aggregation_files_unchanged(self):
        self.assertEqual(self.before,{name:report.digest(self.source/name) for name in self.names})

    def test_http_accounting_and_unfavorable_results_retained(self):
        for run in self.data['runs']:
            self.assertEqual(sum(run['http_status_counts'].values()),run['offered'])
        self.assertEqual(self.group('postgres-stop',12,'async')['totals']['dlq_terminal'],14)
        self.assertEqual(self.group('postgres-stop',12,'async')['stable_recovery_observed_n'],1)
        self.assertEqual(self.group('consumer-stop',12,'async')['totals']['stored_final'],10801)

    def test_tampered_index_entry_has_no_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'example.json').write_text('{}')
            with self.assertRaises(ValueError):
                report.read_verified(root,{'example.json':'0'*64},'example.json')

    def test_missing_metric_is_not_zero(self):
        self.assertFalse(report.eligible({'profile':'steady','block':1,'paired_commit_primary_included':True,'commit_p95_ms':None},'commit_p95_ms'))
        self.assertEqual(report.stats([]),{'n':0,'values':[]})


if __name__=='__main__':unittest.main()
