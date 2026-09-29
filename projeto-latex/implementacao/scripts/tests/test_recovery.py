"""Synthetic temporal fixtures only; these are not pilot/experimental results."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recovery import analyze_recovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.config = {'run_id': 'recovery-fixture', 'profile': 'pilot', 'variant': 'async',
            'warmup_seconds': 0, 'measurement_seconds': 20, 'fault': {'service': 'postgres'},
            'phases': [{'name': 'measurement', 'analysis_phase': 'measurement', 'start_seconds': 0,
                        'seconds': 20, 'rate': 1}]}
        self.manifest = {'run_id': 'recovery-fixture', 'load_exit_code': 0,
            'application_log_export_exit_code': 0, 'errors': [], 'fault_errors': [],
            'observation_end_ns': self.ns(21), 'fault_events': [
                {'action': 'stopped', 'service': 'postgres', 'wall_time_ns': self.ns(2)},
                {'action': 'started', 'service': 'postgres', 'wall_time_ns': self.ns(4)}]}
        self.generator, self.app, self.lag = [], [], []
        self.criteria = {'sustained_window_seconds': 3, 'rate_fraction': 1,
                         'reference_rate_events_s': 1, 'throughput_bin_seconds': 1}

    @staticmethod
    def ns(seconds):
        return round((1000 + seconds) * 1_000_000_000)

    def event(self, name, send, *, commit=None, dlq=None, http=202, commit_status='persisted'):
        common = {'run_id': 'recovery-fixture', 'event_id': name, 'phase': 'measurement', 'segment': 'measurement'}
        self.generator.append(dict(common, kind='request_sent', sent_at_ms=(1000 + send) * 1000,
                                   phase_start_ms=1_000_000, phase_seconds=20))
        if http is not None:
            self.generator.append(dict(common, kind='http_response', http_status=http,
                                       finished_at_ms=(1000 + send + .001) * 1000))
        if commit is not None:
            self.app.append(dict(common, milestone='commit_completed', status=commit_status,
                                 wall_time_ns=self.ns(commit)))
        if dlq is not None:
            self.app.append(dict(common, milestone='dlq_acknowledged', wall_time_ns=self.ns(dlq)))

    def ready(self, second, probe='pg_isready', **extra):
        self.manifest['fault_events'].append(dict(action='ready', service='postgres',
            wall_time_ns=self.ns(second), probe=probe, **extra))

    def analyze(self):
        return analyze_recovery(self.config, self.manifest, self.generator, self.app, self.lag, **self.criteria)

    def steady(self):
        for index, second in enumerate((4.1, 5.1, 6.1)):
            self.event(str(index), second, commit=second + .1)

    def test_consecutive_bins_distinguish_onset_and_confirmation(self):
        self.steady()
        self.ready(4.5)
        result = self.analyze()
        episode = result['episodes'][0]
        recovery = episode['throughput_recovery']
        self.assertEqual(recovery['status'], 'observed')
        self.assertEqual(recovery['window_onset_seconds_after_start_command'], 0)
        self.assertEqual(recovery['confirmation_seconds_after_start_command'], 3)
        self.assertEqual(recovery['confirmation_seconds_after_ready_probe'], 2.5)
        self.assertEqual(episode['dependency_ready']['seconds_after_start_command'], .5)
        self.assertFalse(result['scientific_conclusion_produced'])

    def test_start_command_and_first_commit_do_not_fabricate_readiness(self):
        self.steady()
        episode = self.analyze()['episodes'][0]
        self.assertEqual(episode['dependency_ready']['status'], 'not_observed')
        self.assertIsNone(episode['dependency_ready']['wall_time_ns'])
        self.assertEqual(episode['first_post_restart_new_persistence']['status'], 'observed')

    def test_failed_or_unnamed_ready_probe_is_not_readiness(self):
        self.steady()
        self.ready(4.2, probe='')
        self.ready(4.3, exit_code=1)
        self.assertEqual(self.analyze()['episodes'][0]['dependency_ready']['status'], 'not_observed')

    def test_average_window_burst_cannot_masquerade_as_sustained_rate(self):
        for index in range(3):
            self.event(str(index), 4.1, commit=4.2)
        recovery = self.analyze()['episodes'][0]['throughput_recovery']
        self.assertEqual(recovery['bins'][0]['throughput_events_s'], 3)
        self.assertEqual(recovery['status'], 'right_censored_recovery_not_observed')

    def test_dlq_resolves_pending_but_is_not_successful_drain_or_throughput(self):
        self.event('failed', 3.1, dlq=4.5)
        self.lag = [{'wall_time_ns': self.ns(4.6), 'exit_code': 0, 'partitions': [{'lag': 0}]}]
        result = self.analyze()
        episode = result['episodes'][0]
        cohort = episode['restart_cohort']
        self.assertEqual(cohort['successful_drain']['status'], 'terminal_dlq_present_not_successfully_drained')
        self.assertEqual(cohort['resolved_as_persisted_or_dlq']['seconds_after_start_command'], .5)
        self.assertEqual(episode['first_observed_zero_lag']['status'], 'observed')
        self.assertNotEqual(episode['throughput_recovery']['status'], 'observed')
        self.assertEqual(result['backlog_timeline'][-1]['accepted_not_persisted_uuids'], 1)
        self.assertEqual(result['backlog_timeline'][-1]['accepted_unresolved_excluding_dlq_uuids'], 0)

    def test_dlq_before_restart_does_not_create_successful_zero_second_recovery(self):
        self.event('failed', 3.1, dlq=3.5)
        cohort = self.analyze()['episodes'][0]['restart_cohort']
        self.assertEqual(cohort['terminal_dlq_already_at_restart'], 1)
        self.assertIsNone(cohort['successful_drain']['wall_time_ns'])
        self.assertEqual(cohort['resolved_as_persisted_or_dlq']['seconds_after_start_command'], 0)

    def test_fixed_cohort_successful_drain_is_separate_from_incoming_load(self):
        self.event('old', 3, commit=6)
        self.event('new_pending', 5)
        cohort = self.analyze()['episodes'][0]['restart_cohort']
        self.assertEqual(cohort['event_ids'], ['old'])
        self.assertEqual(cohort['successful_drain']['seconds_after_start_command'], 2)
        self.assertEqual(cohort['unresolved_by_observation_end'], 0)

    def test_duplicate_commits_never_inflate_new_persistence_throughput(self):
        self.event('existing', 4.1, commit=4.2, commit_status='duplicate')
        self.app.extend([copy.deepcopy(self.app[0]) for _ in range(4)])
        recovery = self.analyze()['episodes'][0]['throughput_recovery']
        self.assertEqual(sum(b['new_persisted_uuids'] for b in recovery['bins']), 0)

    def test_repeated_persisted_log_for_one_uuid_counts_once(self):
        self.event('one', 4.1, commit=4.2)
        self.app.append(dict(self.app[0], wall_time_ns=self.ns(5.2)))
        recovery = self.analyze()['episodes'][0]['throughput_recovery']
        self.assertEqual(sum(b['new_persisted_uuids'] for b in recovery['bins']), 1)

    def test_short_followup_and_partial_tail_are_censored(self):
        self.steady()
        self.manifest['observation_end_ns'] = self.ns(6.5)
        recovery = self.analyze()['episodes'][0]['throughput_recovery']
        self.assertEqual(recovery['status'], 'right_censored_insufficient_followup')
        self.assertEqual(recovery['complete_bins'], 2)
        self.assertEqual(recovery['unscored_partial_tail_seconds'], .5)
        self.assertIsNone(recovery['confirmed_at_ns'])

    def test_post_load_drain_does_not_extend_sustained_measurement(self):
        self.config['measurement_seconds'] = 6
        self.event('old1', 3.1, commit=6.1)
        self.event('old2', 3.2, commit=7.1)
        self.event('old3', 3.3, commit=8.1)
        recovery = self.analyze()['episodes'][0]['throughput_recovery']
        self.assertEqual(recovery['status'], 'right_censored_insufficient_followup')
        self.assertEqual(recovery['complete_bins'], 2)

    def test_unknown_lag_is_not_zero(self):
        self.steady()
        self.lag = [{'wall_time_ns': self.ns(5), 'exit_code': 0, 'partitions': [{'lag': None}]},
                    {'wall_time_ns': self.ns(6), 'exit_code': 1, 'partitions': [{'lag': 0}]}]
        episode = self.analyze()['episodes'][0]
        self.assertIsNone(episode['first_observed_zero_lag']['wall_time_ns'])
        self.assertEqual(episode['throughput_recovery']['status'], 'observed')

    def test_missing_export_success_prevents_positive_throughput_claim(self):
        self.steady()
        self.manifest.pop('application_log_export_exit_code')
        result = self.analyze()
        self.assertEqual(result['episodes'][0]['throughput_recovery']['status'], 'inconclusive_instrumentation')
        self.assertIsNone(result['episodes'][0]['throughput_recovery']['confirmed_at_ns'])

    def test_foreign_run_records_are_ignored(self):
        self.event('local', 3)
        for index in range(3):
            self.app.append({'run_id': 'foreign', 'event_id': 'local', 'milestone': 'commit_completed',
                             'status': 'persisted', 'wall_time_ns': self.ns(4.1 + index)})
        self.assertNotEqual(self.analyze()['episodes'][0]['throughput_recovery']['status'], 'observed')

    def test_restart_not_observed_is_censored(self):
        self.event('pending', 3)
        self.manifest['fault_events'] = self.manifest['fault_events'][:1]
        self.assertEqual(self.analyze()['episodes'][0]['status'], 'right_censored_restart_not_observed')

    def test_criteria_have_no_implicit_scientific_defaults(self):
        with self.assertRaises(TypeError):
            analyze_recovery(self.config, self.manifest, [], [], [])
        for field, value in [('rate_fraction', 0), ('rate_fraction', 1.1), ('reference_rate_events_s', float('nan')),
                             ('sustained_window_seconds', 2.5), ('throughput_bin_seconds', 0)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                criteria = dict(self.criteria, **{field: value})
                analyze_recovery(self.config, self.manifest, [], [], [], **criteria)

    def test_half_open_bins_put_boundary_commit_in_next_bin(self):
        self.event('one', 4.1, commit=5)
        recovery = self.analyze()['episodes'][0]['throughput_recovery']
        self.assertEqual(recovery['bins'][0]['new_persisted_uuids'], 0)
        self.assertEqual(recovery['bins'][1]['new_persisted_uuids'], 1)

    def test_commit_before_client_acceptance_does_not_create_false_backlog(self):
        self.event('sync', 3, commit=3.0005, http=201)
        result = self.analyze()
        self.assertTrue(all(row['accepted_not_persisted_uuids'] == 0 for row in result['backlog_timeline']))
        self.assertEqual(result['episodes'][0]['restart_cohort']['count'], 0)


if __name__ == '__main__':
    unittest.main()
