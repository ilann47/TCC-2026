import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('comparison_report', Path(__file__).parents[1] / 'comparison_report.py')
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


def summary(variant='sync'):
    stats = {'n': 3, 'mean': 4.0, 'median': 3.0, 'p95': 8.0, 'p99': 9.0}
    return {'kind': 'validation', 'variant': variant, 'profile': 'steady', 'instrument_valid': True, 'issues': [],
            'run_id': 'test-run-' + variant, 'dataset_id': 'test-dataset', 'rate': 2, 'measure_seconds': 10,
            'offered': 3, 'accepted': 3, 'stored_at_observation_end': 3, 'stored_within_measurement': 2,
            'completed_per_second': 0.2, 'http_status_counts': {'201' if variant == 'sync' else '202': 3},
            'http_error_fraction': 0, 'dropped_iterations_all_phases': 0, 'dlq_terminal': 0, 'pending_retained': 0,
            'accepted_unreconciled': 0, 'stored_despite_unconfirmed_http': 0, 'integrity_mismatches': 0,
            'idempotent_replays': 0, '_duplicates': 0, '_path': '/synthetic/unit-test',
            '_manifest': {k: 'same' for k in ('warmup_seconds', 'drain_seconds', 'vus', 'application_images_sha256', 'instrument_source_sha256', 'analyzer_image_id')},
            'http_duration_ms': stats.copy(), 'send_to_response_ms': stats.copy(), 'send_to_commit_ms': stats.copy(),
            'instrumentation': {'enabled': True, 'max_accepted_not_committed': 1, 'max_kafka_lag': 1,
                                'generator': {'cpu_p95_percent_of_limit': 2, 'memory_max_percent_of_limit': 3},
                                'observer': {'cpu_p95_percent_of_limit': 2, 'memory_max_percent_of_limit': 3}},
            'recovery': {'applicable': False},
            'resources': {f'tcc-entrega04-{part}-1': {'cpu_percent': stats.copy(), 'memory_mib': stats.copy()}
                          for part in ('sync-api', 'async-api', 'consumer', 'postgres', 'kafka')}}


class ComparisonTests(unittest.TestCase):
    def pair(self):
        return {'sync': summary(), 'async': summary('async')}

    def row(self, report, text):
        return next(row for row in report['rows'] if row['metric'] == text)

    def test_http_commit_and_throughput_are_separate(self):
        pair = self.pair();pair['async']['send_to_commit_ms']['mean'] = 500
        report = REPORT.build_report(pair, 'normal')
        self.assertEqual(self.row(report, 'Resposta HTTP — média')['async'], '4,00 ms')
        self.assertEqual(self.row(report, 'Envio → commit no banco — média')['async'], '500,00 ms')
        self.assertEqual(self.row(report, 'Gravados/s dentro da medição')['sync'], '0,20 registros/s')

    def test_inapplicable_is_not_zero(self):
        report = REPORT.build_report(self.pair(), 'normal')
        self.assertEqual(self.row(report, 'Recuperação sustentada confirmada')['async'], REPORT.NA)
        self.assertEqual(self.row(report, 'Pico de lag Kafka amostrado')['sync'], REPORT.NA)

    def test_different_business_components_and_missing_resource(self):
        pair = self.pair();report = REPORT.build_report(pair, 'normal')
        row = self.row(report, 'CPU média — soma dos serviços do fluxo')
        self.assertEqual((row['sync'], row['async']), ('8,00 %', '16,00 %'))
        pair['async']['resources'].pop('tcc-entrega04-kafka-1')
        report = REPORT.build_report(pair, 'normal')
        self.assertEqual(self.row(report, 'CPU média — soma dos serviços do fluxo')['async'], REPORT.MISSING)
        self.assertTrue(any('indisponíveis' in text for text in report['warnings']))

    def test_no_commit_is_not_zero_latency(self):
        pair = self.pair();pair['async']['send_to_commit_ms'] = {'n': 0, 'mean': None}
        report = REPORT.build_report(pair, 'normal')
        self.assertEqual(self.row(report, 'Envio → commit no banco — média')['async'], 'Sem observações')

    def test_different_datasets_or_images_rejected(self):
        pair = self.pair();pair['async']['dataset_id'] = 'different'
        with self.assertRaisesRegex(ValueError, 'dataset_id'): REPORT.build_report(pair, 'normal')
        pair = self.pair();pair['async']['_manifest']['application_images_sha256'] = 'different'
        with self.assertRaisesRegex(ValueError, 'application_images'): REPORT.build_report(pair, 'normal')

    def test_consumer_scenario_has_no_fake_sync_baseline(self):
        report = REPORT.build_report({'async': summary('async')}, 'consumer-stop')
        self.assertTrue(all(row['sync'] == REPORT.NA for row in report['rows']))
        with self.assertRaises(ValueError): REPORT.build_report(self.pair(), 'consumer-stop')

    def test_recovery_not_observed_or_not_drained_is_explicit(self):
        value = summary('async')
        value['recovery'] = {'applicable': True, 'accepted_not_persisted_at_restore': 9,
                             'all_pre_restore_accepted_persisted': False, 'stable_throughput_recovery': {'observed': False}}
        self.assertEqual(REPORT.recovery_value(value, 'stable'), 'Não observada na janela')
        self.assertEqual(REPORT.recovery_value(value, 'backlog'), 'Não concluída na observação')
        value['recovery']['stable_throughput_recovery'] = {'observed': True, 'confirmed_after_restore_ms': 32100}
        self.assertEqual(REPORT.recovery_value(value, 'stable'), '32.100,00 ms')

    def test_html_escaping_and_missing_numbers(self):
        pair = self.pair();pair['sync']['_path'] = '<script>alert(1)</script>'
        page = REPORT.as_html(REPORT.build_report(pair, 'normal'))
        self.assertNotIn('<script>', page);self.assertIn('&lt;script&gt;', page)
        self.assertIn('Síncrona (201 após gravar)', page);self.assertIn('Assíncrona (202 após Kafka)', page)
        self.assertEqual(REPORT.number(float('nan')), REPORT.MISSING)
        self.assertEqual(REPORT.number(True), REPORT.MISSING)

    def test_validation_export_mismatch_and_invalid_instrument(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary);value = summary()
            (root / 'summary.json').write_text(json.dumps(value), encoding='utf-8')
            (root / 'manifest.txt').write_text('\n'.join(f'{k}={value[k]}' for k in ('run_id', 'dataset_id', 'variant', 'profile')), encoding='utf-8')
            (root / 'events.csv').write_text('event_id,phase\na,measure\nb,measure\nc,measure\nw,warmup\n', encoding='utf-8')
            rows = [{'event_id': key} for key in ('a', 'b', 'b', 'c', 'w')]
            (root / 'database.jsonl').write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
            self.assertEqual(REPORT.validate(root, 'sync', 'normal')['_duplicates'], 1)
            value['stored_at_observation_end'] = 7
            (root / 'summary.json').write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'divergem'): REPORT.validate(root, 'sync', 'normal')
            value['instrument_valid'] = False
            (root / 'summary.json').write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'íntegra'): REPORT.validate(root, 'sync', 'normal')


if __name__ == '__main__':
    unittest.main()
