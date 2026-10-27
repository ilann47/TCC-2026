import copy
from contextlib import ExitStack, redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qualified_analysis as q
import reduced_campaign as controller


class QualifiedAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.policy = {'revision': 'A1', 'allowed_variant': 'sync', 'allowed_profile': 'postgres-stop'}
        self.finding = {'event_id': 'event', 'finding': 'persisted_with_unobserved_commit_time_and_http_503',
                        'phase': 'measure', 'row_observed': True, 'commit_time': None}
        self.audit = {'run_id': 'run', 'variant': 'sync', 'profile': 'postgres-stop', 'block': 3, 'rate': 12,
                      'original_instrument_valid': False, 'original_analyzer_exit': 2,
                      'original_issues': ['event:incomplete_commit_db_evidence'], 'findings': [self.finding],
                      'summary_sha256': 'original', 'raw_inventory_sha256': 'inventory',
                      'stored_with_observed_commit_time': 39, 'stored_without_observed_commit_time': 1,
                      'counts_crosschecked': {'offered': 60, 'accepted': 39, 'stored_at_observation_end': 40},
                      'http_status_counts': {'201': 39, '503': 21}}
        self.summary = {'stored_within_measurement': 39, 'measure_seconds': 180}

    def classify(self):
        with patch.object(q, 'implementation_hashes', return_value={}), patch.object(q.review, 'sha', return_value='policy'):
            return q.classify(self.audit, self.summary, self.policy)

    def test_partial_preserves_verdict_coverage_and_http_error(self):
        original = copy.deepcopy((self.audit, self.summary))
        result = self.classify()
        self.assertFalse(result['original_instrument_valid'])
        self.assertFalse(result['eligibility']['commit_latency_primary'])
        self.assertTrue(result['eligibility']['http'])
        self.assertEqual(result['http_status_counts'], {'201': 39, '503': 21})
        self.assertEqual(result['timing']['imputed_timestamps'], 0)
        self.assertEqual(result['completion_in_measurement']['lower_count'], 39)
        self.assertEqual(result['completion_in_measurement']['upper_count'], 40)
        self.assertEqual(result['completion_in_measurement']['upper_per_second'], 40 / 180)
        self.assertEqual(original, (self.audit, self.summary))

    def test_complete_keeps_primary_and_exact_count(self):
        self.audit.update(original_instrument_valid=True, original_analyzer_exit=0, original_issues=[],
                          findings=[], stored_without_observed_commit_time=0)
        result = self.classify()
        self.assertTrue(result['eligibility']['commit_latency_primary'])
        self.assertEqual(result['classification'], 'complete_original_evidence')
        self.assertEqual(result['completion_in_measurement']['lower_count'], result['completion_in_measurement']['upper_count'])

    def test_profile_or_variant_does_not_get_implicit_exception(self):
        for field, value in [('variant', 'async'), ('profile', 'steady'), ('profile', 'burst')]:
            with self.subTest(field=field, value=value):
                audit = copy.deepcopy(self.audit)
                self.audit[field] = value
                with self.assertRaises(ValueError): self.classify()
                self.audit = audit

    def test_unexplained_or_warmup_or_fabricated_time_rejected(self):
        for field, value in [('finding', 'unexplained_evidence_mismatch'), ('phase', 'warmup'),
                             ('row_observed', False), ('commit_time', 'invented')]:
            with self.subTest(field=field):
                finding = copy.deepcopy(self.audit['findings'][0])
                self.audit['findings'][0][field] = value
                with self.assertRaises(ValueError): self.classify()
                self.audit['findings'][0] = finding

    def test_other_instrument_failures_not_waived(self):
        for issue in ('incomplete_client_evidence', 'content_hash_mismatch', 'database_clock_outside_observer_round_trip',
                      'observer_insufficient_coverage', 'generator_resources_insufficient_coverage'):
            with self.subTest(issue=issue):
                self.audit['original_issues'].append(issue)
                with self.assertRaises(ValueError): self.classify()
                self.audit['original_issues'].pop()

    def test_missing_finding_or_wrong_exit_rejected(self):
        self.audit['original_analyzer_exit'] = 1
        with self.assertRaises(ValueError): self.classify()
        self.audit['original_analyzer_exit'] = 2
        self.audit['findings'] = []
        with self.assertRaises(ValueError): self.classify()

    def test_wrong_coverage_cannot_make_bound(self):
        self.audit['stored_without_observed_commit_time'] = 0
        with self.assertRaises(ValueError): self.classify()

    def test_contradictory_complete_verdict_is_rejected(self):
        self.audit['original_instrument_valid'] = True
        with self.assertRaises(ValueError): self.classify()

    def test_negative_count_or_duration_is_not_accepted(self):
        for key, value in [('measure_seconds', 0), ('stored_within_measurement', -1), ('stored_within_measurement', 40)]:
            original = dict(self.summary)
            self.summary[key] = value
            with self.assertRaises(ValueError): self.classify()
            self.summary = original

    def test_initial_resume_shape_refuses_changed_state_or_later_folder(self):
        plan = [{'run_id': f'run-{n}', 'variant': 'sync'} for n in range(65)]
        policy = {'retrospective_attempts': 37, 'initial_partial_run_id': 'run-36'}
        state = {'phase': 'attention_required', 'campaign_completed': [r['run_id'] for r in plan[:36]],
                 'current': {'run_id': 'run-36'}}
        with tempfile.TemporaryDirectory() as temporary, patch.object(q, 'APP', Path(temporary)):
            q.initial_shape(state, plan, policy)
            state['controller_pid'] = 123
            with self.assertRaises(ValueError): q.initial_shape(state, plan, policy)
            del state['controller_pid']
            folder = q.APP / '.runtime/entrega04/run-37-sync'
            folder.mkdir(parents=True)
            with self.assertRaises(ValueError): q.initial_shape(state, plan, policy)

    def test_controller_keeps_qualified_separate_and_idempotent(self):
        state = {'campaign_completed': ['old']}
        assessment = {'run_id': 'partial', 'classification': 'partial_commit_timing'}
        with patch.object(q, 'save_assessment'):
            controller.record_assessment(state, assessment)
            controller.record_assessment(state, assessment)
            self.assertEqual(state['campaign_completed'], ['old'])
            self.assertEqual(state['campaign_qualified'], ['partial'])
            self.assertEqual(state['campaign_accounted'], 2)
            with self.assertRaises(ValueError):
                controller.record_assessment(state, dict(assessment, classification='complete_original_evidence'))

    def test_plain_launcher_cannot_resume_attention_state(self):
        with patch.object(controller, 'read', return_value={'phase': 'attention_required'}), patch.object(controller.subprocess, 'Popen') as spawn:
            with self.assertRaises(ValueError): controller.launch('campaign')
            spawn.assert_not_called()

    def test_assessment_cannot_overwrite_different_prior_analysis(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(q, 'RUNTIME', Path(temporary)):
            q.save_assessment({'run_id': 'run', 'classification': 'partial'})
            with self.assertRaises(ValueError): q.save_assessment({'run_id': 'run', 'classification': 'complete'})

    def run_controller_fixture(self, fail_next=False):
        rows = controller.make_plan({'seed': 20261026})
        original_read = controller.read
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            app = Path(temporary)
            runtime, report = app / 'runtime', app / 'report'
            runtime.mkdir(); report.mkdir()
            state_path = runtime / 'state.json'
            policy_path = report / 'policy.json'
            controller.write(policy_path, {})
            (report / 'plan.csv').write_bytes(controller.csv_bytes(rows))
            original_state = {'phase': 'attention_required', 'policy_sha256': controller.sha(policy_path.read_bytes()),
                              'campaign_completed': [r['run_id'] for r in rows[:36]], 'current': rows[36], 'error': 'original failure'}
            controller.write(state_path, original_state)
            original_state_bytes = state_path.read_bytes()
            for row in rows[:37]:
                folder = app / '.runtime/entrega04' / f"{row['run_id']}-{row['variant']}"
                folder.mkdir(parents=True)
                (folder / 'preserved.txt').write_text('unchanged')
            frozen = {'schema_version': 2, 'status': 'ready_for_definitive_runs',
                      'controller_sha256': controller.sha(Path(controller.__file__).read_bytes()),
                      'plan_sha256': controller.sha((report / 'plan.csv').read_bytes()),
                      'warmup_seconds': 60, 'measure_seconds': 180, 'drain_seconds': 90, 'fault_seconds': 40,
                      'analytical_amendment': {'revision': 'A1', 'files': {'adoption_audit': {'path': 'adoption.json'}}}}
            partial = {'run_id': rows[36]['run_id'], 'classification': 'partial_commit_timing', 'original_analyzer_exit': 2}
            def read(path):
                if Path(path) == app / 'experimento/FROZEN-PROTOCOL.json': return frozen
                if Path(path) == app / 'adoption.json': return {'assessments': [partial]}
                return original_read(path)
            def assess(row, policy):
                if row['run_id'] == partial['run_id']: return partial
                if fail_next: raise ValueError('headroom or unexplained evidence failure')
                return {'run_id': row['run_id'], 'classification': 'complete_original_evidence', 'original_analyzer_exit': 0}
            for name, value in [('APP', app), ('RUNTIME', runtime), ('REPORT', report), ('STATE', state_path), ('POLICY', policy_path)]:
                stack.enter_context(patch.object(controller, name, value))
            stack.enter_context(patch.object(controller, 'read', side_effect=read))
            for name in ('clean', 'fingerprints', 'published_checkout', 'audit_case', 'experimental_stop', 'terminate_child', 'command'):
                stack.enter_context(patch.object(controller, name))
            stack.enter_context(patch.object(controller, 'checked_amendment', return_value=frozen))
            stack.enter_context(patch.object(controller, 'output', side_effect=lambda args: '' if args[0] == 'docker' else 'published-head'))
            stack.enter_context(patch.object(q, 'resume_preflight', return_value=partial))
            stack.enter_context(patch.object(q, 'save_assessment'))
            stack.enter_context(patch.object(q, 'assess', side_effect=assess))
            child = MagicMock(pid=123); child.wait.return_value = 0
            spawn = stack.enter_context(patch.object(controller.subprocess, 'Popen', return_value=child))
            stack.enter_context(patch.object(controller.subprocess, 'run'))
            with redirect_stdout(io.StringIO()):
                if fail_next:
                    with self.assertRaisesRegex(ValueError, 'unexplained'): controller.execute('campaign', reviewed=True)
                else: controller.execute('campaign', reviewed=True)
            state = original_read(state_path)
            self.assertEqual((runtime / 'state-before-a1.json').read_bytes(), original_state_bytes)
            for row in rows[:37]:
                self.assertEqual((app / '.runtime/entrega04' / f"{row['run_id']}-{row['variant']}" / 'preserved.txt').read_text(), 'unchanged')
            started = [call.kwargs['env']['RUN_ID'] for call in spawn.call_args_list]
            self.assertEqual(started, [r['run_id'] for r in rows[37:38 if fail_next else 65]])
            for call in spawn.call_args_list:
                env = call.kwargs['env']
                self.assertEqual((env['WARMUP_SECONDS'], env['MEASURE_SECONDS'], env['DRAIN_SECONDS'], env['FAULT_SECONDS']), ('60', '180', '90', '40'))
            self.assertEqual(state['campaign_qualified'], [rows[36]['run_id']])
            self.assertNotIn(rows[36]['run_id'], state['campaign_completed'])
            return state

    def test_controller_only_launches_28_unused_and_preserves_partial(self):
        state = self.run_controller_fixture()
        self.assertEqual(state['phase'], 'campaign_complete')
        self.assertEqual(len(state['campaign_completed']), 64)
        self.assertEqual(state['campaign_accounted'], 65)

    def test_controller_stops_on_other_failure_without_next_uuid(self):
        state = self.run_controller_fixture(fail_next=True)
        self.assertEqual(state['phase'], 'attention_required')
        self.assertEqual(len(state['campaign_completed']), 36)


if __name__ == '__main__':
    unittest.main()
