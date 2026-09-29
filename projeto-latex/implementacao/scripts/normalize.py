"""Offline reconciliation of immutable run artifacts; Python standard library only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from evidence_gate import definitive_evidence_issues


def read_jsonl(path: Path):
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        start = line.find('{')
        if start < 0:
            continue
        try:
            value = json.loads(line[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            # Accept a JSON log envelope emitted by the container runtime/k6.
            if isinstance(value.get('msg'), str) and value['msg'].startswith('{'):
                try:
                    value = json.loads(value['msg'])
                except json.JSONDecodeError:
                    pass
            records.append(value)
    return records


def percentile(values, proportion):
    """Linear interpolation, inclusive [0, 1], defined also for a single value."""
    if not values:
        return None
    data = sorted(values)
    position = (len(data) - 1) * proportion
    low, high = math.floor(position), math.ceil(position)
    return data[low] + (data[high] - data[low]) * (position - low)


def describe(values):
    data = [float(value) for value in values if value is not None and math.isfinite(value)]
    return {
        'n': len(data), 'mean': statistics.mean(data) if data else None,
        'median': statistics.median(data) if data else None,
        'sample_sd': statistics.stdev(data) if len(data) > 1 else None,
        'min': min(data) if data else None, 'max': max(data) if data else None,
        'p95': percentile(data, .95), 'p99': percentile(data, .99),
    }


def milestone(record):
    return record.get('milestone', record.get('event', record.get('stage', '')))


def parse_lag(output):
    """Ignore client host/IDs; Kafka log end and committed positions are not UUID counts."""
    rows = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 6 or not parts[2].isdigit():
            continue
        values = []
        for token in parts[3:6]:
            values.append(int(token) if token.isdigit() else None)
        rows.append(dict(group=parts[0], topic=parts[1], partition=int(parts[2]),
                         committed_offset=values[0], log_end_offset=values[1], lag=values[2]))
    return rows


def memory_bytes(value):
    multipliers = {'B': 1, 'kB': 1000, 'MB': 1000**2, 'GB': 1000**3,
                   'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3, 'TiB': 1024**4}
    for unit in sorted(multipliers, key=len, reverse=True):
        if value.strip().endswith(unit):
            try:
                return float(value.strip()[:-len(unit)]) * multipliers[unit]
            except ValueError:
                return None
    return None


def write_csv(path, records, fields):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)


def normalize(run_dir: Path, output_dir: Path | None = None):
    config = json.loads((run_dir / 'config.json').read_text(encoding='utf-8'))
    manifest = json.loads((run_dir / 'manifest.json').read_text(encoding='utf-8'))
    target = output_dir or run_dir / 'analysis'
    target.mkdir(parents=True, exist_ok=False)
    run_id = config['run_id']
    generator = [r for r in read_jsonl(run_dir / 'generator.jsonl') if r.get('run_id') == run_id]
    logs = [r for r in read_jsonl(run_dir / 'application.jsonl') if r.get('run_id') == run_id]
    sends = [r for r in generator if r.get('kind') == 'request_sent']
    responses = {r['event_id']: r for r in generator if r.get('kind') == 'http_response'}
    event_logs = defaultdict(list)
    for record in logs:
        if record.get('event_id'):
            event_logs[record['event_id']].append(record)
    for records in event_logs.values():
        records.sort(key=lambda r: r.get('wall_time_ns', 0))
    database = {}
    if (run_dir / 'database.csv').exists():
        with (run_dir / 'database.csv').open(encoding='utf-8', newline='') as stream:
            database = {r['event_id']: r for r in csv.DictReader(stream) if r.get('event_id')}
    reconciled = []
    for sent in sends:
        event_id = sent['event_id']
        response = responses.get(event_id, {})
        entries = event_logs[event_id]
        commits = [r for r in entries if milestone(r) == 'commit_completed']
        first_commit = commits[0] if commits else None
        dlq = [r for r in entries if milestone(r) == 'dlq_acknowledged']
        broker = [r for r in entries if milestone(r) == 'broker_acknowledged']
        attempts = [r for r in entries if milestone(r) == 'processing_attempt']
        retries = [r for r in entries if milestone(r) == 'retry_scheduled']
        accepted = 200 <= response.get('http_status', 0) < 300
        latency = first_commit['wall_time_ns'] / 1_000_000 - sent['sent_at_ms'] if first_commit else None
        # A negative duration flags incomparable clocks; never silently clamp it to zero.
        clock_error = latency is not None and latency < 0
        if first_commit:
            state = 'persisted' if first_commit.get('status') == 'persisted' else 'duplicate'
        elif event_id in database:
            state = 'persisted_without_commit_instrumentation'
        elif dlq:
            state = 'terminal_dlq'
        elif response.get('http_status') == 409:
            state = 'conflict_rejected'
        elif accepted:
            state = 'accepted_unresolved_at_window_end'
        elif not response:
            state = 'http_response_missing'
        else:
            state = 'http_rejected_or_transport_error'
        reconciled.append({
            'run_id': run_id, 'event_id': event_id, 'variant': config['variant'],
            'scenario': config['scenario'], 'phase': sent['phase'],
            'sent_at_ms': sent['sent_at_ms'], 'http_status': response.get('http_status'),
            'http_accepted': accepted, 'http_wall_duration_ms': response.get('http_wall_duration_ms'),
            'http_transport_duration_ms': response.get('http_transport_duration_ms'),
            'commit_wall_time_ns': first_commit.get('wall_time_ns') if first_commit else None,
            'end_to_end_ms': None if clock_error else latency, 'clock_error': clock_error,
            'broker_ack_duration_ms': broker[0].get('duration_ms') if broker else None,
            'database_row_observed': event_id in database, 'state': state,
            'processing_attempts': len(attempts), 'retries_scheduled': len(retries),
            'consumer_deliveries': sum(r.get('attempt') == 1 for r in attempts),
            'redelivery_observations': max(0, sum(r.get('attempt') == 1 for r in attempts) - 1),
            'dlq_confirmations': len(dlq), 'duplicate_observations': sum(r.get('status') == 'duplicate' for r in commits),
        })
    write_csv(target / 'events.csv', reconciled, list(reconciled[0]) if reconciled else [
        'run_id', 'event_id', 'variant', 'phase', 'state', 'end_to_end_ms'])

    measured = [r for r in reconciled if r['phase'] == 'measurement']
    phase_sends = [r for r in sends if r['phase'] == 'measurement']
    offsets = {phase['name']: phase['start_seconds'] for phase in config.get('phases', [])}
    test_starts = [r['phase_start_ms'] - offsets.get(r.get('segment'), 0) * 1000 for r in sends]
    measure_start = min(test_starts) + config.get('warmup_seconds', 0) * 1000 if test_starts else None
    measure_end = measure_start + config['measurement_seconds'] * 1000 if measure_start is not None else None
    # Window length is scheduled measurement, including empty seconds and segment boundaries.
    duration = config['measurement_seconds']
    unique_in_window = {r['event_id'] for r in measured if r['state'] == 'persisted'
                        and measure_start is not None
                        and measure_start * 1_000_000 <= r['commit_wall_time_ns'] < measure_end * 1_000_000}
    summary_path = run_dir / 'k6-summary.json'
    k6_summary = json.loads(summary_path.read_text(encoding='utf-8')) if summary_path.exists() else {}
    dropped = k6_summary.get('metrics', {}).get('dropped_iterations', {}).get('values', {}).get('count')
    # k6 omits a counter that was never emitted. Missing summary is unknown, not zero.
    if dropped is None and summary_path.exists():
        dropped = 0
    point_records = read_jsonl(run_dir / 'k6-points.jsonl')
    dropped_measured = sum(r.get('data', {}).get('value', 0) for r in point_records
                           if r.get('type') == 'Point' and r.get('metric') == 'dropped_iterations'
                           and r.get('data', {}).get('tags', {}).get('phase') == 'measurement')
    lag_samples = read_jsonl(run_dir / 'lag.jsonl')
    stats_samples = read_jsonl(run_dir / 'resources.jsonl')
    resources = defaultdict(lambda: {'cpu': [], 'memory': []})
    for sample in stats_samples:
        for record in sample.get('containers', []):
            name = record.get('Name', record.get('ID', 'unknown'))
            try:
                resources[name]['cpu'].append(float(record.get('CPUPerc', '').rstrip('%')))
            except ValueError:
                pass
            mem = memory_bytes(record.get('MemUsage', '').split('/')[0])
            if mem is not None:
                resources[name]['memory'].append(mem)
    lags = []
    for sample in lag_samples:
        rows = sample.get('partitions', [])
        if rows and all(r['lag'] is not None for r in rows):
            lags.append({'wall_time_ns': sample['wall_time_ns'], 'lag': sum(r['lag'] for r in rows)})
    recovery = None
    resumed = [r for r in manifest.get('fault_events', []) if r.get('action') == 'started']
    if resumed:
        resume_time = resumed[-1]['wall_time_ns']
        observations = [s for s in lags if s['wall_time_ns'] >= resume_time]
        zero = next((s for s in observations if s['lag'] == 0), None)
        if zero:
            recovery = (zero['wall_time_ns'] - resume_time) / 1_000_000_000
    issues = []
    for artifact in ('generator.jsonl', 'application.jsonl', 'database.csv', 'k6-points.jsonl', 'resources.jsonl'):
        if not (run_dir / artifact).is_file():
            issues.append('essential observation artifact missing: ' + artifact)
    if config.get('variant') == 'async' and not (run_dir / 'lag.jsonl').is_file():
        issues.append('essential observation artifact missing: lag.jsonl')
    if not summary_path.exists():
        issues.append('k6 summary missing: run may have been interrupted')
    if any(r['clock_error'] for r in reconciled):
        issues.append('negative wall-clock duration detected; affected samples excluded')
    if any(r['state'] == 'persisted_without_commit_instrumentation' for r in measured):
        issues.append('database rows lack post-commit instrumentation; no fabricated latency')
    if not phase_sends:
        issues.append('no measurement requests recorded')
    if len(responses) < len(sends):
        issues.append('one or more sent requests lack response records')
    if manifest.get('load_exit_code') != 0:
        issues.append('load generator did not exit successfully')
    if type(manifest.get('database_export_exit_code')) is not int or manifest['database_export_exit_code'] != 0:
        issues.append('database export success absent or failed')
    if type(manifest.get('application_log_export_exit_code')) is not int or manifest['application_log_export_exit_code'] != 0:
        issues.append('application log export success absent or failed')
    if manifest.get('errors'):
        issues.append('collection manifest records execution errors')
    if manifest.get('fault_errors'):
        issues.append('fault control did not complete as planned')
    expected_offered = sum(p['rate'] * p['seconds'] for p in config.get('phases', [])
                           if p['analysis_phase'] == 'measurement')
    deviation = abs(len(measured) - expected_offered) / expected_offered if expected_offered else None
    if config.get('offered_rate_tolerance_fraction') is not None and deviation is not None:
        if deviation > config['offered_rate_tolerance_fraction']:
            issues.append('actual offered volume deviated beyond the frozen tolerance')
    measured_ids = {r['event_id'] for r in measured}
    measured_logs = [r for r in logs if r.get('event_id') in measured_ids]
    error_milestones = {'request_failed', 'publication_unconfirmed', 'dlq_unconfirmed', 'dlq_acknowledged'}
    errors_by_stage = Counter((milestone(r), r.get('reason', 'unspecified')) for r in measured_logs
                             if milestone(r) in error_milestones)
    offset_delivery_counts = Counter((r.get('topic'), r.get('partition'), r.get('offset')) for r in logs
                                     if milestone(r) == 'message_received')
    publication_attempts = sum(milestone(r) == 'request_received' and r.get('variant') == 'async'
                               for r in measured_logs)
    publication_failures = sum(milestone(r) == 'publication_unconfirmed' for r in measured_logs)
    try:
        eligibility_issues = definitive_evidence_issues(run_dir, config, manifest)
    except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
        # A malformed gate input cannot turn into a positive eligibility result.
        eligibility_issues = ['definitive evidence verification failed closed: ' + type(error).__name__]
    result = {
        'run_id': run_id, 'profile': config['profile'], 'variant': config['variant'], 'scenario': config['scenario'],
        'eligible_definitive_observation': config['profile'] == 'definitive' and not issues and not eligibility_issues,
        'definitive_eligibility_issues': eligibility_issues,
        'scientific_conclusion_produced': False,
        'measurement_seconds': duration, 'measurement_start_ms': measure_start, 'measurement_end_ms': measure_end,
        'offered_events': len(measured), 'offered_rate_events_s': len(measured) / duration,
        'scheduled_offered_events': expected_offered, 'offered_volume_deviation_fraction': deviation,
        'http_accepted_events': sum(r['http_accepted'] for r in measured),
        'committed_unique_within_measurement_window': len(unique_in_window),
        'throughput_persisted_events_s': len(unique_in_window) / duration,
        'completed_after_send_by_observation_end': sum(r['commit_wall_time_ns'] is not None for r in measured),
        'states': dict(Counter(r['state'] for r in measured)),
        'http_error_rate': sum(not r['http_accepted'] for r in measured) / len(measured) if measured else None,
        'end_to_end_ms': describe([r['end_to_end_ms'] for r in measured]),
        'http_wall_duration_ms': describe([r['http_wall_duration_ms'] for r in measured]),
        'http_transport_duration_ms': describe([r['http_transport_duration_ms'] for r in measured]),
        'broker_ack_duration_ms': describe([r['broker_ack_duration_ms'] for r in measured]),
        'retry_attempts_scheduled': sum(r['retries_scheduled'] for r in measured),
        'event_redelivery_observations': sum(r['redelivery_observations'] for r in measured),
        'kafka_offset_redelivery_observations_all_phases': sum(max(0, count - 1) for count in offset_delivery_counts.values()),
        'duplicate_observations': sum(r['duplicate_observations'] for r in measured),
        'dlq_confirmed_events': sum(r['dlq_confirmations'] > 0 for r in measured),
        'publication_unconfirmed_rate': publication_failures / publication_attempts if publication_attempts else None,
        'errors_by_stage_and_reason': [{'stage': key[0], 'reason': key[1], 'observations': count}
                                     for key, count in sorted(errors_by_stage.items())],
        'dropped_iterations_all_phases': dropped,
        'dropped_iterations_measurement': dropped_measured if (run_dir / 'k6-points.jsonl').exists() else None,
        'backlog_offset_max': max((s['lag'] for s in lags), default=None),
        'first_observed_zero_lag_after_resume_seconds': recovery,
        'resources_all_phases': {name: {'cpu_percent': describe(data['cpu']), 'memory_bytes': describe(data['memory'])}
                                for name, data in resources.items()},
        'milestone_counts_all_phases': dict(Counter(milestone(r) for r in logs)),
        'instrumentation_issues': issues,
        'notes': [
            'End-to-end uses send Date.now() and log emitted after DB transaction commit, identically for both variants.',
            'Date.now() has millisecond resolution; cross-process duration uses wall clock. Monotonic clocks are not subtracted across processes.',
            'HTTP transport duration excludes initial connection and is reported separately from wall duration.',
            'Unresolved at the observation deadline is not automatically lost; DLQ/conflict are distinct terminal states.',
            'Lag is Kafka offset position difference, not a count of accepted minus persisted UUIDs.',
            'First observed zero lag is descriptive; it is not the sustained scientific recovery criterion or throughput stability.',
            'Descriptive statistics are per run; no confidence interval, hypothesis test or architectural winner is inferred.',
            'Resource summaries currently include warmup, measurement and drain; raw timestamps permit phase-specific reanalysis.',
        ],
    }
    if config['profile'] == 'pilot':
        result['notes'].insert(0, 'PILOT CALIBRATION ONLY. Provisional settings; excluded from definitive repetitions and architectural conclusions.')
    elif config['profile'] != 'definitive':
        result['notes'].insert(0, 'FUNCTIONAL VALIDATION ONLY. This run is neither pilot calibration nor definitive TCC experiment.')
    (target / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    timeline = []
    pending = set()
    transitions = []
    for row in measured:
        response = responses.get(row['event_id'], {})
        if row['http_accepted']:
            transitions.append((response['finished_at_ms'], 'accepted', row['event_id']))
        if row['commit_wall_time_ns']:
            transitions.append((row['commit_wall_time_ns'] / 1_000_000, 'persisted', row['event_id']))
    already_persisted = set()
    for instant, kind, event_id in sorted(transitions):
        if kind == 'persisted':
            already_persisted.add(event_id)
            pending.discard(event_id)
        elif event_id not in already_persisted:
            pending.add(event_id)
        timeline.append({'wall_time_ms': instant, 'kind': kind, 'event_id': event_id,
                         'accepted_not_yet_persisted_uuids': len(pending)})
    write_csv(target / 'backlog_uuid.csv', timeline, ['wall_time_ms', 'kind', 'event_id', 'accepted_not_yet_persisted_uuids'])
    write_csv(target / 'backlog_offsets.csv', lags, ['wall_time_ns', 'lag'])
    return result


def checksums(run_dir: Path):
    result = {}
    for path in sorted(run_dir.rglob('*')):
        if path.is_file() and path.name != 'checksums.sha256.json':
            result[path.relative_to(run_dir).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (run_dir / 'checksums.sha256.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def seal_inputs(run_dir: Path):
    """Seal finished raw inputs before analysis; no circular hash of analysis output."""
    path = run_dir / 'inputs.sha256.json'
    if path.exists():
        raise FileExistsError('Input hash manifest already exists; sealed inputs are immutable')
    result = {}
    for item in sorted(run_dir.rglob('*')):
        relative = item.relative_to(run_dir)
        if (item.is_file() and relative.parts[0] != 'analysis'
                and item.name not in ('checksums.sha256.json', 'inputs.sha256.json')):
            result[relative.as_posix()] = hashlib.sha256(item.read_bytes()).hexdigest()
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = normalize(args.run_dir, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
