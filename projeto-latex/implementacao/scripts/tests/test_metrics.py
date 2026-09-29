import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from normalize import describe, memory_bytes, normalize, parse_lag, percentile, read_jsonl
from run_experiment import phases_for, validate_protocol


class MetricTests(unittest.TestCase):
    def test_percentiles_empty_singleton_and_interpolation(self):
        self.assertIsNone(percentile([], .95))
        self.assertEqual(percentile([7], .99), 7)
        self.assertEqual(percentile([0, 10], .95), 9.5)
        self.assertIsNone(describe([1])['sample_sd'])
        self.assertAlmostEqual(describe([1, 3])['sample_sd'], 2**.5)

    def test_lag_unknown_offsets_are_not_zero(self):
        rows = parse_lag('GROUP TOPIC PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG CONSUMER-ID HOST CLIENT-ID\n'
                         'g audit-events 0 10 15 5 client host id\n'
                         'g audit-events 1 - 7 - - - -')
        self.assertEqual(rows[0]['lag'], 5)
        self.assertIsNone(rows[1]['lag'])
        self.assertNotIn('host', rows[0])

    def test_memory_units(self):
        self.assertEqual(memory_bytes('1.5MiB '), 1.5 * 1024**2)
        self.assertEqual(memory_bytes('2MB'), 2_000_000)
        self.assertIsNone(memory_bytes('--'))

    def test_burst_phases_have_nonoverlapping_payload_ranges(self):
        phases = phases_for({'warmup_seconds': 60, 'rate': 5, 'measurement_seconds': 300,
                             'burst': {'at_seconds': 20, 'seconds': 10, 'rate': 20}})
        self.assertEqual([p['start_seconds'] for p in phases], [0, 60, 80, 90])
        self.assertEqual([p['payload_offset'] for p in phases], [0, 300, 400, 600])
        self.assertEqual(sum(p['seconds'] for p in phases), 360)

    def test_unfrozen_protocol_refused(self):
        with self.assertRaisesRegex(ValueError, 'frozen'):
            validate_protocol({'frozen': False})


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.config = {'run_id': 'run-1', 'profile': 'validation', 'variant': 'sync', 'scenario': 'functional',
                       'warmup_seconds': 0, 'measurement_seconds': 10,
                       'phases': [{'name': 'measurement', 'start_seconds': 0,
                                   'analysis_phase': 'measurement', 'rate': 1, 'seconds': 10}]}
        self.generator, self.app, self.rows = [], [], []

    def tearDown(self):
        self.temp.cleanup()

    def event(self, name, *, http=201, phase='measurement', send=1000, commit=None, state='persisted'):
        self.generator.append({'kind': 'request_sent', 'run_id': 'run-1', 'event_id': name,
                               'phase': phase, 'segment': 'measurement', 'sent_at_ms': send,
                               'phase_start_ms': 1000, 'phase_seconds': 10})
        if http is not None:
            self.generator.append({'kind': 'http_response', 'run_id': 'run-1', 'event_id': name,
                                   'http_status': http, 'finished_at_ms': send + 90,
                                   'http_wall_duration_ms': 90, 'http_transport_duration_ms': 80})
        if commit is not None:
            self.app.append({'milestone': 'commit_completed', 'run_id': 'run-1', 'event_id': name,
                             'wall_time_ns': int(commit * 1_000_000), 'status': state})
            self.rows.append({'event_id': name, 'content_hash': 'synthetic', 'run_id': 'run-1'})

    def analyze(self):
        (self.path / 'config.json').write_text(json.dumps(self.config))
        (self.path / 'manifest.json').write_text(json.dumps({'load_exit_code': 0}))
        (self.path / 'k6-summary.json').write_text(json.dumps({'metrics': {}}))
        for filename, records in [('generator.jsonl', self.generator), ('application.jsonl', self.app)]:
            (self.path / filename).write_text('\n'.join(json.dumps(r) for r in records))
        with (self.path / 'database.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['event_id', 'content_hash', 'run_id'])
            writer.writeheader()
            writer.writerows(self.rows)
        return normalize(self.path)

    def test_http_and_post_commit_latency_are_different_metrics(self):
        self.event('one', commit=1010)
        result = self.analyze()
        self.assertEqual(result['end_to_end_ms']['mean'], 10)
        self.assertEqual(result['http_wall_duration_ms']['mean'], 90)
        self.assertEqual(result['http_transport_duration_ms']['mean'], 80)
        self.assertEqual(result['throughput_persisted_events_s'], .1)
        self.assertFalse(result['eligible_definitive_observation'])

    def test_same_end_to_end_rule_for_async(self):
        self.config['variant'] = 'async'
        self.event('one', http=202, commit=1250)
        result = self.analyze()
        self.assertEqual(result['end_to_end_ms']['mean'], 250)

    def test_warmup_not_in_measurement_count(self):
        self.event('warm', phase='warmup', commit=1010)
        self.event('measured', commit=1020)
        result = self.analyze()
        self.assertEqual(result['offered_events'], 1)
        self.assertEqual(result['end_to_end_ms']['mean'], 20)

    def test_completion_after_window_is_not_measurement_throughput(self):
        self.event('one', commit=11001)
        result = self.analyze()
        self.assertEqual(result['completed_after_send_by_observation_end'], 1)
        self.assertEqual(result['throughput_persisted_events_s'], 0)
        self.assertEqual(result['end_to_end_ms']['n'], 1)

    def test_dlq_is_terminal_state_and_unresolved_is_not_invented_loss(self):
        self.event('terminal', http=202)
        self.event('pending', http=202)
        self.app.append({'milestone': 'dlq_acknowledged', 'run_id': 'run-1', 'event_id': 'terminal',
                         'wall_time_ns': 1_020_000_000})
        result = self.analyze()
        self.assertEqual(result['states']['terminal_dlq'], 1)
        self.assertEqual(result['states']['accepted_unresolved_at_window_end'], 1)
        self.assertNotIn('lost', result['states'])

    def test_negative_clock_duration_is_flagged_not_clamped(self):
        self.event('one', commit=999)
        result = self.analyze()
        self.assertEqual(result['end_to_end_ms']['n'], 0)
        self.assertTrue(any('negative' in s for s in result['instrumentation_issues']))

    def test_other_run_commit_does_not_complete_event(self):
        self.event('one', http=202)
        self.app.append({'milestone': 'commit_completed', 'run_id': 'other-run', 'event_id': 'one',
                         'wall_time_ns': 1_020_000_000, 'status': 'persisted'})
        result = self.analyze()
        self.assertEqual(result['end_to_end_ms']['n'], 0)
        self.assertEqual(result['states']['accepted_unresolved_at_window_end'], 1)

    def test_transport_failure_does_not_imply_no_commit(self):
        self.event('one', http=0, commit=1010)
        result = self.analyze()
        self.assertEqual(result['http_accepted_events'], 0)
        self.assertEqual(result['completed_after_send_by_observation_end'], 1)
        self.assertEqual(result['states']['persisted'], 1)

    def test_database_without_commit_log_has_no_fabricated_latency(self):
        self.event('one')
        self.rows.append({'event_id': 'one', 'content_hash': 'synthetic', 'run_id': 'run-1'})
        result = self.analyze()
        self.assertEqual(result['end_to_end_ms']['n'], 0)
        self.assertEqual(result['states']['persisted_without_commit_instrumentation'], 1)

    def test_duplicates_not_counted_as_new_persistence_throughput(self):
        self.event('one', commit=1010, state='duplicate')
        result = self.analyze()
        self.assertEqual(result['duplicate_observations'], 1)
        self.assertEqual(result['throughput_persisted_events_s'], 0)

    def test_retry_and_redelivery_are_distinct(self):
        self.event('one', http=202, commit=1010)
        for attempt in (1, 2, 1):
            self.app.append({'milestone': 'processing_attempt', 'run_id': 'run-1', 'event_id': 'one',
                             'attempt': attempt, 'wall_time_ns': 1_000_000_001})
        self.app.append({'milestone': 'retry_scheduled', 'run_id': 'run-1', 'event_id': 'one',
                         'attempt': 1, 'wall_time_ns': 1_000_000_002})
        result = self.analyze()
        self.assertEqual(result['event_redelivery_observations'], 1)
        self.assertEqual(result['retry_attempts_scheduled'], 1)

    def test_response_missing_remains_an_instrumentation_issue(self):
        self.event('one', http=None)
        result = self.analyze()
        self.assertTrue(any('lack response' in message for message in result['instrumentation_issues']))

    def test_existing_analysis_is_never_overwritten(self):
        self.event('one', commit=1010)
        self.analyze()
        with self.assertRaises(FileExistsError):
            normalize(self.path)


if __name__ == '__main__':
    unittest.main()
