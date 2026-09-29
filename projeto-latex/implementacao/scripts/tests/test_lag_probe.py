"""Offline doubles only: no broker, container or experimental observations."""
import io
import json
import sys
import tempfile
import threading
import unittest
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kafka_lag_probe import LagProbe, client_configs, main, observe, positive_seconds


def topic_partition(topic, partition, offset=-1001, error=None):
    return SimpleNamespace(topic=topic, partition=partition, offset=offset, error=error)


class FakeAdmin:
    def __init__(self):
        self.partitions = {0: SimpleNamespace(error=None)}
        self.topics = {'audit-events': SimpleNamespace(error=None, partitions=self.partitions)}
        self.offsets = [topic_partition('audit-events', 0, 7)]
        self.calls = []
        self.metadata_error = self.offset_error = None

    def list_topics(self, **kwargs):
        self.calls.append(('list_topics', kwargs))
        if self.metadata_error:
            raise self.metadata_error
        return SimpleNamespace(topics=self.topics)

    def list_consumer_group_offsets(self, requests, **kwargs):
        self.calls.append(('list_consumer_group_offsets', requests, kwargs))
        future = Future()
        if self.offset_error:
            future.set_exception(self.offset_error)
        else:
            future.set_result(SimpleNamespace(topic_partitions=self.offsets))
        return {requests[0].group_id: future}


class FakeConsumer:
    def __init__(self):
        self.values = {0: (0, 10)}
        self.calls = []

    def get_watermark_offsets(self, partition, **kwargs):
        self.calls.append(('get_watermark_offsets', partition, kwargs))
        value = self.values[partition.partition]
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        self.calls.append(('close',))


class Clock:
    def __init__(self, step=1_000_000):
        self.tick, self.step = 0, step

    def monotonic_ns(self):
        self.tick += self.step
        return self.tick

    def time_ns(self):
        return 1_000_000_000 + self.tick

    def process_time_ns(self):
        return self.tick // 2


