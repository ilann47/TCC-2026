"""Shared frozen-protocol validation and deterministic phase planning; no runtime operations."""
import math
from pathlib import Path

ALL_SERVICES = ('postgres', 'kafka', 'sync-api', 'async-api', 'consumer')
C2_LEVELS = (0.25, 0.50, 0.75, 1.00)


def c2_rate(common_reference_rate, level_fraction):
    """Integer k6 arrivals: floor(reference * fraction), with a minimum of one.

    The same absolute rate applies to both variants. At a small reference rate,
    levels may legitimately share an integer rate; their fractions stay distinct.
    """
    return max(1, math.floor(common_reference_rate * level_fraction))


def positive_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0)


def phases_for(config):
    phases = []
    cursor = 0
    if config['warmup_seconds']:
        phases.append({'name': 'warmup', 'analysis_phase': 'warmup', 'rate': config['rate'],
                       'seconds': config['warmup_seconds'], 'start_seconds': 0})
        cursor += config['warmup_seconds']
    burst = config.get('burst')
    if burst:
        lengths = [('measurement_before', burst['at_seconds'], config['rate']),
                   ('measurement_burst', burst['seconds'], burst['rate']),
                   ('measurement_after', config['measurement_seconds'] - burst['at_seconds'] - burst['seconds'], config['rate'])]
    else:
        lengths = [('measurement', config['measurement_seconds'], config['rate'])]
    for name, seconds, rate in lengths:
        if seconds > 0:
            phases.append({'name': name, 'analysis_phase': 'measurement', 'rate': rate,
                           'seconds': seconds, 'start_seconds': cursor})
            cursor += seconds
    offset = 0
    for phase in phases:
        phase['payload_offset'] = offset
        offset += phase['rate'] * phase['seconds']
    return phases


def validate_protocol(protocol, *, check_pilot_path=True):
    errors = []
    if protocol.get('frozen') is not True:
        errors.append('frozen must explicitly be true after pilot and author decision')
    if protocol.get('warmup_seconds') != 60 or protocol.get('measurement_seconds') != 300:
        errors.append('registered protocol requires 60 seconds warmup and 300 seconds measurement')
    if not isinstance(protocol.get('repetitions'), int) or protocol['repetitions'] < 10:
        errors.append('at least ten independent repetitions are required')
    if not isinstance(protocol.get('random_seed'), int):
        errors.append('random_seed must be an explicit integer')
    for field in ('pilot_evidence_path', 'c4_choice_justification', 'frozen_by', 'frozen_utc'):
        if not protocol.get(field):
            errors.append(f'{field} must be explicitly recorded')
    if check_pilot_path and protocol.get('pilot_evidence_path') and not Path(protocol['pilot_evidence_path']).is_file():
        errors.append('pilot evidence must be an existing report file')
    for field in ('common_reference_rate', 'drain_seconds', 'sample_interval_seconds', 'recovery_stable_seconds'):
        if not positive_number(protocol.get(field)):
            errors.append(f'{field} must be a positive pilot-calibrated value')
    generator = protocol.get('generator', {})
    for field in ('preallocated_vus', 'max_vus', 'http_timeout_seconds', 'generator_cpus'):
        if not isinstance(generator.get(field), (float, int)) or generator[field] <= 0:
            errors.append(f'generator.{field} must be explicitly frozen and positive')
    if not isinstance(generator.get('payload_padding_bytes'), int) or generator['payload_padding_bytes'] < 0:
        errors.append('generator.payload_padding_bytes must be explicitly frozen')
    if not generator.get('generator_memory'):
        errors.append('generator.generator_memory must be explicitly frozen')
    tolerance = protocol.get('offered_rate_tolerance_fraction')
    if not isinstance(tolerance, (float, int)) or not 0 <= tolerance < 1:
        errors.append('offered rate tolerance must be explicitly calibrated in [0,1)')
    cases = protocol.get('cases', [])
    if not {'C1', 'C2', 'C3', 'C4C5'}.issubset({row.get('scenario') for row in cases}):
        errors.append('cases must cover C1, C2, C3 and paired C4/C5 observation')
    c2_cases = [case for case in cases if case.get('scenario') == 'C2']
    fractions = [case.get('level_fraction') for case in c2_cases]
    if len(c2_cases) != len(C2_LEVELS) or any(fractions.count(level) != 1 for level in C2_LEVELS):
        errors.append('C2 requires exactly four levels: 0.25, 0.50, 0.75 and 1.00')
    reference = protocol.get('common_reference_rate')
    for case in cases:
        if type(case.get('rate')) is not int or case['rate'] <= 0:
            errors.append('each case needs a positive shared absolute integer rate')
        if case.get('scenario') == 'C2':
            fraction = case.get('level_fraction')
            if type(fraction) not in (int, float) or fraction not in C2_LEVELS:
                errors.append('C2 level_fraction must be one of the four registered numeric fractions')
            elif positive_number(reference) and case.get('rate') != c2_rate(reference, fraction):
                errors.append('C2 rate must equal max(1, floor(common_reference_rate * level_fraction))')
        if case.get('scenario') == 'C3':
            burst = case.get('burst', {})
            if not all(type(burst.get(k)) is int and burst[k] > 0 for k in ('rate', 'at_seconds', 'seconds')):
                errors.append('C3 burst parameters must be explicit positive integers')
            else:
                if positive_number(reference) and burst['rate'] <= reference:
                    errors.append('C3 burst rate must exceed the common stable reference rate')
                if burst['at_seconds'] + burst['seconds'] >= 300:
                    errors.append('C3 burst must fit inside the measurement window')
        if case.get('scenario') == 'C4C5':
            faults = case.get('fault_by_variant', {})
            for variant in ('sync', 'async'):
                fault = faults.get(variant, {})
                if fault.get('service') not in ALL_SERVICES:
                    errors.append(f'C4 service for {variant} requires an author choice')
                if not all(type(fault.get(k)) is int and fault[k] > 0 for k in ('at_seconds', 'seconds')):
                    errors.append(f'C4 timings for {variant} must be explicit')
                elif fault['at_seconds'] + fault['seconds'] >= 300:
                    errors.append('C4 interruption must leave time for recovery observation')
    if errors:
        raise ValueError('; '.join(errors))
