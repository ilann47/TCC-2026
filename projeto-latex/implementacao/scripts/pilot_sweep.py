"""Bounded exploratory rate search, never freezes a scientific protocol.

Starts at the previously verified 5 events/s and doubles until the first
incomplete load or the explicit operator ceiling. No files/volumes are deleted.
Each complete run is preserved even when unsuitable as a reference candidate.
"""
import argparse
import json
from pathlib import Path
import uuid

from run_experiment import BASE, Compose, collect, write_json, utc_now, execute, K6_IMAGE


def candidate(summary, manifest):
    reasons = []
    if not summary:
        return False, ['normalization unavailable']
    if manifest.get('errors') or manifest.get('load_exit_code') != 0 or summary['instrumentation_issues']:
        reasons.append('instrumentation incomplete')
    if summary['dropped_iterations_all_phases'] != 0:
        reasons.append('generator dropped offered arrivals')
    if summary['http_error_rate'] != 0:
        reasons.append('HTTP errors observed')
    if summary['offered_events'] != summary['scheduled_offered_events']:
        reasons.append('offered volume differs from schedule')
    if summary['states'].get('persisted', 0) != summary['offered_events']:
        reasons.append('not every measurement UUID persisted by observation end')
    if summary['backlog_offset_max'] is None:
        reasons.append('no valid offset samples')
    return not reasons, reasons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-rate', type=int, required=True,
                        help='engineering stop ceiling, NOT an assumed sustainable capacity')
    parser.add_argument('--duration', type=int, required=True)
    parser.add_argument('--warmup', type=int, required=True)
    parser.add_argument('--drain', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.max_rate < 5 or args.duration <= 0 or args.warmup < 0 or args.drain <= 0:
        parser.error('positive durations and ceiling >= previous verified rate 5 required')
    root = args.output.resolve() / ('sweep-' + str(uuid.uuid4()))
    root.mkdir(parents=True, exist_ok=False)
    plan = {'profile': 'pilot', 'purpose': 'exploratory rate screening, not maximum-capacity estimation',
        'started_utc': utc_now(), 'start_rate': 5, 'factor': 2, 'ceiling_rate': args.max_rate,
        'measurement_seconds': args.duration, 'warmup_seconds': args.warmup, 'drain_seconds': args.drain,
        'rationale': '5 events/s previously verified; geometric search bounds trial count; ceiling limits resources, not a scientific threshold.',
        'reset_between_runs': False, 'independent_definitive_repetition': False,
        'stop_rule': 'first pair with errors, dropped arrivals, incomplete persistence, or missing instrumentation; all observations retained',
        'runs': [], 'last_pair_candidate_rate': None, 'scientific_protocol_frozen': False}
    write_json(root / 'screening.json', plan)
    compose = Compose(BASE / '.runtime/compose.env')
    execute(['docker', 'pull', K6_IMAGE], timeout=300)
    rate, block = 5, 0
    while rate <= args.max_rate:
        variants = ('sync', 'async') if block % 2 == 0 else ('async', 'sync')
        pair_ok = True
        for variant in variants:
            cfg = {'profile': 'pilot', 'scenario': 'rate_screening', 'variant': variant, 'rate': rate,
                'warmup_seconds': args.warmup, 'measurement_seconds': args.duration,
                'drain_seconds': args.drain, 'sample_interval_seconds': 2,
                'preallocated_vus': 10, 'max_vus': 50, 'http_timeout_seconds': 20,
                'payload_padding_bytes': 128, 'generator_cpus': 1, 'generator_memory': '512m',
                'lag_method': 'observer'}
            run, manifest, summary = collect(compose, root, cfg)
            acceptable, reasons = candidate(summary, manifest)
            pair_ok &= acceptable
            row = {'directory': str(run), 'variant': variant, 'rate': rate,
                   'candidate_for_long_confirmation': acceptable, 'reasons': reasons}
            if summary:
                row.update({k: summary[k] for k in ('offered_events', 'scheduled_offered_events',
                    'http_error_rate', 'dropped_iterations_all_phases', 'states', 'backlog_offset_max',
                    'end_to_end_ms', 'throughput_persisted_events_s', 'instrumentation_issues')})
            plan['runs'].append(row)
            write_json(root / 'screening.json', plan)
            print(json.dumps(row), flush=True)
            if manifest.get('errors') or not summary or summary['instrumentation_issues']:
                plan['stopped_reason'] = 'instrumentation error; do not continue searching under untrusted measurements'
                plan['finished_utc'] = utc_now()
                write_json(root / 'screening.json', plan)
                return 1
        if not pair_ok:
            plan['stopped_reason'] = 'first rate pair failed exploratory criteria'
            break
        plan['last_pair_candidate_rate'] = rate
        rate *= 2
        block += 1
    else:
        plan['stopped_reason'] = 'operator ceiling reached; maximum capacity remains unknown'
    plan['finished_utc'] = utc_now()
    write_json(root / 'screening.json', plan)
    print(json.dumps({'screening_report': str(root / 'screening.json'),
        'candidate_only': plan['last_pair_candidate_rate'], 'not_a_frozen_protocol': True}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
