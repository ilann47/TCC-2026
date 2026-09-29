"""Synthetic frozen plans verify constraints, not pilot or author decisions."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from protocol import C2_LEVELS, c2_rate, validate_protocol


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.protocol = {
            'frozen': True, 'frozen_by': 'synthetic fixture', 'frozen_utc': '2026-01-01T00:00:00Z',
            'pilot_evidence_path': 'synthetic fixture only', 'c4_choice_justification': 'synthetic fixture only',
            'random_seed': 1, 'warmup_seconds': 60, 'measurement_seconds': 300, 'repetitions': 10,
            'common_reference_rate': 6, 'drain_seconds': 10, 'sample_interval_seconds': 2,
            'recovery_stable_seconds': 5, 'offered_rate_tolerance_fraction': 0.01,
            'generator': {'preallocated_vus': 1, 'max_vus': 2, 'http_timeout_seconds': 5,
                          'generator_cpus': 1, 'generator_memory': '64m', 'payload_padding_bytes': 0},
            'cases': [{'scenario': 'C1', 'rate': 1},
                      *({'scenario': 'C2', 'level_fraction': fraction, 'rate': c2_rate(6, fraction)}
                        for fraction in C2_LEVELS),
                      {'scenario': 'C3', 'rate': 6, 'burst': {'rate': 7, 'at_seconds': 10, 'seconds': 5}},
                      {'scenario': 'C4C5', 'rate': 6, 'fault_by_variant': {
                          variant: {'service': 'postgres', 'at_seconds': 10, 'seconds': 5}
                          for variant in ('sync', 'async')}}]}

    def validate(self):
        return validate_protocol(self.protocol, check_pilot_path=False)

    def c2(self):
        return [case for case in self.protocol['cases'] if case['scenario'] == 'C2']

    def test_floor_rule_keeps_shared_absolute_integer_rates(self):
        self.assertEqual([case['rate'] for case in self.c2()], [1, 3, 4, 6])
        self.assertIsNone(self.validate())

    def test_low_reference_keeps_four_levels_even_when_integer_rates_repeat(self):
        self.protocol['common_reference_rate'] = 1
        for case in self.c2():
            case['rate'] = c2_rate(1, case['level_fraction'])
        self.assertEqual([case['rate'] for case in self.c2()], [1, 1, 1, 1])
        self.assertIsNone(self.validate())

    def test_c2_missing_level_is_rejected(self):
        self.protocol['cases'].remove(self.c2()[0])
        with self.assertRaisesRegex(ValueError, 'exactly four levels'):
            self.validate()

    def test_c2_duplicate_fraction_does_not_replace_missing_level(self):
        self.c2()[0]['level_fraction'] = 0.50
        with self.assertRaisesRegex(ValueError, 'exactly four levels'):
            self.validate()

    def test_c2_extra_case_is_rejected(self):
        self.protocol['cases'].append(dict(self.c2()[0]))
        with self.assertRaisesRegex(ValueError, 'exactly four levels'):
            self.validate()

    def test_c2_rate_must_follow_recorded_reference_and_rounding_rule(self):
        self.c2()[0]['rate'] = 2
        with self.assertRaisesRegex(ValueError, r'floor\(common_reference_rate'):
            self.validate()

    def test_c2_boolean_fraction_is_not_numeric_one(self):
        self.c2()[-1]['level_fraction'] = True
        with self.assertRaisesRegex(ValueError, 'registered numeric fractions'):
            self.validate()

    def test_c3_burst_must_exceed_reference_not_merely_its_base_rate(self):
        case = next(case for case in self.protocol['cases'] if case['scenario'] == 'C3')
        case['rate'] = 1
        for rate in (1, 5, 6):
            with self.subTest(rate=rate):
                case['burst']['rate'] = rate
                with self.assertRaisesRegex(ValueError, 'exceed the common stable reference'):
                    self.validate()

    def test_nonfinite_and_boolean_reference_rates_are_rejected(self):
        for value in (float('nan'), float('inf'), True):
            with self.subTest(value=value):
                self.protocol['common_reference_rate'] = value
                with self.assertRaisesRegex(ValueError, 'common_reference_rate'):
                    self.validate()

    def test_other_explicit_c4_service_choices_remain_supported(self):
        case = next(case for case in self.protocol['cases'] if case['scenario'] == 'C4C5')
        case['fault_by_variant']['sync']['service'] = 'sync-api'
        case['fault_by_variant']['async']['service'] = 'consumer'
        self.assertIsNone(self.validate())

    def test_definitive_validator_still_refuses_unfrozen_pilot_plan(self):
        self.protocol['frozen'] = False
        with self.assertRaisesRegex(ValueError, 'frozen must explicitly be true'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
