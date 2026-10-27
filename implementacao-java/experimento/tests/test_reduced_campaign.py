import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('reduced', Path(__file__).parents[1] / 'reduced_campaign.py')
reduced = importlib.util.module_from_spec(spec);spec.loader.exec_module(reduced)


class ReducedTests(unittest.TestCase):
    def test_pending_protocol_cannot_authorize_execution(self):
        checker_spec = importlib.util.spec_from_file_location('check_reduced', Path(__file__).parents[1] / 'check_reduced_plan.py')
        checker = importlib.util.module_from_spec(checker_spec);checker_spec.loader.exec_module(checker)
        with patch.object(checker.reduced, 'read', return_value={'schema_version': 2, 'status': 'pilot_pending'}), patch('sys.argv', ['check', 'plan.csv', '--require-unused']):
            with self.assertRaisesRegex(ValueError, 'execução definitiva proibida'): checker.main()

    def test_plan_has_65_unique_runs_and_five_repetitions(self):
        rows = reduced.make_plan({'seed': 20261026});reduced.validate_plan(rows)
        self.assertEqual(len(rows), 65)
        self.assertEqual(sum(r['profile'] == 'consumer-stop' for r in rows), 5)
        first = [rows[i]['variant'] for i in range(len(rows)) if rows[i]['profile'] != 'consumer-stop' and (i == 0 or (rows[i]['block'], rows[i]['profile'], rows[i]['rate']) != (rows[i-1]['block'], rows[i-1]['profile'], rows[i-1]['rate']))]
        self.assertEqual((first.count('sync'), first.count('async')), (15, 15))

    def test_pair_dataset_and_counts_are_checked(self):
        rows = reduced.make_plan({'seed': 20261026})
        with self.assertRaises(ValueError): reduced.validate_plan(rows[:-1])
        rows[1]['run_id'] = rows[0]['run_id']
        with self.assertRaises(ValueError): reduced.validate_plan(rows)

    def test_headroom_missing_is_failure_not_zero(self):
        policy = reduced.read(reduced.POLICY)
        self.assertEqual(len(reduced.headroom({}, policy)), 4)
        summary = {'instrumentation': {r: {'cpu_p95_percent_of_limit': 1, 'memory_max_percent_of_limit': 1} for r in ('generator', 'observer')}}
        self.assertEqual(reduced.headroom(summary, policy), [])
        summary['instrumentation']['generator']['cpu_p95_percent_of_limit'] = 99
        self.assertIn('generator:cpu_p95_percent_of_limit:headroom', reduced.headroom(summary, policy))

    def test_shorter_steady_requires_all_records_and_windows(self):
        s = dict(rate=48, measure_seconds=180, offered=8640, accepted=8640, stored_at_observation_end=8640, dropped_iterations_all_phases=0, dlq_terminal=0, pending_retained=0, accepted_unreconciled=0, integrity_mismatches=0, completed_per_second=48,
                 measurement_windows_10s=[{'unique_commits': 480, 'duration_seconds': 10} for _ in range(18)],
                 instrumentation=dict(database_error_samples=0, kafka_error_samples=0, clock_error_samples=0, pending_tail_slope_events_per_second=0, max_accepted_not_committed=1, max_kafka_lag=None, sample_gaps_ms={'p95': 1000}))
        self.assertEqual(reduced.steady_reasons(s), [])
        s['stored_at_observation_end'] -= 1
        self.assertIn('not_all_offered_accepted_stored', reduced.steady_reasons(s))


if __name__ == '__main__': unittest.main()
