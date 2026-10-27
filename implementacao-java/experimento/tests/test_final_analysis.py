"""Regression checks for final descriptive aggregation, not new measurements."""
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import finalize_reduced_a1 as f
import render_final_tables as render


class FinalAnalysisTest(unittest.TestCase):
    def test_table_note_cannot_float_away(self):
        tex = render.table('Caption', 'test', ['A', 'B'], [['one', 2]], 'NOTE_BODY')
        self.assertLess(tex.index('NOTE_BODY'), tex.index(r'\end{table}'))
        self.assertIn(r'\begin{minipage}{\textwidth}', tex)

    def test_empty_is_not_zero(self):
        self.assertEqual(f.stats([None]), {'n': 0, 'values': []})
        self.assertIsNone(f.stats([2])['sd_sample'])

    def test_sample_sd_and_nearest_rank(self):
        s = f.stats([1, 2, 3])
        self.assertEqual((s['mean'], s['median'], s['sd_sample'], s['p95']), (2, 2, 1, 3))
        with self.assertRaises(ValueError):
            f.stats([float('nan')])

    def records(self):
        rows = []
        totals = ['offered', 'accepted', 'stored_final', 'nonpersisted_final', 'accepted_nonpersisted_final', 'dlq_terminal', 'pending_retained', 'accepted_unreconciled', 'stored_without_confirmed_http', 'commit_unobserved_n', 'database_duplicate_uuids', 'integrity_mismatches', 'dropped_iterations_all_phases']
        for b in range(1, 6):
            for variant in ['sync', 'async']:
                rows.append({**{k: 1 for k in f.METRICS + totals}, 'block': b, 'profile': 'postgres-stop', 'rate': 12,
                             'variant': variant, 'commit_primary_eligible': not (b == 3 and variant == 'sync'),
                             'stable_recovery_observed': True, 'dataset_id': str(b), 'run_id': str(b) + variant})
        return rows

    def test_primary_and_strict_populations(self):
        records = self.records(); pairs = f.pair_groups(records)
        for g in f.grouped(records):
            self.assertEqual(g['metrics']['commit_p95_ms']['n'], 4)
            self.assertEqual(g['metrics']['http_success_p95_ms']['n'], 5)
            self.assertEqual(g['totals']['offered'], 5)
        for g in f.grouped(records, strict=True):
            self.assertEqual(g['metrics']['http_success_p95_ms']['n'], 4)
            self.assertEqual(g['totals']['offered'], 4)
            self.assertEqual(g['eligible_blocks_for_totals'], [1, 2, 4, 5])
        self.assertEqual(f.paired_comparisons(pairs)[0]['metrics']['commit_p95_ms']['n'], 4)
        self.assertEqual(f.grouped(records, sensitivity=True)[0]['metrics']['commit_p95_ms']['n'], 5)

    def test_throughput_interval_difference(self):
        records = self.records()
        for r in records:
            r['throughput_lower'], r['throughput_upper'] = (2, 3) if r['variant'] == 'sync' else (4, 4)
        out = f.paired_comparisons(f.pair_groups(records))[0]['metrics']
        self.assertEqual(out['throughput_delta_lower']['values'], [1] * 5)
        self.assertEqual(out['throughput_delta_upper']['values'], [2] * 5)

    def test_components_and_missing_batch_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = '1970-01-01T00:00:01Z\ttcc-entrega04-sync-api-1\t2%\t1GiB / 2GiB\n'
            (root / 'resources.tsv').write_text(text + '1970-01-01T00:00:01Z\ttcc-entrega04-postgres-1\t3%\t10MiB / 512MiB\n')
            meta = {'measurement_start_ms': '0', 'measure_seconds': '2'}
            out = f.business_resources(root, meta, 'sync')
            self.assertEqual(out['cpu_percent']['mean'], 5)
            self.assertEqual(out['memory_mib']['mean'], 1034)
            (root / 'resources.tsv').write_text(text)
            with self.assertRaises(ValueError):
                f.business_resources(root, meta, 'sync')


if __name__ == '__main__': unittest.main()
