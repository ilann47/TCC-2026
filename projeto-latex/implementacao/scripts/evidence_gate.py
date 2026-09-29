"""Fail-closed structural/provenance gate; never certifies scientific conclusions."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from protocol import ALL_SERVICES, phases_for, validate_protocol

ESSENTIAL_FILES = ('config.json', 'manifest.json', 'payloads.json', 'generator.jsonl',
                   'application.jsonl', 'database.csv', 'k6-summary.json', 'k6-points.jsonl',
                   'resources.jsonl', 'protocol.json', 'pilot_evidence.snapshot', 'inputs.sha256.json')
CORE_SOURCES = ('docker-compose.yml', 'Dockerfile', 'requirements.txt', 'scripts/load.js',
                'scripts/run_experiment.py', 'scripts/normalize.py',
                'scripts/evidence_gate.py', 'scripts/protocol.py',
                'app/sync_api/main.py', 'app/async_api/main.py', 'app/consumer/main.py',
                'app/shared/observability.py', 'app/shared/database.py')


def finite(value, *, positive=False):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and (value > 0 if positive else True))


def utc_ms(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone absent')
    return parsed.timestamp() * 1000


def safe_file(root, relative):
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
        raise ValueError('missing or out-of-scope file')
    return candidate


def fault_timing_observation(config, manifest, *, measurement_start_ms, measurement_end_ms,
                             observation_start_ms, observation_end_ms):
    """Reconcile fault commands without inventing an upper runtime-delay tolerance.

    Actual command/readiness delays are descriptive outcomes, not grounds to reject
    a slow recovery. A complete injection must still begin in the measurement
    window, hold the stopped service for the planned duration, and be observed.
    """
    fault = config.get('fault')
    if not fault:
        return None
    result = {'service': fault.get('service'), 'issues': []}
    issues = result['issues']
    actions = ('stop_requested', 'stopped', 'start_requested', 'started', 'ready')
    events = manifest.get('fault_events')
    if not isinstance(events, list) or any(not isinstance(event, dict) for event in events):
        issues.append('fault command events must be an explicit list of records')
        return result
    if any(event.get('service') != fault.get('service') for event in events):
        issues.append('fault command service differs from the configured frozen fault')
    matching = {action: [event for event in events if event.get('action') == action] for action in actions}
    for action, records in matching.items():
        if len(records) != 1:
            issues.append('fault command requires exactly one observed action: ' + action)
    if any(len(records) != 1 for records in matching.values()):
        return result
    timestamps = {action: records[0].get('wall_time_ns') for action, records in matching.items()}
    if any(type(value) is not int or value <= 0 for value in timestamps.values()):
        issues.append('fault command timestamps must be positive integer nanoseconds')
        return result
    result['timestamps_ns'] = timestamps
    if [event.get('action') for event in events if event.get('action') in actions] != list(actions):
        issues.append('fault command records are not in the required action order')
    if any(timestamps[before] > timestamps[after] for before, after in zip(actions, actions[1:])):
        issues.append('fault command timestamps are not in the required action order')
    bounds = (measurement_start_ms, measurement_end_ms, observation_start_ms, observation_end_ms)
    if any(not finite(value, positive=True) for value in bounds):
        issues.append('fault timing requires valid measurement and observation windows')
        return result
    # Decimal conversion preserves the recorded millisecond resolution without
    # floating-point rounding around the epoch-sized nanosecond timestamps.
    measurement_start_ns, measurement_end_ns, observation_start_ns, observation_end_ns = (
        int(Decimal(str(value)) * 1_000_000) for value in bounds)
    if not (observation_start_ns <= measurement_start_ns < measurement_end_ns <= observation_end_ns):
        issues.append('fault measurement window is outside the recorded observation')
    if any(not observation_start_ns <= value <= observation_end_ns for value in timestamps.values()):
        issues.append('fault command occurred outside the recorded observation')
    if not all(type(fault.get(key)) is int and fault[key] > 0 for key in ('at_seconds', 'seconds')):
        issues.append('fault timing configuration must contain positive integer seconds')
        return result
    target_ns = measurement_start_ns + fault['at_seconds'] * 1_000_000_000
    stop_request_ns = timestamps['stop_requested']
    if not measurement_start_ns <= stop_request_ns < measurement_end_ns:
        issues.append('fault stop request must occur inside the measurement window')
    if stop_request_ns < target_ns:
        issues.append('fault stop request preceded the planned measurement-relative target')
    hold_ns = timestamps['start_requested'] - timestamps['stopped']
    planned_hold_ns = fault['seconds'] * 1_000_000_000
    if hold_ns < planned_hold_ns:
        issues.append('fault stopped hold was shorter than the planned interruption')
    result.update({
        'planned_at_seconds': fault['at_seconds'],
        'planned_stopped_hold_seconds': fault['seconds'],
        'stop_request_delay_seconds': (stop_request_ns - target_ns) / 1_000_000_000,
        'stop_command_seconds': (timestamps['stopped'] - stop_request_ns) / 1_000_000_000,
        'observed_stopped_hold_seconds': hold_ns / 1_000_000_000,
        'stopped_hold_overrun_seconds': (hold_ns - planned_hold_ns) / 1_000_000_000,
        'start_command_seconds': (timestamps['started'] - timestamps['start_requested']) / 1_000_000_000,
        'readiness_after_started_seconds': (timestamps['ready'] - timestamps['started']) / 1_000_000_000,
        'stopped_to_ready_seconds': (timestamps['ready'] - timestamps['stopped']) / 1_000_000_000,
        'ready_after_measurement_end_seconds': max(0, timestamps['ready'] - measurement_end_ns) / 1_000_000_000,
    })
    return result


def definitive_evidence_issues(run_dir: Path, config, manifest):
    """A complete observation is not a replicated experiment or a validated conclusion.

    Inputs are sealed BEFORE normalization. The final checksum file is intentionally
    not required here, avoiding a circular dependency on this analysis' own output.
    """
    if config.get('profile') != 'definitive':
        return ['profile is not definitive']
    issues = []

    def problem(message):
        if message not in issues:
            issues.append(message)

    required = list(ESSENTIAL_FILES)
    if config.get('variant') == 'async':
        required.append('lag.jsonl')
    for name in required:
        path = run_dir / name
        if not path.is_file() or not path.stat().st_size:
            problem('essential artifact missing or empty: ' + name)

    def load_json(name, expected_type=dict):
        try:
            value = json.loads((run_dir / name).read_text(encoding='utf-8'))
            if not isinstance(value, expected_type):
                raise ValueError('wrong JSON shape')
            return value
        except (OSError, UnicodeError, ValueError):
            problem('invalid or absent JSON artifact: ' + name)
            return expected_type()

    def load_jsonl(name):
        records = []
        try:
            for line_number, line in enumerate((run_dir / name).read_text(encoding='utf-8').splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError('not an object')
                    records.append(value)
                except ValueError:
                    problem(f'invalid JSONL record in {name}:{line_number}')
            if not records:
                problem('no parseable observations: ' + name)
        except (OSError, UnicodeError):
            problem('unreadable JSONL artifact: ' + name)
        return records

    for key in ('load_exit_code', 'database_export_exit_code', 'application_log_export_exit_code'):
        if type(manifest.get(key)) is not int or manifest[key] != 0:
            problem('successful explicit exit required: ' + key)
    for key in ('errors', 'fault_errors'):
        if manifest.get(key) != []:
            problem('manifest must contain an empty error list: ' + key)
    if manifest.get('profile') != 'definitive' or manifest.get('run_id') != config.get('run_id'):
        problem('manifest/config identity or profile mismatch')
    try:
        uuid.UUID(config['run_id'])
    except (KeyError, TypeError, ValueError, AttributeError):
        problem('run_id must be a UUID')
    if config.get('variant') not in ('sync', 'async'):
        problem('variant is not sync or async')

    # Frozen plan and pilot proof travel with the run, not a mutable external path.
    protocol = load_json('protocol.json')
    try:
        validate_protocol(protocol, check_pilot_path=False)
    except (ValueError, TypeError, KeyError):
        problem('frozen protocol is incomplete or invalid')
    for name, key in (('protocol.json', 'protocol_sha256'), ('pilot_evidence.snapshot', 'pilot_evidence_sha256')):
        path = run_dir / name
        if not path.is_file() or config.get(key) != hashlib.sha256(path.read_bytes()).hexdigest():
            problem('frozen evidence digest missing or mismatched: ' + name)
    for key in ('warmup_seconds', 'measurement_seconds', 'drain_seconds', 'sample_interval_seconds',
                'offered_rate_tolerance_fraction', 'common_reference_rate', 'recovery_stable_seconds',
                'repetitions', 'random_seed'):
        if key not in config or config.get(key) != protocol.get(key):
            problem('run differs from frozen protocol: ' + key)
    repetition = config.get('repetition')
    if (type(repetition) is not int or type(protocol.get('repetitions')) is not int
            or not 0 <= repetition < protocol['repetitions']):
        problem('repetition index absent or outside frozen schedule')
    for key, value in protocol.get('generator', {}).items():
        if key not in config or config[key] != value:
            problem('generator differs from frozen protocol: ' + key)
    matching = [case for case in protocol.get('cases', [])
                if case.get('scenario') == config.get('scenario') and type(config.get('rate')) is int
                and case.get('rate') == config.get('rate')
                and (case.get('scenario') != 'C2' or (type(config.get('level_fraction')) in (int, float)
                     and case.get('level_fraction') == config.get('level_fraction')))
                and case.get('burst') == config.get('burst')
                and case.get('fault_by_variant', {}).get(config.get('variant')) == config.get('fault')]
    if not matching:
        problem('case/level/rate/burst/fault does not match a frozen case')
    try:
        if config.get('phases') != phases_for(config):
            problem('phase plan differs from deterministic frozen configuration')
    except (KeyError, TypeError, ValueError):
        problem('phase configuration is incomplete')

    # Validate every sealed input and every recorded source. No environment secrets are read.
    input_hashes = load_json('inputs.sha256.json')
    for name in required:
        if name != 'inputs.sha256.json' and name not in input_hashes:
            problem('essential input absent from hash manifest: ' + name)
    for relative, digest in input_hashes.items():
        try:
            if hashlib.sha256(safe_file(run_dir, relative).read_bytes()).hexdigest() != digest:
                problem('sealed input checksum mismatch: ' + relative)
        except (ValueError, OSError, TypeError):
            problem('sealed input missing or unsafe: ' + str(relative))
    environment = manifest.get('environment', {})
    source_hashes = environment.get('sources_sha256', {})
    if not isinstance(source_hashes, dict) or not set(CORE_SOURCES).issubset(source_hashes):
        problem('source manifest does not cover the essential implementation')
        source_hashes = source_hashes if isinstance(source_hashes, dict) else {}
    for relative, digest in source_hashes.items():
        snapshot = 'source_snapshot/' + relative
        try:
            if (hashlib.sha256(safe_file(run_dir, snapshot).read_bytes()).hexdigest() != digest
                    or snapshot not in input_hashes):
                problem('source snapshot unsealed or checksum mismatch: ' + relative)
        except (ValueError, OSError, TypeError):
            problem('source snapshot missing or unsafe: ' + str(relative))
    for key in ('os', 'python', 'cpu_count', 'cpu_model', 'docker_server', 'compose_version', 'clock_notes'):
        if not environment.get(key):
            problem('runtime evidence absent: ' + key)
    if environment.get('runtime_secret_values_included') is not False:
        problem('sanitized runtime evidence is not explicitly identified')
    containers = environment.get('containers', [])
    if not set(ALL_SERVICES).issubset({c.get('service') for c in containers}):
        problem('runtime container/resource manifest is incomplete')
    if any(not c.get('image_id') or not finite(c.get('nano_cpus'), positive=True)
           or not finite(c.get('memory_limit_bytes'), positive=True) for c in containers):
        problem('container image/resource identification is incomplete')
    images = environment.get('images', [])
    references = {i.get('reference') for i in images}
    if ('grafana/k6:1.4.0' not in references or not images
            or any(not i.get('image_id') for i in images)
            or not {c.get('image') for c in containers}.issubset(references)):
        problem('runtime image identifiers/digests are incomplete')

    started_ms = finished_ms = observation_ms = None
    try:
        started_ms, finished_ms = utc_ms(manifest['started_utc']), utc_ms(manifest['finished_utc'])
        observation_ms = manifest['observation_end_ns'] / 1_000_000
        frozen_ms = utc_ms(protocol['frozen_utc'])
        if not started_ms <= finished_ms <= observation_ms or frozen_ms > started_ms:
            raise ValueError('timestamp order')
    except (KeyError, TypeError, ValueError, AttributeError):
        problem('run/freeze UTC timestamps absent, invalid or out of order')
    generator = load_jsonl('generator.jsonl')
    logs = load_jsonl('application.jsonl')
    payloads = load_json('payloads.json', list)
    sends = [r for r in generator if r.get('kind') == 'request_sent']
    responses = [r for r in generator if r.get('kind') == 'http_response']
    scheduler_excess = [r for r in generator if r.get('kind') == 'scheduler_excess_iteration']
    if any(r.get('run_id') != config.get('run_id') for r in generator + logs):
        problem('foreign or uncorrelated records in run artifacts')
    if not sends or len({r.get('event_id') for r in sends}) != len(sends):
        problem('sent UUIDs absent or duplicated by the generator')
    if len(responses) != len(sends) or {r.get('event_id') for r in sends} != {r.get('event_id') for r in responses}:
        problem('send/response correlation is incomplete or ambiguous')
    phase_map = {p.get('name'): p for p in config.get('phases', [])}
    excess_identities = set()
    for excess in scheduler_excess:
        phase = phase_map.get(excess.get('segment'), {})
        rate, seconds = phase.get('rate'), phase.get('seconds')
        iteration_index = excess.get('iteration_index')
        if (not phase or excess.get('phase') != phase.get('analysis_phase')
                or type(rate) is not int or type(seconds) is not int or rate <= 0 or seconds <= 0
                or type(excess.get('scheduled_count')) is not int or excess['scheduled_count'] != rate * seconds
                or type(iteration_index) is not int or iteration_index < rate * seconds):
            problem('scheduler excess iteration does not match its phase budget and index')
        else:
            identity = (excess['segment'], iteration_index)
            if identity in excess_identities:
                problem('scheduler excess iteration is duplicated within its segment')
            excess_identities.add(identity)
        timestamp = excess.get('wall_time_ms')
        if (not finite(timestamp, positive=True) or started_ms is None or observation_ms is None
                or not started_ms <= timestamp <= observation_ms):
            problem('scheduler excess iteration lacks a valid observed wall clock')
    origins = []
    for sent in sends:
        phase = phase_map.get(sent.get('segment'), {})
        if (not phase or sent.get('phase') != phase.get('analysis_phase')
                or sent.get('phase_seconds') != phase.get('seconds')
                or not finite(sent.get('sent_at_ms'), positive=True)
                or not finite(sent.get('phase_start_ms'), positive=True)):
            problem('send phase/timestamp evidence is incomplete')
            continue
        if not sent['phase_start_ms'] <= sent['sent_at_ms'] < sent['phase_start_ms'] + phase['seconds'] * 1000 + 1:
            problem('send occurred outside its declared phase')
        origins.append(sent['phase_start_ms'] - phase['start_seconds'] * 1000)
        index = sent.get('payload_index')
        if (type(index) is not int or not 0 <= index < len(payloads)
                or payloads[index].get('event_id') != sent.get('event_id')
                or payloads[index].get('payload', {}).get('run_id') != config.get('run_id')):
            problem('sent event lacks its preserved payload identity')
    if not {'warmup', 'measurement'}.issubset({r.get('phase') for r in sends}):
        problem('both warmup and measurement phases require observed sends')
    measurement_start = measurement_end = None
    if origins:
        if max(origins) - min(origins) > 1:
            problem('phase clocks do not share a consistent test origin')
        measurement_start = min(origins) + config.get('warmup_seconds', 0) * 1000
        measurement_end = measurement_start + config.get('measurement_seconds', 0) * 1000
        if started_ms is None or observation_ms is None or not started_ms <= min(origins) < measurement_end <= observation_ms:
            problem('observation timestamps do not contain the scheduled measurement')
    fault_observation = fault_timing_observation(config, manifest,
        measurement_start_ms=measurement_start, measurement_end_ms=measurement_end,
        observation_start_ms=started_ms, observation_end_ms=observation_ms)
    if fault_observation:
        for issue in fault_observation['issues']:
            problem(issue)
    for response in responses:
        if (not finite(response.get('sent_at_ms'), positive=True)
                or not finite(response.get('finished_at_ms'), positive=True)
                or not finite(response.get('http_wall_duration_ms'))
                or type(response.get('http_status')) is not int
                or response.get('finished_at_ms', 0) < response.get('sent_at_ms', 0)):
            problem('HTTP response timestamps/status are incomplete')
    if any(not finite(r.get('wall_time_ns'), positive=True) or not finite(r.get('monotonic_ns'), positive=True)
           or not r.get('milestone') for r in logs):
        problem('application milestones lack required clocks or identity')

    database_ids = set()
    try:
        with (run_dir / 'database.csv').open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            if not {'event_id', 'content_hash', 'persisted_at', 'run_id'}.issubset(reader.fieldnames or []):
                problem('database export schema is incomplete')
            for row in reader:
                if row.get('run_id') != config.get('run_id') or not row.get('event_id') or not row.get('content_hash'):
                    problem('database export contains uncorrelated or incomplete rows')
                if row.get('event_id') in database_ids:
                    problem('database export contains duplicate UUID rows')
                database_ids.add(row.get('event_id'))
    except (OSError, UnicodeError, csv.Error):
        problem('database export is missing or invalid')
    if not {r.get('event_id') for r in logs if r.get('milestone') == 'commit_completed'}.issubset(database_ids):
        problem('post-commit observations are not reconciled with the SQL export')
    k6 = load_json('k6-summary.json')
    # Boundary scheduler invocations are recorded but return before sending HTTP;
    # they must reconcile with k6 iterations without inventing an offered event.
    for metric, expected in (('http_reqs', len(responses)), ('iterations', len(sends) + len(scheduler_excess))):
        if k6.get('metrics', {}).get(metric, {}).get('values', {}).get('count') != expected:
            problem('k6 summary count missing or inconsistent: ' + metric)
    points = load_jsonl('k6-points.jsonl')
    measurement_points = [p for p in points if p.get('type') == 'Point' and p.get('metric') == 'http_req_duration'
                          and p.get('data', {}).get('tags', {}).get('phase') == 'measurement']
    if not measurement_points:
        problem('k6 measurement HTTP points are absent')
    for point in measurement_points:
        try:
            utc_ms(point['data']['time'])
            if not finite(point['data']['value']):
                raise ValueError('not finite')
        except (KeyError, TypeError, ValueError, AttributeError):
            problem('k6 point has invalid timestamp/value')
    resources = load_jsonl('resources.jsonl')
    observed_containers = set()
    for sample in resources:
        if sample.get('exit_code') != 0 or not finite(sample.get('wall_time_ns'), positive=True):
            continue
        for container in sample.get('containers', []):
            try:
                cpu = float(container['CPUPerc'].rstrip('%'))
                if not math.isfinite(cpu) or '/' not in container.get('MemUsage', ''):
                    raise ValueError('invalid resource')
                observed_containers.add(container.get('Container', container.get('ID')))
            except (KeyError, ValueError, TypeError, AttributeError):
                continue
    if not containers or any(not any(str(c.get('id', '')).startswith(str(item)) for item in observed_containers)
                             for c in containers):
        problem('valid CPU/memory observations absent for one or more runtime containers')
    if config.get('variant') == 'async':
        lag = load_jsonl('lag.jsonl')
        if not any(sample.get('exit_code') == 0 and finite(sample.get('wall_time_ns'), positive=True)
                   and sample.get('partitions') and all(type(p.get('lag')) is int
                   and type(p.get('committed_offset')) is int and type(p.get('log_end_offset')) is int
                   for p in sample['partitions']) for sample in lag):
            problem('async offset/lag observations are absent or unknown')
    return issues
