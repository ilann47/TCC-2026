"""Post-hoc recovery sensitivity. Reads frozen evidence; never replaces its verdict."""
import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def ns(value):
    match = re.fullmatch(r'(.*T\d\d:\d\d:\d\d)(?:\.(\d+))?(Z|[+-]\d\d:\d\d)', value)
    if not match:
        raise ValueError('Invalid timestamp')
    seconds = int(datetime.fromisoformat(match[1] + match[3].replace('Z', '+00:00')).timestamp())
    return seconds * 10**9 + int((match[2] or '').ljust(9, '0')[:9])

def objects(path):
    for line in path.read_text(encoding='utf-8').splitlines():
        if '{' in line:
            yield json.loads(line[line.index('{'):])

def verify(root):
    before = {}
    for line in (root/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        path = (root/name).resolve()
        assert path.parent == root.resolve() and name not in before
        assert sha(path) == digest, name
        before[name] = digest
    return before

def evaluate(events, observations, start, restored, seconds, rate, subtract_terminal):
    windows, streak, candidate, result = [], 0, None, None
    for second in range(0, seconds-9, 10):
        a, b = start + second*10**9, start + (second+10)*10**9
        if a < restored:
            continue
        commits = sum(e.get('stored') and a <= e.get('commit',-1) < b for e in events.values())
        errors = sum(a <= e.get('response',-1) < b and not e.get('accepted', False) for e in events.values())
        pending = [e for e in events.values() if e.get('accepted') and e['response'] <= b and e.get('commit',10**30) > b]
        terminal = sum(e.get('dlq_ack',10**30) <= b for e in pending)
        active = len(pending) - (terminal if subtract_terminal else 0)
        points = [p for p in observations if p['_time'] <= b]
        p = max(points,key=lambda p:p['_time']) if points else None
        limit = max(2,math.ceil(rate*.1))
        healthy = bool(p is not None and b-p['_time'] <= 3*10**9 and 'database_error' not in p and 'database_measured' in p and 'kafka_error' not in p and 'kafka_group_lag' in p and p['kafka_group_lag'] <= limit)
        ok = commits >= rate*9 and errors == 0 and active <= limit and healthy
        windows.append(dict(start_second=second, commits=commits, errors=errors,
                            accepted_without_commit=len(pending), dlq_acknowledged=terminal,
                            pending_for_criterion=active, healthy=healthy, qualifies=ok))
        if ok:
            if not streak: candidate=a
            streak += 1
            if streak==3 and result is None:
                result=dict(start_after_restore_s=(candidate-restored)/1e9,confirmed_after_restore_s=(b-restored)/1e9)
        else:
            streak=0
    return dict(observed=result is not None, timing=result, windows=windows)

def analyze(repo):
    public=repo/'implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1'
    rows=[r for r in json.loads((public/'per-run.json').read_text()) if r['profile']=='postgres-stop' and r['variant']=='async']
    results=[]
    assert len(rows)==5
    for row in sorted(rows,key=lambda r:r['block']):
        root=repo/'implementacao-java/.runtime/entrega04'/f"{row['run_id']}-async"
        before=verify(root)
        meta=dict(line.split('=',1) for line in (root/'manifest.txt').read_text().splitlines() if '=' in line)
        with (root/'events.csv').open(newline='',encoding='utf-8') as stream:
            events={e['event_id']:{'stored':e['db_present']=='true'} for e in csv.DictReader(stream) if e['phase']=='measure'}
        with gzip.open(root/'k6.jsonl.gz','rt',encoding='utf-8') as stream:
            for line in stream:
                p=json.loads(line); d=p.get('data',{}); tags=d.get('tags',{})
                if p.get('type')=='Point' and p.get('metric')=='experiment_response' and tags.get('run_id')==row['run_id'] and tags.get('event_id') in events and tags.get('phase')=='measure':
                    e=events[tags['event_id']]
                    assert 'response' not in e
                    e.update(response=ns(d['time']),accepted=tags['http_status']=='202' and tags['id_matches']=='true')
        for p in objects(root/'app.log'):
            if p.get('run_id') != row['run_id'] or p.get('event_id') not in events: continue
            field={'commit_completed':'commit','dlq_acknowledged':'dlq_ack'}.get(p.get('milestone'))
            if field:
                assert field not in events[p['event_id']]
                events[p['event_id']][field]=ns(p['timestamp'])
        assert sum(e.get('accepted',False) for e in events.values())==row['accepted']
        assert sum('dlq_ack' in e for e in events.values())==row['dlq_terminal']
        observations=list(objects(root/'observation.jsonl'))
        for p in observations:p['_time']=ns(p['sample_end'])
        args=(events,observations,int(meta['measurement_start_ms'])*10**6,ns(meta['fault_restore_utc']),int(meta['measure_seconds']),int(meta['rate']))
        original=evaluate(*args,False)
        exploratory=evaluate(*args,True)
        summary=json.loads((root/'summary.json').read_text())['recovery']['stable_throughput_recovery']
        assert original['observed']==summary['observed'], 'Original criterion failed to reproduce'
        if original['observed']:
            assert abs(original['timing']['confirmed_after_restore_s']-summary['confirmed_after_restore_ms']/1000)<1e-7
        assert verify(root)==before
        results.append(dict(block=row['block'],run_id=row['run_id'],raw_inventory_sha256=sha(root/'SHA256SUMS'),
                            verified_files=len(before),dlq_terminal=row['dlq_terminal'],original=original,exploratory=exploratory))
    return dict(kind='post_hoc_exploratory_sensitivity_not_campaign_reclassification',date='2026-10-30',
                change='Only pending count subtracts measured events with observed DLQ ACK by the window end; throughput/errors/fresh health/lag/3x10s/active-input bounds unchanged.',
                original_observed=sum(r['original']['observed'] for r in results),
                exploratory_observed=sum(r['exploratory']['observed'] for r in results),runs=results,
                caveat='Terminal DLQ is resolved as a destination, not persisted. This does not meet the original audit-storage objective and does not replace the frozen 1/5 verdict.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--repo',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); value=analyze(args.repo.resolve())
    with args.output.open('x',encoding='utf-8') as stream: json.dump(value,stream,ensure_ascii=False,indent=2); stream.write('\n')
    print(json.dumps({k:value[k] for k in ('original_observed','exploratory_observed')}))