class LagProbeTests(unittest.TestCase):
    def setUp(self):
        self.admin, self.consumer, self.clock = FakeAdmin(), FakeConsumer(), Clock()
        self.probe = LagProbe(self.admin, self.consumer, topic_partition,
            lambda group, parts: SimpleNamespace(group_id=group, topic_partitions=parts),
            group='audit-persistence', topic='audit-events', timeout=1, clock=self.clock)

    def test_known_committed_offset_uses_next_offset_and_uncached_high_watermark(self):
        sample = self.probe.sample()
        row = sample['partitions'][0]
        self.assertEqual((row['committed_offset'], row['current_offset'], row['log_end_offset'], row['lag']), (7, 7, 10, 3))
        self.assertEqual((sample['status'], sample['exit_code']), ('ok', 0))
        self.assertEqual(self.consumer.calls[0][2]['cached'], False)
        self.assertNotIn('topic', self.admin.calls[0][1])
        self.assertEqual(self.admin.calls[1][1][0].group_id, 'audit-persistence')
        self.assertGreater(sample['sample_duration_ns'], 0)
        self.assertGreater(sample['observer_process_cpu_ns'], 0)
        self.assertGreaterEqual(sample['observer_process_cpu_total_ns'], sample['observer_process_cpu_ns'])
        self.assertEqual(sample['wall_time_ns'], sample['sample_finished_ns'])
        self.assertEqual(len(sample['stages']), 3)

    def test_consumer_config_never_joins_target_or_stores_offsets(self):
        _, config = client_configs('kafka:9092')
        self.assertNotEqual(config['group.id'], 'audit-persistence')
        for key in ('enable.auto.commit', 'enable.auto.offset.store', 'allow.auto.create.topics'):
            self.assertIs(config[key], False)
        self.probe.sample()
        self.probe.close()
        self.assertEqual([c[0] for c in self.consumer.calls], ['get_watermark_offsets', 'close'])
        self.assertEqual([c[0] for c in self.admin.calls], ['list_topics', 'list_consumer_group_offsets'])

    def test_uncommitted_offset_is_null_even_for_an_empty_log(self):
        self.admin.offsets[0].offset = -1001
        self.consumer.values[0] = (0, 0)
        sample = self.probe.sample()
        self.assertIsNone(sample['partitions'][0]['lag'])
        self.assertIsNone(sample['partitions'][0]['committed_offset'])
        self.assertEqual(sample['partitions'][0]['status'], 'committed_offset_unknown')
        self.assertEqual(sample['exit_code'], 1)

    def test_zero_is_valid_only_when_both_offsets_are_known(self):
        self.admin.offsets[0].offset = 0
        self.consumer.values[0] = (0, 0)
        self.assertEqual(self.probe.sample()['partitions'][0]['lag'], 0)

    def test_group_query_timeout_preserves_high_watermark_but_not_fake_lag(self):
        self.admin.offset_error = TimeoutError('sensitive server diagnostic')
        sample = self.probe.sample()
        self.assertEqual(sample['partitions'][0]['log_end_offset'], 10)
        self.assertIsNone(sample['partitions'][0]['lag'])
        self.assertNotIn('sensitive', json.dumps(sample))
        self.assertEqual(sample['errors'][0]['error_type'], 'TimeoutError')

    def test_watermark_timeout_none_is_unknown(self):
        self.consumer.values[0] = None
        sample = self.probe.sample()
        self.assertEqual(sample['partitions'][0]['committed_offset'], 7)
        self.assertIsNone(sample['partitions'][0]['lag'])
        self.assertEqual(sample['exit_code'], 1)

    def test_watermark_exception_is_unknown_and_sanitized(self):
        self.consumer.values[0] = RuntimeError('secret diagnostics')
        sample = self.probe.sample()
        self.assertIsNone(sample['partitions'][0]['lag'])
        self.assertNotIn('secret', json.dumps(sample))

    def test_metadata_failure_does_not_reuse_previous_values(self):
        self.probe.sample()
        self.admin.metadata_error = TimeoutError()
        sample = self.probe.sample()
        self.assertEqual(sample['partitions'][0]['partition'], 0)
        for name in ('lag', 'committed_offset', 'log_end_offset'):
            self.assertIsNone(sample['partitions'][0][name])
        self.assertEqual(sample['exit_code'], 1)

    def test_absent_topic_does_not_create_or_claim_zero_lag(self):
        self.admin.topics = {}
        sample = self.probe.sample()
        self.assertEqual(sample['partitions'], [])
        self.assertEqual(sample['status'], 'unknown')
        self.assertEqual(len(self.admin.calls), 1)
        self.assertEqual(self.consumer.calls, [])

    def test_partition_error_and_missing_group_partition_are_unknown(self):
        self.admin.offsets = []
        self.assertIsNone(self.probe.sample()['partitions'][0]['lag'])
        self.admin.partitions[0].error = RuntimeError()
        sample = self.probe.sample()
        self.assertIsNone(sample['partitions'][0]['lag'])
        self.assertEqual(sample['partitions'][0]['status'], 'partition_metadata_error')

    def test_out_of_range_offsets_are_not_clamped_to_zero(self):
        for current, watermarks in ((12, (0, 10)), (2, (5, 10)), (7, (11, 10))):
            with self.subTest(current=current, watermarks=watermarks):
                self.admin.offsets[0].offset = current
                self.consumer.values[0] = watermarks
                sample = self.probe.sample()
                self.assertIsNone(sample['partitions'][0]['lag'])
                self.assertEqual(sample['partitions'][0]['status'], 'offsets_out_of_range')

    def test_partial_multi_partition_sample_keeps_unknown_partition(self):
        self.admin.partitions[1] = SimpleNamespace(error=None)
        self.consumer.values[1] = (0, 20)
        sample = self.probe.sample()
        self.assertEqual(sample['status'], 'partial')
        self.assertEqual(sample['exit_code'], 1)
        self.assertEqual([p['lag'] for p in sample['partitions']], [3, None])

    def test_shared_sample_budget_does_not_multiply_by_partition_count(self):
        self.probe.timeout = .00001
        sample = self.probe.sample()
        self.assertEqual(sample['exit_code'], 1)
        self.assertEqual(self.admin.calls, [])
        self.assertEqual(sample['errors'][0]['error_type'], 'TimeoutError')

    def test_partition_offset_error_exposes_only_error_code(self):
        self.admin.offsets[0].error = SimpleNamespace(code=lambda: 31, diagnostic='must not escape')
        sample = self.probe.sample()
        self.assertIsNone(sample['partitions'][0]['lag'])
        self.assertEqual(sample['partitions'][0]['error_code'], 31)
        self.assertNotIn('must not escape', json.dumps(sample))

    def test_reversed_wall_clock_excludes_lag_but_keeps_monotonic_duration(self):
        self.clock.time_ns = lambda: 1_000_000_000 - self.clock.tick
        sample = self.probe.sample()
        self.assertEqual(sample['status'], 'clock_error')
        self.assertEqual(sample['exit_code'], 1)
        self.assertGreater(sample['sample_duration_ns'], 0)
        self.assertIsNone(sample['partitions'][0]['lag'])

    def test_observe_writes_compatible_jsonl_with_index_and_run_identity(self):
        stream = io.StringIO()
        count = observe(self.probe, stream, interval=.00001, stop_event=threading.Event(),
                        samples=2, run_id='fixture-only', clock=self.clock)
        records = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual(count, 2)
        self.assertEqual([r['sample_index'] for r in records], [0, 1])
        self.assertTrue(all(r['run_id'] == 'fixture-only' for r in records))
        self.assertTrue(all(r['interval_overrun_seconds'] > 0 for r in records))
        self.assertIsNone(records[0]['sample_start_delta_ns'])
        self.assertGreater(records[1]['sample_start_delta_ns'], 0)
        self.assertEqual(len(self.consumer.calls), 2)

    def test_stopped_observer_does_not_query(self):
        event = threading.Event()
        event.set()
        self.assertEqual(observe(self.probe, io.StringIO(), interval=1, stop_event=event), 0)
        self.assertEqual(self.admin.calls, [])

    def test_nonfinite_nonpositive_durations_rejected(self):
        for value in ('nan', 'inf', '-inf', '0', '-1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                positive_seconds(value)

    def test_main_refuses_existing_evidence_before_opening_clients(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'lag.jsonl'
            output.write_text('preserved evidence', encoding='utf-8')
            with patch('kafka_lag_probe.create_probe') as factory, patch('sys.stderr', new_callable=io.StringIO):
                result = main(['--interval', '1', '--timeout', '1', '--output', str(output)])
            self.assertEqual(result, 2)
            factory.assert_not_called()
            self.assertEqual(output.read_text(encoding='utf-8'), 'preserved evidence')

    def test_main_creates_new_jsonl_and_closes_injected_client(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'lag.jsonl'
            with patch('kafka_lag_probe.create_probe', return_value=self.probe):
                result = main(['--interval', '1', '--timeout', '1', '--samples', '1', '--output', str(output)])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(output.read_text())['partitions'][0]['lag'], 3)
            self.assertEqual(self.consumer.calls[-1], ('close',))


if __name__ == '__main__':
    unittest.main()
