"""Review regressions. These never invoke Docker or modify campaign evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review_commit_uncertainty as review


class UncertaintyReviewTest(unittest.TestCase):
    def setUp(self):
        self.event = {'http_status': '503', 'id_matches': 'false', 'db_present': 'true',
                      'commit_ms': '', 'dlq': 'false', 'pending_retained': 'false',
                      'retries': '0', 'idempotent_replays': '0'}
        self.logs = [{'milestone': 'request_received'},
                     {'milestone': 'request_failed', 'reason': 'database_unavailable'}]

    def finding(self):
        return review.uncertainty_finding(self.event, self.logs, 'sync')

    def test_narrow_finding_does_not_approve_collection(self):
        self.assertEqual('persisted_with_unobserved_commit_time_and_http_503', self.finding())

    def test_success_missing_marker_is_not_this_case(self):
        self.event.update(http_status='201', id_matches='true')
        self.assertEqual('unexplained_evidence_mismatch', self.finding())

    def test_other_failures_are_not_general_exception(self):
        for code in ('0', '409', '500', '202'):
            with self.subTest(code=code):
                self.event['http_status'] = code
                self.assertEqual('unexplained_evidence_mismatch', self.finding())

    def test_commit_marker_cannot_be_discarded(self):
        self.logs.append({'milestone': 'commit_completed'})
        self.assertEqual('unexplained_evidence_mismatch', self.finding())

    def test_recorded_latency_cannot_be_discarded(self):
        self.event['commit_ms'] = '12.3'
        self.assertEqual('unexplained_evidence_mismatch', self.finding())

    def test_no_persisted_row_is_not_this_case(self):
        self.event['db_present'] = 'false'
        self.assertEqual('unexplained_evidence_mismatch', self.finding())

    def test_no_failure_marker_is_not_explained(self):
        self.logs.pop()
        self.assertEqual('unexplained_evidence_mismatch', self.finding())

    def test_wrong_failure_reason_is_not_explained(self):
        self.logs[-1]['reason'] = 'event_id_content_conflict'
        self.assertEqual('unexplained_evidence_mismatch', self.finding())

    def test_conflicting_duplicate_failure_or_confirmation_is_rejected(self):
        for extra in (self.logs[-1], {'milestone': 'persistence_confirmed'}, self.logs[0]):
            with self.subTest(extra=extra):
                self.assertEqual('unexplained_evidence_mismatch',
                                 review.uncertainty_finding(self.event, self.logs + [extra], 'sync'))

    def test_async_is_not_silently_covered(self):
        self.assertEqual('unexplained_evidence_mismatch', review.uncertainty_finding(self.event, self.logs, 'async'))

    def test_no_mutation_of_evidence_objects(self):
        before = copy.deepcopy((self.event, self.logs))
        self.finding()
        self.assertEqual(before, (self.event, self.logs))

    def test_expected_canonical_hash_and_changed_content(self):
        client = {'experiment_sent': {'tags': {'event_id': 'event', 'iteration': '725',
                                             'occurred_at': '2026-10-06T00:00:00.725Z'}}}
        body = review.expected_body(client, 'dataset')
        self.assertEqual('2026-10-06T00:00:00.725000Z', body['occurred_at'])
        row = dict(body, content_hash=hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
        review.check_row(row, client, 'dataset')
        row['payload'] = {'value': 6}
        with self.assertRaisesRegex(ValueError, 'database content mismatch'):
            review.check_row(row, client, 'dataset')

    def test_checksum_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'SHA256SUMS').write_text('0' * 64 + '  ../outside\n')
            with self.assertRaisesRegex(ValueError, 'outside evidence'):
                review.verify_checksums(root)


if __name__ == '__main__':
    unittest.main()
