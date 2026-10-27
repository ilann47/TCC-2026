"""Audit and aggregate the completed R2/A1 campaign. Never changes raw evidence.

Experimental unit: one execution; comparison unit: one matched block/dataset.
Event distributions are computed within runs only, never pooled as replicates.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone, timedelta
import gzip
import json
import math
from pathlib import Path
import re
import shutil
import statistics
import sys
import qualified_analysis as q
import reduced_campaign as control
import review_commit_uncertainty as review

APP, REPORT, RUNTIME = review.APP, review.REPORT, review.RUNTIME
require = review.require
METRICS = ['http_success_p95_ms', 'http_success_median_ms', 'http_success_mean_ms',
           'response_success_p95_ms', 'commit_p95_ms', 'commit_median_ms', 'commit_mean_ms',
           'throughput_lower', 'throughput_upper', 'http_error_percent',
           'business_cpu_mean_percent', 'business_memory_mean_mib',
           'first_commit_after_restore_s', 'stable_recovery_confirmed_s', 'backlog_recovery_s']


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def stats(values):
    values = [v for v in values if v is not None]
    require(all(isinstance(v, (int, float)) and math.isfinite(v) for v in values), 'non-finite metric')
    if not values: return {'n': 0, 'values': []}
    ordered = sorted(values)
    return {'n': len(values), 'mean': statistics.mean(values), 'median': statistics.median(values),
            'sd_sample': statistics.stdev(values) if len(values) > 1 else None,
            'min': ordered[0], 'max': ordered[-1],
            'p95': ordered[math.ceil(.95 * len(values)) - 1],
            'p99': ordered[math.ceil(.99 * len(values)) - 1], 'values': values}


def instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def mem_mib(value):
    match = re.fullmatch(r'([0-9.]+)(GiB|MiB|KiB|B)', value.split(' / ')[0])
    require(match is not None, 'unknown memory unit')
    return float(match[1]) * {'GiB': 1024, 'MiB': 1, 'KiB': 1/1024, 'B': 1/1048576}[match[2]]


def business_resources(root, meta, variant):
    roles = ['sync-api', 'postgres'] if variant == 'sync' else ['async-api', 'consumer', 'postgres', 'kafka']
    names = {'tcc-entrega04-' + role + '-1' for role in roles}
    start = datetime.fromtimestamp(float(meta['measurement_start_ms']) / 1000, timezone.utc)
    end = start + timedelta(seconds=int(meta['measure_seconds']))
    batches = defaultdict(dict)
    with (root / 'resources.tsv').open(encoding='utf-8') as stream:
        for line in stream:
            parts = line.rstrip('\n').split('\t')
            if len(parts) != 4: continue
            at, name, cpu, memory = parts
            if name not in names or not start <= instant(at) < end: continue
            require(name not in batches[at], 'duplicate business resource sample')
            batches[at][name] = (float(cpu.removesuffix('%')), mem_mib(memory))
    require(batches and all(set(batch) == names for batch in batches.values()), 'incomplete business resource batch; no zero imputation')
    cpu = [sum(v[0] for v in batch.values()) for batch in batches.values()]
    memory = [sum(v[1] for v in batch.values()) for batch in batches.values()]
    return {'components': roles, 'batches': len(batches), 'cpu_percent': stats(cpu), 'memory_mib': stats(memory),
            'definition': 'sum at matching sampled batch timestamps; arithmetic means, 100% CPU = one logical CPU; not host load or financial cost'}


def consumer_pause_evidence(root, meta, measured):
    if meta['profile'] != 'consumer-stop': return None
    a, b = instant(meta['fault_stopped_utc']), instant(meta['fault_restore_utc'])
    during = set()
    with gzip.open(root / 'k6.jsonl.gz', 'rt', encoding='utf-8') as stream:
        for line in stream:
            point = json.loads(line)
            if point.get('type') != 'Point' or point.get('metric') != 'experiment_response': continue
            data = point['data']; tags = data['tags']
            if (tags.get('run_id') == meta['run_id'] and tags.get('phase') == 'measure' and
                    tags.get('http_status') == '202' and tags.get('id_matches') == 'true' and a <= instant(data['time']) < b):
                during.add(tags['event_id'])
    after = {item['event_id'] for item in review.objects(root / 'app.log')
             if item.get('milestone') == 'commit_completed' and instant(item['timestamp']) >= b}
    stored = {e['event_id'] for e in measured if e['db_present'] == 'true'}
    return {'accepted_during_stopped_consumer': len(during),
            'of_those_stored_final': len(during & stored),
            'of_those_with_commit_observed_after_restore': len(during & after),
            'pause_start_utc': meta['fault_stopped_utc'], 'restore_utc': meta['fault_restore_utc']}


def metrics_for_run(row, assessment):
    root = control.folder(row)
    summary, meta = review.read(root / 'summary.json'), control.manifest(root / 'manifest.txt')
    with (root / 'events.csv').open(newline='', encoding='utf-8') as stream:
        measured = [e for e in csv.DictReader(stream) if e['phase'] == 'measure']
    expected = '201' if row['variant'] == 'sync' else '202'
    accepted = [e for e in measured if e['http_status'] == expected and e['id_matches'] == 'true']
    http = stats([float(e['http_duration_ms']) for e in accepted])
    response = stats([float(e['response_ms']) for e in accepted])
    require(http['n'] == summary['accepted'] and len(measured) == summary['offered'], 'HTTP population mismatch')
    business = business_resources(root, meta, row['variant'])
    recovery = summary['recovery']
    stable = recovery.get('stable_throughput_recovery', {})
    applicable = recovery.get('applicable', False)
    bounds = assessment['completion_in_measurement']
    record = {**row, 'classification': assessment['classification'],
              'commit_primary_eligible': assessment['eligibility']['commit_latency_primary'],
              'offered': summary['offered'], 'accepted': summary['accepted'],
              'stored_final': summary['stored_at_observation_end'],
              'nonpersisted_final': summary['offered'] - summary['stored_at_observation_end'],
              'accepted_nonpersisted_final': sum(e['db_present'] != 'true' for e in accepted),
              'stored_without_confirmed_http': summary['stored_despite_unconfirmed_http'],
              'dlq_terminal': summary['dlq_terminal'], 'pending_retained': summary['pending_retained'],
              'accepted_unreconciled': summary['accepted_unreconciled'],
              'idempotent_replays': summary['idempotent_replays'], 'retry_scheduled': summary['retry_scheduled'],
              'database_duplicate_uuids': 0, 'integrity_mismatches': summary['integrity_mismatches'],
              'dropped_iterations_all_phases': summary['dropped_iterations_all_phases'],
              'http_error_percent': summary['http_error_fraction'] * 100,
              'http_success_n': http['n'], 'http_success_mean_ms': http.get('mean'),
              'http_success_median_ms': http.get('median'), 'http_success_p95_ms': http.get('p95'),
              'http_success_p99_ms': http.get('p99'), 'response_success_p95_ms': response.get('p95'),
              'commit_observed_n': summary['send_to_commit_ms']['n'],
              'commit_unobserved_n': assessment['timing']['stored_without_observed_time'],
              'commit_mean_ms': summary['send_to_commit_ms'].get('mean'),
              'commit_median_ms': summary['send_to_commit_ms'].get('median'),
              'commit_p95_ms': summary['send_to_commit_ms'].get('p95'),
              'commit_p99_ms': summary['send_to_commit_ms'].get('p99'),
              'throughput_lower': bounds['lower_per_second'], 'throughput_upper': bounds['upper_per_second'],
              'business_cpu_mean_percent': business['cpu_percent']['mean'],
              'business_memory_mean_mib': business['memory_mib']['mean'], 'resource_batches': business['batches'],
              'stable_recovery_observed': stable.get('observed') if applicable else None,
              'first_commit_after_restore_s': recovery.get('first_commit_after_restore_ms', 0) / 1000 if applicable and recovery.get('first_commit_after_restore_ms') is not None else None,
              'stable_recovery_confirmed_s': stable.get('confirmed_after_restore_ms', 0) / 1000 if applicable and stable.get('observed') else None,
              'backlog_recovery_s': recovery.get('backlog_persistence_recovery_ms', 0) / 1000 if applicable and recovery.get('backlog_persistence_recovery_ms') is not None else None,
              'accepted_not_persisted_at_restore': recovery.get('accepted_not_persisted_at_restore') if applicable else None,
              'all_pre_restore_accepted_persisted': recovery.get('all_pre_restore_accepted_persisted') if applicable else None,
              'max_accepted_not_committed': summary['instrumentation']['max_accepted_not_committed'],
              'max_kafka_lag': summary['instrumentation']['max_kafka_lag'],
              'collection_commit': meta['commit']}
    details = {'http_success_native_ms': http, 'response_success_ms': response, 'business_resources': business,
               'consumer_pause': consumer_pause_evidence(root, meta, measured),
               'instrument_headroom': {role: summary['instrumentation'][role] for role in ('generator', 'observer')}}
    return record, details


def pair_groups(records):
    pairs = defaultdict(dict)
    for row in records:
        pairs[(row['block'], row['profile'], row['rate'])][row['variant']] = row
    for (_, profile, _), pair in pairs.items():
        complete = all(r['commit_primary_eligible'] for r in pair.values())
        for row in pair.values(): row['paired_commit_primary_included'] = complete
        if profile != 'consumer-stop': require(set(pair) == {'sync', 'async'}, 'missing comparison pair')
    return pairs


def grouped(records, strict=False, sensitivity=False):
    buckets = defaultdict(list)
    for row in records: buckets[(row['profile'], row['rate'], row['variant'])].append(row)
    output = []
    for (profile, rate, variant), runs in sorted(buckets.items()):
        require(len(runs) == 5, 'group does not have five planned observations')
        eligible = [r for r in runs if not strict or r['paired_commit_primary_included']]
        metrics = {}
        for metric in METRICS:
            selected = [r for r in runs if (not strict or r['paired_commit_primary_included']) and
                        (sensitivity or not metric.startswith('commit_') or r['paired_commit_primary_included'])]
            metrics[metric] = stats([r[metric] for r in selected])
        output.append({'profile': profile, 'rate': rate, 'variant': variant, 'planned_n': 5,
                       'blocks': [r['block'] for r in runs], 'eligible_blocks_for_totals': [r['block'] for r in eligible], 'metrics': metrics,
                       'totals': {k: sum(r[k] for r in eligible) for k in ('offered', 'accepted', 'stored_final', 'nonpersisted_final', 'accepted_nonpersisted_final', 'dlq_terminal', 'pending_retained', 'accepted_unreconciled', 'stored_without_confirmed_http', 'commit_unobserved_n', 'database_duplicate_uuids', 'integrity_mismatches', 'dropped_iterations_all_phases')},
                       'stable_recovery_observed_n': sum(r['stable_recovery_observed'] is True for r in eligible),
                       'stable_recovery_not_observed_n': sum(r['stable_recovery_observed'] is False for r in eligible)})
    return output


def paired_comparisons(pairs):
    buckets = defaultdict(list)
    for (block, profile, rate), pair in sorted(pairs.items()):
        if profile == 'consumer-stop': continue
        a, s = pair['async'], pair['sync']
        require(a['dataset_id'] == s['dataset_id'], 'dataset mismatch')
        differences = {metric: a[metric] - s[metric] if a[metric] is not None and s[metric] is not None else None
                       for metric in METRICS if not metric.startswith('throughput_')}
        for metric in list(differences):
            if metric.startswith('commit_') and not a['paired_commit_primary_included']: differences[metric] = None
        differences['throughput_delta_lower'] = a['throughput_lower'] - s['throughput_upper']
        differences['throughput_delta_upper'] = a['throughput_upper'] - s['throughput_lower']
        buckets[(profile, rate)].append({'block': block, 'dataset_id': a['dataset_id'],
                                         'sync_run_id': s['run_id'], 'async_run_id': a['run_id'], 'differences_async_minus_sync': differences})
    out = []
    for (profile, rate), rows in sorted(buckets.items()):
        require(len(rows) == 5, 'five comparison pairs required')
        metric_stats = {metric: stats([r['differences_async_minus_sync'][metric] for r in rows])
                        for metric in rows[0]['differences_async_minus_sync']}
        directions = {}
        for metric, data in metric_stats.items():
            values = data['values']
            directions[metric] = ('insufficient_complete_pairs' if len(values) != 5 else
                                  'async_greater_in_all_five' if all(v > 0 for v in values) else
                                  'async_lower_in_all_five' if all(v < 0 for v in values) else 'mixed_or_tied')
        out.append({'profile': profile, 'rate': rate, 'pairs': rows, 'metrics': metric_stats,
                    'descriptive_direction_only': directions, 'population_significance_claimed': False})
    return out


def finalize(output):
    state = review.read(RUNTIME / 'state.json')
    require(state['phase'] == 'campaign_complete' and not state.get('controller_pid') and not state.get('runner_pid'), 'measurement not finished')
    frozen = review.read(APP / 'experimento/FROZEN-PROTOCOL.json')
    q.verify_extension(frozen)
    control.fingerprints(frozen)
    require(not control.output(['docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=tcc-entrega04']), 'experimental project still active')
    rows = control.plan_rows(REPORT / 'plan.csv'); control.validate_plan(rows)
    complete, partial = set(state['campaign_completed']), set(state['campaign_qualified'])
    require(len(complete) == len(state['campaign_completed']) and len(partial) == len(state['campaign_qualified']), 'duplicate journal UUID')
    require(not complete & partial and complete | partial == {r['run_id'] for r in rows}, 'journal not exactly the planned UUID union')
    require(len(complete | partial) == state['campaign_accounted'] == 65, 'not 65 accounted')
    require(not output.exists(), 'refusing to overwrite a result directory')
    output.mkdir(parents=True)
    for directory in ('runs', 'assessments', 'raw-checksums', 'manifests'): (output / directory).mkdir()
    catalog, records, details = [], [], []
    for index, row in enumerate(rows, 1):
        print(f"final audit {index}/65 {row['run_id']}", file=sys.stderr, flush=True)
        assessment = q.assess(row, frozen)
        saved = RUNTIME / 'assessments-a1' / (row['run_id'] + '.json')
        require(review.read(saved) == assessment, 'assessment changed after campaign')
        require((row['run_id'] in partial) == (assessment['classification'] == 'partial_commit_timing'), 'journal classification mismatch')
        root, name = control.folder(row), f"{row['run_id']}-{row['variant']}"
        meta = control.manifest(root / 'manifest.txt')
        if 'stop' in row['profile']: require(int(meta['fault_seconds_requested']) == frozen['fault_seconds'], 'fault duration changed')
        shutil.copyfile(root / 'summary.json', output / 'runs' / (name + '.json'))
        shutil.copyfile(saved, output / 'assessments' / (row['run_id'] + '.json'))
        shutil.copyfile(root / 'SHA256SUMS', output / 'raw-checksums' / (name + '.sha256'))
        allowed = ['kind', 'run_id', 'dataset_id', 'variant', 'profile', 'rate', 'vus', 'warmup_seconds', 'measure_seconds', 'drain_seconds', 'fault_seconds_requested',
                   'commit', 'working_tree', 'instrumentation_version', 'observer_enabled', 'resources_enabled', 'telemetry',
                   'instrument_source_sha256', 'application_images_sha256', 'analyzer_image_id',
                   'started_utc', 'measurement_start_ms', 'load_end_utc', 'collection_end_utc', 'fault_stop_command_utc', 'fault_stopped_utc', 'fault_restore_utc', 'k6_exit', 'observer_exit', 'analyzer_exit']
        public_meta = {k: meta[k] for k in allowed if k in meta}
        write(output / 'manifests' / (name + '.json'), {'projection_not_raw_manifest': True, 'fields': public_meta, 'original_manifest_sha256': review.sha(root / 'manifest.txt')})
        record, detail = metrics_for_run(row, assessment)
        records.append(record); details.append({'run_id': row['run_id'], **detail})
        catalog.append({**row, 'classification': assessment['classification'],
                        'summary_sha256': review.sha(root / 'summary.json'), 'assessment_sha256': review.sha(saved),
                        'raw_inventory_sha256': review.sha(root / 'SHA256SUMS'),
                        'raw_files_verified': len((root / 'SHA256SUMS').read_text().splitlines()), 'collection_commit': meta['commit']})
    pairs = pair_groups(records)
    write(output / 'per-run.json', records)
    write(output / 'per-run-details.json', details)
    with (output / 'per-run.csv').open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator='\n')
        writer.writeheader();writer.writerows(records)
    write(output / 'group-summary.json', grouped(records))
    write(output / 'strict-sensitivity.json', grouped(records, strict=True))
    write(output / 'partial-latency-sensitivity.json', grouped(records, sensitivity=True))
    write(output / 'paired.json', paired_comparisons(pairs))
    write(output / 'catalog.json', {'kind': 'completed_definitive_campaign_with_A1_qualification',
          'finished_utc': state['finished_utc'], 'planned_runs': 65, 'complete_original_evidence': len(complete),
          'partial_commit_timing': len(partial), 'conditions': 13, 'planned_repetitions': 5,
          'raw_files_verified': sum(r['raw_files_verified'] for r in catalog),
          'frozen_protocol_sha256': review.sha(APP / 'experimento/FROZEN-PROTOCOL.json'),
          'producer_source_sha256': review.sha(Path(__file__)), 'analysis_unit': 'run and matched block/dataset; never pooled events',
          'resource_definition': details[0]['business_resources']['definition'],
          'collection_commits': dict(Counter(r['collection_commit'] for r in records)), 'runs': catalog})
    for file in output.rglob('*'):
        if file.is_file():
            content = file.read_text(encoding='utf-8')
            require(not re.search(r'C:\\Users|/mnt/c/Users|ilan\.wendling|password|api_key', content, re.I), 'private data in public output')
    with (output / 'SHA256SUMS').open('x', encoding='utf-8', newline='\n') as stream:
        for file in sorted(p for p in output.rglob('*') if p.is_file() and p.name != 'SHA256SUMS'):
            stream.write(f'{review.sha(file)}  {file.relative_to(output).as_posix()}\n')
    print(json.dumps({'output': str(output), 'complete': len(complete), 'partial': len(partial), 'runs': 65,
                      'raw_files_verified': sum(r['raw_files_verified'] for r in catalog)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    destination = args.output.resolve()
    require(APP.resolve() in destination.parents, 'output outside application workspace')
    finalize(destination)
