"""All data in this suite are fabricated fixtures, never experiment evidence."""
import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence_gate import CORE_SOURCES, ESSENTIAL_FILES, definitive_evidence_issues
from normalize import normalize, seal_inputs
from protocol import ALL_SERVICES, phases_for


class DefinitiveEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.run_id = '11111111-1111-4111-8111-111111111111'
        self.protocol = {
            'frozen': True, 'frozen_by': 'synthetic fixture only', 'frozen_utc': '2025-12-31T00:00:00Z',
            'pilot_evidence_path': 'synthetic fixture only', 'c4_choice_justification': 'fixture, not author decision',
            'random_seed': 1, 'repetitions': 10, 'warmup_seconds': 60, 'measurement_seconds': 300,
            'common_reference_rate': 1, 'drain_seconds': 10, 'sample_interval_seconds': 2,
            'recovery_stable_seconds': 5, 'offered_rate_tolerance_fraction': 0.01,
            'generator': {'preallocated_vus': 1, 'max_vus': 2, 'http_timeout_seconds': 5,
                          'generator_cpus': 1, 'generator_memory': '64m', 'payload_padding_bytes': 0},
            'cases': [{'scenario': 'C1', 'rate': 1},
                      *({'scenario': 'C2', 'level_fraction': level, 'rate': 1} for level in (0.25, 0.50, 0.75, 1.00)),
                      {'scenario': 'C3', 'rate': 1, 'burst': {'rate': 2, 'at_seconds': 10, 'seconds': 10}},
                      {'scenario': 'C4C5', 'rate': 1, 'fault_by_variant': {
                          v: {'service': 'postgres', 'at_seconds': 10, 'seconds': 5} for v in ('sync', 'async')}}]}
        self.config = {key: self.protocol[key] for key in (
            'warmup_seconds', 'measurement_seconds', 'drain_seconds', 'sample_interval_seconds',
            'recovery_stable_seconds', 'offered_rate_tolerance_fraction', 'common_reference_rate',
            'repetitions', 'random_seed')}
        self.config.update(self.protocol['generator'])
        self.config.update(run_id=self.run_id, profile='definitive', variant='sync', scenario='C1', rate=1, repetition=0)
        self.config['phases'] = phases_for(self.config)
        self.put('protocol.json', self.protocol)
        (self.path / 'pilot_evidence.snapshot').write_text('SYNTHETIC UNIT TEST FIXTURE, NOT A PILOT')
        for name, key in (('protocol.json', 'protocol_sha256'), ('pilot_evidence.snapshot', 'pilot_evidence_sha256')):
            self.config[key] = hashlib.sha256((self.path / name).read_bytes()).hexdigest()
        self.put('config.json', self.config)
        containers = [{'service': s, 'id': f'container-{s}', 'image': f'image-{s}', 'image_id': f'sha256:{s}',
                       'nano_cpus': 1_000_000_000, 'memory_limit_bytes': 64_000_000} for s in ALL_SERVICES]
        sources = {}
        for relative in CORE_SOURCES:
            path = self.path / 'source_snapshot' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# synthetic source fixture\n')
            sources[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.manifest = {
            'run_id': self.run_id, 'profile': 'definitive', 'errors': [], 'fault_errors': [], 'fault_events': [],
            'load_exit_code': 0, 'database_export_exit_code': 0, 'application_log_export_exit_code': 0,
            'started_utc': '2026-01-01T00:00:00Z', 'finished_utc': '2026-01-01T00:06:11Z',
            'observation_end_ns': 1767225971000000000,
            'environment': {'os': 'fixture', 'python': 'fixture', 'cpu_count': 1, 'cpu_model': 'fixture',
                'docker_server': ['fixture'], 'compose_version': 'fixture', 'clock_notes': 'fixture',
                'runtime_secret_values_included': False, 'sources_sha256': sources, 'containers': containers,
                'images': [{'reference': c['image'], 'image_id': c['image_id']} for c in containers]
                          + [{'reference': 'grafana/k6:1.4.0', 'image_id': 'sha256:fixture'}]}}
        self.put('manifest.json', self.manifest)
        self.generator, self.app, payloads, rows = [], [], [], []
        origin = self.origin = 1767225601000
        for index in range(360):
            event_id = f'{index:08x}-1111-4111-8111-111111111111'
            phase = 'warmup' if index < 60 else 'measurement'
            sent = origin + index * 1000
            common = {'run_id': self.run_id, 'event_id': event_id, 'phase': phase, 'segment': phase}
            self.generator.append(dict(common, kind='request_sent', sent_at_ms=sent,
                phase_start_ms=origin if phase == 'warmup' else origin + 60000,
                phase_seconds=60 if phase == 'warmup' else 300, payload_index=index))
            self.generator.append(dict(common, kind='http_response', sent_at_ms=sent, finished_at_ms=sent + 10,
                http_status=201, http_wall_duration_ms=10, http_transport_duration_ms=9))
            self.app.append(dict(common, milestone='commit_completed', wall_time_ns=(sent + 5) * 1_000_000,
                                 monotonic_ns=index + 1, status='persisted'))
            payloads.append({'event_id': event_id, 'payload': {'run_id': self.run_id}})
            rows.append({'event_id': event_id, 'content_hash': 'fixture', 'persisted_at': '2026-01-01T00:00:00Z',
                         'run_id': self.run_id})
        self.put_lines('generator.jsonl', self.generator)
        self.put_lines('application.jsonl', self.app)
        self.put('payloads.json', payloads)
        with (self.path / 'database.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['event_id', 'content_hash', 'persisted_at', 'run_id'])
            writer.writeheader()
            writer.writerows(rows)
        self.put('k6-summary.json', {'metrics': {name: {'values': {'count': 360}} for name in ('iterations', 'http_reqs')}})
        self.put_lines('k6-points.jsonl', [{'type': 'Point', 'metric': 'http_req_duration',
            'data': {'time': '2026-01-01T00:02:00Z', 'value': 9, 'tags': {'phase': 'measurement'}}}])
        self.put_lines('resources.jsonl', [{'wall_time_ns': (origin + 61000) * 1_000_000, 'exit_code': 0,
            'containers': [{'Container': c['id'], 'CPUPerc': '1.0%', 'MemUsage': '1MiB / 64MiB'} for c in containers]}])
        self.put_lines('lag.jsonl', [{'wall_time_ns': (origin + 61000) * 1_000_000, 'exit_code': 0,
            'partitions': [{'committed_offset': 2, 'log_end_offset': 2, 'lag': 0}]}])
        seal_inputs(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, value):
        (self.path / name).write_text(json.dumps(value), encoding='utf-8')

    def put_lines(self, name, records):
        (self.path / name).write_text('\n'.join(json.dumps(record) for record in records), encoding='utf-8')

    def reseal_fixture(self):
        # Only modifies temporary fixture data; real run evidence is never touched.
        (self.path / 'inputs.sha256.json').unlink(missing_ok=True)
        seal_inputs(self.path)

    def gate(self):
        return definitive_evidence_issues(self.path, self.config, self.manifest)

    def configure_fault_fixture(self):
        # Structural fixture only: these command records are not real fault results.
        case = next(case for case in self.protocol['cases'] if case['scenario'] == 'C4C5')
        self.config.update(scenario='C4C5', fault=dict(case['fault_by_variant']['sync']))
        target_ns = (self.origin + 60000 + 10000) * 1_000_000
        self.manifest['fault_events'] = [
            {'action': action, 'service': 'postgres', 'wall_time_ns': target_ns + offset * 1_000_000_000}
            for action, offset in (('stop_requested', 0), ('stopped', 2), ('start_requested', 7),
                                   ('started', 8), ('ready', 10))]
        self.put('config.json', self.config)
        self.put('manifest.json', self.manifest)
        self.reseal_fixture()

    def configure_excess_fixture(self, excess=None):
        # Artificial boundary marker; it deliberately has no UUID or HTTP response.
        excess = excess or [{'kind': 'scheduler_excess_iteration', 'run_id': self.run_id,
            'segment': 'measurement', 'phase': 'measurement', 'iteration_index': 300,
            'scheduled_count': 300, 'wall_time_ms': self.origin + 360000}]
        self.put_lines('generator.jsonl', self.generator + excess)
        self.put('k6-summary.json', {'metrics': {
            'iterations': {'values': {'count': 360 + len(excess)}},
            'http_reqs': {'values': {'count': 360}}}})
        self.reseal_fixture()
        return excess

    def test_complete_fixture_can_pass_gate_but_never_produces_scientific_conclusion(self):
        self.assertEqual(self.gate(), [])
        result = normalize(self.path)
        self.assertTrue(result['eligible_definitive_observation'])
        self.assertFalse(result['scientific_conclusion_produced'])

    def test_each_essential_artifact_is_required(self):
        for filename in ESSENTIAL_FILES:
            with self.subTest(filename=filename):
                path = self.path / filename
                saved = path.read_bytes()
                path.unlink()
                try:
                    self.assertTrue(self.gate())
                    if filename in ('config.json', 'manifest.json'):
                        with self.assertRaises(FileNotFoundError):
                            normalize(self.path, self.path / ('analysis-' + filename))
                finally:
                    path.write_bytes(saved)

    def test_missing_or_null_success_exit_codes_are_ineligible(self):
        for key in ('load_exit_code', 'database_export_exit_code', 'application_log_export_exit_code'):
            for value in (None, 1, False):
                with self.subTest(key=key, value=value):
                    self.manifest[key] = value
                    self.assertTrue(any(key in issue for issue in self.gate()))
            self.manifest.pop(key)
            self.assertTrue(any(key in issue for issue in self.gate()))
            self.manifest[key] = 0

    def test_missing_application_logs_do_not_become_successful_zero_observations(self):
        (self.path / 'application.jsonl').unlink()
        result = normalize(self.path)
        self.assertFalse(result['eligible_definitive_observation'])
        self.assertTrue(any('application.jsonl' in message for message in result['instrumentation_issues']))

    def test_empty_k6_summary_is_not_success(self):
        self.put('k6-summary.json', {'metrics': {}})
        self.reseal_fixture()
        result = normalize(self.path)
        self.assertFalse(result['eligible_definitive_observation'])
        self.assertTrue(any('k6 summary count' in message for message in result['definitive_eligibility_issues']))

    def test_empty_database_export_does_not_reconcile_commits(self):
        (self.path / 'database.csv').write_text('event_id,content_hash,persisted_at,run_id\n')
        self.reseal_fixture()
        self.assertTrue(any('SQL export' in message for message in self.gate()))

    def test_corrupt_jsonl_is_not_silently_ignored_by_gate(self):
        with (self.path / 'generator.jsonl').open('a') as stream:
            stream.write('\n{broken json')
        self.reseal_fixture()
        self.assertTrue(any('invalid JSONL' in message for message in self.gate()))

    def test_async_requires_measured_offsets(self):
        self.config['variant'] = 'async'
        (self.path / 'lag.jsonl').unlink()
        self.assertTrue(any('lag' in message for message in self.gate()))

    def test_resource_file_without_real_samples_is_ineligible(self):
        self.put_lines('resources.jsonl', [{'wall_time_ns': 1, 'exit_code': 0, 'containers': []}])
        self.reseal_fixture()
        self.assertTrue(any('CPU/memory' in message for message in self.gate()))

    def test_missing_source_snapshot_is_ineligible(self):
        (self.path / 'source_snapshot' / CORE_SOURCES[0]).unlink()
        self.assertTrue(any('source snapshot missing' in message for message in self.gate()))

    def test_changed_source_is_rejected_even_after_inputs_are_resealed(self):
        (self.path / 'source_snapshot' / CORE_SOURCES[0]).write_text('# changed fixture')
        self.reseal_fixture()
        self.assertTrue(any('source snapshot unsealed or checksum mismatch' in message for message in self.gate()))

    def test_changed_sealed_input_is_ineligible(self):
        with (self.path / 'generator.jsonl').open('a') as stream:
            stream.write('\n')
        self.assertTrue(any('sealed input checksum mismatch' in message for message in self.gate()))

    def test_unfrozen_protocol_is_ineligible_even_with_matching_hash(self):
        self.protocol['frozen'] = False
        self.put('protocol.json', self.protocol)
        self.config['protocol_sha256'] = hashlib.sha256((self.path / 'protocol.json').read_bytes()).hexdigest()
        self.put('config.json', self.config)
        self.reseal_fixture()
        self.assertTrue(any('protocol is incomplete' in message for message in self.gate()))

    def test_config_drift_from_frozen_protocol_is_ineligible(self):
        self.config['measurement_seconds'] = 10
        self.assertTrue(any('measurement_seconds' in message for message in self.gate()))

    def test_missing_send_phase_clock_is_ineligible(self):
        self.generator[0].pop('phase_start_ms')
        self.put_lines('generator.jsonl', self.generator)
        self.reseal_fixture()
        self.assertTrue(any('phase/timestamp' in message for message in self.gate()))

    def test_missing_manifest_timestamps_are_ineligible(self):
        self.manifest.pop('observation_end_ns')
        self.assertTrue(any('UTC timestamps' in message for message in self.gate()))

    def test_missing_payload_identity_is_ineligible(self):
        self.put('payloads.json', [])
        self.reseal_fixture()
        self.assertTrue(any('preserved payload identity' in message for message in self.gate()))

    def test_sealing_does_not_require_final_checksums_or_allow_overwrite(self):
        self.assertFalse((self.path / 'checksums.sha256.json').exists())
        self.assertEqual(self.gate(), [])
        with self.assertRaises(FileExistsError):
            seal_inputs(self.path)

    def test_complete_fault_commands_can_pass_structural_gate(self):
        self.configure_fault_fixture()
        self.assertEqual(self.gate(), [])

    def test_configured_fault_requires_each_actual_command_milestone(self):
        self.configure_fault_fixture()
        recorded = self.manifest['fault_events']
        for action in ('stop_requested', 'stopped', 'start_requested', 'started', 'ready'):
            with self.subTest(action=action):
                self.manifest['fault_events'] = [row for row in recorded if row['action'] != action]
                self.assertTrue(any(action in issue for issue in self.gate()))
        self.manifest['fault_events'] = recorded

    def test_configured_fault_rejects_early_resume_request(self):
        self.configure_fault_fixture()
        self.manifest['fault_events'][2]['wall_time_ns'] -= 1
        self.assertTrue(any('shorter than' in issue for issue in self.gate()))

    def test_configured_fault_service_must_match_frozen_plan(self):
        self.configure_fault_fixture()
        self.manifest['fault_events'][0]['service'] = 'consumer'
        self.assertTrue(any('service differs' in issue for issue in self.gate()))

    def test_configured_fault_cannot_be_injected_before_scheduled_target(self):
        self.configure_fault_fixture()
        self.manifest['fault_events'][0]['wall_time_ns'] -= 1
        self.assertTrue(any('preceded the planned' in issue for issue in self.gate()))

    def test_c2_level_is_required_even_when_all_rounded_rates_are_identical(self):
        self.config['scenario'] = 'C2'
        self.assertTrue(any('case/level/rate' in issue for issue in self.gate()))

    def test_c2_keeps_explicit_level_identity_when_integer_rates_repeat(self):
        self.config.update(scenario='C2', level_fraction=0.25)
        self.put('config.json', self.config)
        self.reseal_fixture()
        self.assertEqual(self.gate(), [])

    def test_c2_boolean_does_not_stand_in_for_full_level_identity(self):
        self.config.update(scenario='C2', level_fraction=True)
        self.assertTrue(any('case/level/rate' in issue for issue in self.gate()))

    def test_scheduler_excess_is_accounted_without_fake_http_or_offered_event(self):
        self.configure_excess_fixture()
        self.assertEqual(self.gate(), [])
        result = normalize(self.path)
        self.assertTrue(result['eligible_definitive_observation'])
        self.assertEqual(result['offered_events'], 300)
        self.assertEqual(result['http_accepted_events'], 300)
        self.assertFalse(result['scientific_conclusion_produced'])

    def test_scheduler_excess_requires_k6_iteration_count_to_include_skipped_invocation(self):
        self.configure_excess_fixture()
        self.put('k6-summary.json', {'metrics': {
            name: {'values': {'count': 360}} for name in ('iterations', 'http_reqs')}})
        self.reseal_fixture()
        self.assertTrue(any('inconsistent: iterations' in issue for issue in self.gate()))

    def test_scheduler_excess_cannot_inflate_http_count(self):
        self.configure_excess_fixture()
        self.put('k6-summary.json', {'metrics': {
            name: {'values': {'count': 361}} for name in ('iterations', 'http_reqs')}})
        self.reseal_fixture()
        self.assertTrue(any('inconsistent: http_reqs' in issue for issue in self.gate()))

    def test_scheduler_excess_metadata_must_match_phase_and_budget(self):
        original = self.configure_excess_fixture()[0]
        changes = ({'segment': 'unknown'}, {'phase': 'warmup'}, {'scheduled_count': 301},
                   {'iteration_index': 299}, {'iteration_index': True}, {'wall_time_ms': None},
                   {'wall_time_ms': self.origin + 400000})
        for change in changes:
            with self.subTest(change=change):
                self.configure_excess_fixture([dict(original, **change)])
                self.assertTrue(any('scheduler excess iteration' in issue for issue in self.gate()))

    def test_scheduler_excess_index_must_be_unique_per_segment(self):
        original = self.configure_excess_fixture()[0]
        self.configure_excess_fixture([original, dict(original)])
        self.assertTrue(any('scheduler excess iteration is duplicated' in issue for issue in self.gate()))


if __name__ == '__main__':
    unittest.main()
