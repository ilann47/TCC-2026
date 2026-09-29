"""Artificial command timelines exercise evidence checks without Docker or sleep."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence_gate import fault_timing_observation


class FaultTimingTests(unittest.TestCase):
    def setUp(self):
        self.origin_ms = 1767225601000
        self.config = {'fault': {'service': 'postgres', 'at_seconds': 10, 'seconds': 5}}
        self.windows = {'measurement_start_ms': self.origin_ms,
                        'measurement_end_ms': self.origin_ms + 300000,
                        'observation_start_ms': self.origin_ms - 61000,
                        'observation_end_ms': self.origin_ms + 400000}
        self.manifest = {'fault_events': [
            {'action': action, 'service': 'postgres', 'wall_time_ns': self.ns(offset)}
            for action, offset in (('stop_requested', 10), ('stopped', 12), ('start_requested', 17),
                                   ('started', 18), ('ready', 20))]}

    def ns(self, seconds):
        return self.origin_ms * 1_000_000 + seconds * 1_000_000_000

    def observe(self):
        return fault_timing_observation(self.config, self.manifest, **self.windows)

    def test_no_fault_does_not_require_fault_events(self):
        self.assertIsNone(fault_timing_observation({}, {}, **self.windows))

    def test_complete_sequence_reports_actual_durations(self):
        result = self.observe()
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['stop_command_seconds'], 2)
        self.assertEqual(result['observed_stopped_hold_seconds'], 5)
        self.assertEqual(result['stopped_hold_overrun_seconds'], 0)
        self.assertEqual(result['readiness_after_started_seconds'], 2)

    def test_late_commands_and_readiness_are_reported_without_arbitrary_rejection(self):
        times = (20, 25, 290, 310, 350)
        for record, seconds in zip(self.manifest['fault_events'], times):
            record['wall_time_ns'] = self.ns(seconds)
        result = self.observe()
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['stop_request_delay_seconds'], 10)
        self.assertEqual(result['observed_stopped_hold_seconds'], 265)
        self.assertEqual(result['stopped_hold_overrun_seconds'], 260)
        self.assertEqual(result['ready_after_measurement_end_seconds'], 50)

    def test_stop_request_before_target_by_one_nanosecond_is_rejected(self):
        self.manifest['fault_events'][0]['wall_time_ns'] -= 1
        self.assertTrue(any('preceded the planned' in issue for issue in self.observe()['issues']))

    def test_stopped_hold_shorter_by_one_nanosecond_is_rejected(self):
        self.manifest['fault_events'][2]['wall_time_ns'] -= 1
        self.assertTrue(any('shorter than' in issue for issue in self.observe()['issues']))

    def test_command_order_and_timestamp_order_are_both_checked(self):
        self.manifest['fault_events'][1], self.manifest['fault_events'][2] = (
            self.manifest['fault_events'][2], self.manifest['fault_events'][1])
        self.assertTrue(any('records are not' in issue for issue in self.observe()['issues']))
        self.manifest['fault_events'][1], self.manifest['fault_events'][2] = (
            self.manifest['fault_events'][2], self.manifest['fault_events'][1])
        self.manifest['fault_events'][1]['wall_time_ns'] = self.ns(9)
        self.assertTrue(any('timestamps are not' in issue for issue in self.observe()['issues']))

    def test_duplicate_command_cannot_fake_complete_single_fault(self):
        self.manifest['fault_events'].append(dict(self.manifest['fault_events'][0]))
        self.assertTrue(any('exactly one' in issue for issue in self.observe()['issues']))

    def test_readiness_timeout_is_not_a_successful_ready_marker(self):
        self.manifest['fault_events'][-1]['action'] = 'readiness_timeout'
        self.assertTrue(any('ready' in issue for issue in self.observe()['issues']))

    def test_fault_outside_measurement_window_is_rejected(self):
        for index, record in enumerate(self.manifest['fault_events']):
            record['wall_time_ns'] = self.ns(301 + index * 10)
        self.assertTrue(any('inside the measurement' in issue for issue in self.observe()['issues']))

    def test_observation_cannot_end_before_recorded_readiness(self):
        self.manifest['fault_events'][-1]['wall_time_ns'] = self.ns(401)
        self.assertTrue(any('outside the recorded observation' in issue for issue in self.observe()['issues']))

    def test_fault_service_must_match_configured_service(self):
        self.manifest['fault_events'][0]['service'] = 'consumer'
        self.assertTrue(any('service differs' in issue for issue in self.observe()['issues']))

    def test_unknown_windows_are_not_replaced_by_zero(self):
        self.windows['measurement_start_ms'] = None
        self.assertTrue(any('requires valid' in issue for issue in self.observe()['issues']))


if __name__ == '__main__':
    unittest.main()
