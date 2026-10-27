"""Offline evidence review, NOT a campaign gate or revised analyzer.

Reads the R2 snapshot and writes a new report only. Never edits raw evidence,
the frozen protocol, a validity verdict, plan, or controller journal.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

APP = Path(__file__).resolve().parents[1]
REPORT = APP / 'experimento/campanhas/2026-10-27-reduzida65-r2'
RUNTIME = APP / '.runtime/reduzida65-2026-10-27-r2'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def objects(path):
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            brace = line.find('{')
            if brace >= 0:
                yield json.loads(line[brace:])


def verify_checksums(root):
    names = set()
    for line in (root / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest, name = line.split(maxsplit=1)
        path = (root / name.lstrip('*')).resolve()
        require(path.parent == root.resolve(), 'checksum path outside evidence folder')
        require(path.name not in names, 'duplicate checksum path')
        names.add(path.name)
        require(sha(path) == digest, f'checksum mismatch: {root.name}/{path.name}')
    required = {'summary.json', 'manifest.txt', 'events.csv', 'database.jsonl',
                'app.log', 'k6.jsonl.gz', 'observation.jsonl', 'resources.tsv',
                'dlq.jsonl', 'retained.jsonl'}
    require(required <= names, 'incomplete checksum inventory')
    return len(names)


def expected_body(event, dataset):
    sent = event['experiment_sent']
    iteration = int(sent['tags']['iteration'])
    at = datetime.fromisoformat(sent['tags']['occurred_at'].replace('Z', '+00:00'))
    at = at.astimezone(timezone.utc)
    time = at.strftime('%Y-%m-%dT%H:%M:%S')
    if at.microsecond:
        time += f'.{at.microsecond:06d}'
    return {'actor_id': 'k6-experiment', 'entity_id': f'E{iteration}',
            'entity_type': 'experiment', 'event_id': sent['tags']['event_id'],
            'event_type': 'created', 'occurred_at': time + 'Z',
            'payload': {'value': iteration % 10}, 'source': 'experiment-' + dataset}


def check_row(row, event, dataset):
    body = expected_body(event, dataset)
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    require(row['content_hash'] == hashlib.sha256(encoded).hexdigest(), 'content hash mismatch')
    for field in body.keys() - {'occurred_at'}:
        require(row[field] == body[field], 'database content mismatch: ' + field)
    require(datetime.fromisoformat(row['occurred_at'].replace('Z', '+00:00')) ==
            datetime.fromisoformat(body['occurred_at'].replace('Z', '+00:00')), 'occurred_at mismatch')


def uncertainty_finding(event, milestones, variant):
    """A narrow diagnostic description; it does not make a collection valid."""
    commits = [m for m in milestones if m.get('milestone') == 'commit_completed']
    failures = [m for m in milestones if m.get('milestone') == 'request_failed'
                and m.get('reason') == 'database_unavailable']
    requests = [m for m in milestones if m.get('milestone') == 'request_received']
    confirmed = [m for m in milestones if m.get('milestone') == 'persistence_confirmed']
    if (variant == 'sync' and event['http_status'] == '503' and
            event['id_matches'] == 'false' and event['db_present'] == 'true' and
            not event['commit_ms'] and not commits and not confirmed and
            len(requests) == 1 and len(failures) == 1 and event['dlq'] == 'false' and
            event['pending_retained'] == 'false' and event['retries'] == '0' and
            event['idempotent_replays'] == '0'):
        return 'persisted_with_unobserved_commit_time_and_http_503'
    return 'unexplained_evidence_mismatch'


def audit_run(row, policy, stage):
    root = APP / '.runtime/entrega04' / f"{row['run_id']}-{row['variant']}"
    count = verify_checksums(root)
    before = sha(root / 'SHA256SUMS')
    meta = dict(line.split('=', 1) for line in (root / 'manifest.txt').read_text().splitlines() if '=' in line)
    summary = read(root / 'summary.json')
    for key in ('run_id', 'dataset_id', 'variant', 'profile', 'rate', 'vus'):
        require(str(row[key]) == meta[key], 'manifest identity mismatch: ' + key)
        if key in summary:
            require(str(row[key]) == str(summary[key]), 'summary identity mismatch: ' + key)
    for key in ('instrument_source_sha256', 'analyzer_image_id', 'application_images_sha256'):
        require(meta[key] == policy[key], 'frozen fingerprint mismatch: ' + key)
    kind = 'definitive' if stage == 'campaign' else 'calibration' if row['profile'] == 'steady' else 'validation'
    require(meta['kind'] == kind and summary['kind'] == kind and meta['working_tree'] == 'clean', 'kind/checkout mismatch')
    require(meta['k6_exit'] == '0' and meta['observer_exit'] == '0', 'collector failure')
    if row['profile'] != 'model':
        for key in ('warmup_seconds', 'measure_seconds', 'drain_seconds'):
            require(int(meta[key]) == policy[key], 'parameter mismatch: ' + key)
        for role in ('generator', 'observer'):
            for metric, suffix in (('cpu_p95_percent_of_limit', 'cpu_p95_percent_max'),
                                   ('memory_max_percent_of_limit', 'memory_percent_max')):
                value = summary['instrumentation'][role][metric]
                require(math.isfinite(value) and value <= policy[role + '_' + suffix], 'headroom failure')
    with (root / 'events.csv').open(newline='', encoding='utf-8') as stream:
        events = list(csv.DictReader(stream))
    indexed = {e['event_id']: e for e in events}
    require(len(indexed) == len(events), 'duplicate event CSV identity')
    client = defaultdict(dict)
    with gzip.open(root / 'k6.jsonl.gz', 'rt', encoding='utf-8') as stream:
        for line in stream:
            point = json.loads(line)
            data = point.get('data', {})
            tags = data.get('tags', {})
            metric = point.get('metric')
            if (point.get('type') != 'Point' or tags.get('run_id') != row['run_id'] or
                    tags.get('phase') not in ('warmup', 'measure') or
                    metric not in ('experiment_sent', 'experiment_response', 'http_req_duration')):
                continue
            require(tags['variant'] == row['variant'], 'client variant mismatch')
            event_id = tags['event_id']
            require(metric not in client[event_id], 'duplicate client point')
            client[event_id][metric] = data
    require(set(client) == set(indexed), 'client/CSV event set mismatch')
    milestones = defaultdict(list)
    for item in objects(root / 'app.log'):
        require(item.get('run_id') == row['run_id'], 'app log run mismatch')
        if item.get('event_id') in indexed:
            milestones[item['event_id']].append(item)
    database = {}
    for item in objects(root / 'database.jsonl'):
        event_id = item['event_id']
        require(event_id in indexed and event_id not in database, 'unknown/duplicate DB identity')
        check_row(item, client[event_id], row['dataset_id'])
        database[event_id] = item
    findings = []
    for event_id, event in indexed.items():
        points = client[event_id]
        require(set(points) == {'experiment_sent', 'experiment_response', 'http_req_duration'}, 'incomplete client evidence')
        response = points['experiment_response']['tags']
        require(event['phase'] == points['experiment_sent']['tags']['phase'] == response['phase'], 'phase mismatch')
        require(event['http_status'] == response['http_status'] and event['id_matches'] == response['id_matches'], 'response mismatch')
        require(math.isclose(float(event['http_duration_ms']), points['http_req_duration']['value'], abs_tol=1e-8), 'HTTP duration mismatch')
        require((event_id in database) == (event['db_present'] == 'true'), 'CSV/DB presence mismatch')
        commits = [m for m in milestones[event_id] if m.get('milestone') == 'commit_completed']
        require(bool(commits) == bool(event['commit_ms']), 'CSV/log commit mismatch')
        if bool(commits) != (event_id in database):
            finding = {'event_id': event_id, 'phase': event['phase'],
                       'finding': uncertainty_finding(event, milestones[event_id], row['variant']),
                       'http_status': int(event['http_status']), 'commit_time': None,
                       'row_observed': event_id in database,
                       'request_milestones': milestones[event_id]}
            findings.append(finding)
    measured = [e for e in events if e['phase'] == 'measure']
    expected = '201' if row['variant'] == 'sync' else '202'
    accepted = [e for e in measured if e['http_status'] == expected and e['id_matches'] == 'true']
    accepted_ids = {e['event_id'] for e in accepted}
    stored = [e for e in measured if e['db_present'] == 'true']
    timed = [e for e in stored if e['commit_ms']]
    statuses = dict(sorted(Counter(e['http_status'] for e in measured).items()))
    counts = {'offered': len(measured), 'accepted': len(accepted),
              'stored_at_observation_end': len(stored),
              'stored_despite_unconfirmed_http': sum(e['event_id'] not in accepted_ids for e in stored)}
    for key, value in counts.items():
        require(summary[key] == value, 'summary count mismatch: ' + key)
    require(summary['http_status_counts'] == statuses, 'summary status mismatch')
    require(summary['send_to_commit_ms']['n'] == len(timed), 'commit timing coverage mismatch')
    recognized = all(f['finding'] != 'unexplained_evidence_mismatch' for f in findings)
    mismatch_issues = sorted(f['event_id'] + ':incomplete_commit_db_evidence' for f in findings)
    require(sorted(summary['issues']) == mismatch_issues, 'other analyzer issues require separate review')
    require(summary['instrument_valid'] == (not mismatch_issues), 'original verdict inconsistent with issues')
    require(meta['analyzer_exit'] == ('2' if mismatch_issues else '0'), 'original analyzer exit inconsistent')
    require(sha(root / 'SHA256SUMS') == before, 'checksum inventory changed during review')
    # Recheck the raw files after parsing as well as before, not just their inventory.
    require(verify_checksums(root) == count, 'evidence inventory changed during review')
    return {'run_id': row['run_id'], 'stage': stage, 'block': int(row['block']),
            'profile': row['profile'], 'variant': row['variant'], 'rate': int(row['rate']),
            'summary_sha256': sha(root / 'summary.json'), 'raw_inventory_sha256': before,
            'raw_files_verified': count, 'original_instrument_valid': summary['instrument_valid'],
            'original_issues': summary['issues'], 'original_analyzer_exit': int(meta['analyzer_exit']),
            'counts_crosschecked': counts, 'http_status_counts': statuses,
            'stored_with_observed_commit_time': len(timed),
            'stored_without_observed_commit_time': len(stored) - len(timed),
            'findings': findings, 'all_mismatches_have_narrow_diagnostic_explanation': recognized,
            'original_validity_verdict_unchanged': True, 'campaign_admission_authorized': False}


def audit_snapshot():
    state_path = RUNTIME / 'state.json'
    state_hash = sha(state_path)
    state = read(state_path)
    require(state['phase'] == 'attention_required' and not state.get('controller_pid') and not state.get('runner_pid'), 'not a stopped review snapshot')
    policy = read(REPORT / 'policy.json')
    frozen = read(APP / 'experimento/FROZEN-PROTOCOL.json')
    require(sha(REPORT / 'policy.json') == state['policy_sha256'], 'policy changed')
    require(sha(REPORT / 'plan.csv') == frozen['plan_sha256'], 'plan changed')
    require(sha(APP / 'experimento/reduced_campaign.py') == frozen['controller_sha256'], 'controller changed')
    with (REPORT / 'plan.csv').open(newline='', encoding='utf-8') as stream:
        plan = list(csv.DictReader(stream))
    require(len(plan) == 65 and len({r['run_id'] for r in plan}) == 65, 'plan is not the fixed 65 UUIDs')
    completed = state['campaign_completed']
    require([r['run_id'] for r in plan[:len(completed)]] == completed, 'completed prefix mismatch')
    require(plan[len(completed)]['run_id'] == state['current']['run_id'], 'current run mismatch')
    pilots = read(REPORT / 'pilot-plan.json')
    require([r['run_id'] for r in pilots] == state['pilot_completed'], 'pilot journal mismatch')
    public = {r['run_id']: r for r in read(REPORT / 'pilot-catalog.json')['records']}
    audits = []
    for stage, rows in [('pilot', pilots), ('campaign', plan[:len(completed) + 1])]:
        for row in rows:
            print(f"review {stage} {row['run_id']}", file=sys.stderr, flush=True)
            item = audit_run(row, policy, stage)
            if stage == 'pilot':
                require(item['summary_sha256'] == public[row['run_id']]['summary_sha256'], 'pilot catalog mismatch')
            audits.append(item)
    for row in plan[len(completed) + 1:]:
        require(not (APP / '.runtime/entrega04' / f"{row['run_id']}-{row['variant']}").exists(), 'unexpected later attempted UUID')
    require(sha(state_path) == state_hash, 'journal changed during review')
    return {'kind': 'offline_formal_review_not_a_validity_amendment',
            'review_tool_sha256': sha(Path(__file__)), 'frozen_protocol_sha256': sha(APP / 'experimento/FROZEN-PROTOCOL.json'),
            'state_sha256': state_hash, 'policy_sha256': sha(REPORT / 'policy.json'),
            'plan_sha256': sha(REPORT / 'plan.csv'), 'pilot_runs_reviewed': len(pilots),
            'definitive_attempts_reviewed': len(completed) + 1,
            'previously_completed_runs': len(completed), 'not_started_UUIDs': len(plan) - len(completed) - 1,
            'raw_files_verified_before_and_after': sum(r['raw_files_verified'] for r in audits),
            'runs': audits, 'raw_evidence_modified': False, 'frozen_protocol_modified': False,
            'journal_modified': False, 'campaign_resumed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new .runtime review report (never overwrite)')
    args = parser.parse_args()
    target = args.output.resolve()
    require(RUNTIME.resolve() in target.parents, 'output must be in the R2 runtime directory')
    require(not target.exists(), 'refusing to overwrite any report')
    report = audit_snapshot()
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'runs'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
