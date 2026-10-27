"""Auditable, resumable local controller for the authorized 65-run campaign.

Never rebuilds images, changes the instrument, silently retries a failed run,
or counts pilot/demo evidence as definitive. Linux/WSL + Python stdlib only.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import sys
import uuid

APP = Path(__file__).resolve().parents[1]
REPORT = APP / 'experimento/campanhas/2026-10-27-reduzida65-r2'
RUNTIME = APP / '.runtime/reduzida65-2026-10-27-r2'
STATE = RUNTIME / 'state.json'
POLICY = REPORT / 'policy.json'
FIELDS = ['block', 'profile', 'variant', 'rate', 'run_id', 'dataset_id', 'vus']
IMAGES = ['tcc-java-2026-sync-api:latest', 'tcc-java-2026-async-api:latest', 'tcc-java-2026-consumer:latest', 'postgres:16-alpine', 'apache/kafka:3.9.1']
CHILD = None


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def command(args, **kwargs):
    return subprocess.run(args, cwd=APP, check=True, text=True, **kwargs)


def output(args):
    return command(args, capture_output=True).stdout.strip()


def clean():
    if output(['git', 'status', '--porcelain']):
        raise ValueError('Checkout modificado: revisar e commitar antes de medir; não há limpeza automática.')


def instrument_hash():
    base = 'experimento/analyzer/src/main/java/br/com/ilan/tcc/experiment'
    files = ['experimento/run.sh', 'experimento/load.js'] + sorted(str(p.relative_to(APP)).replace('\\', '/') for p in (APP / base).glob('*.java'))
    return sha(''.join(f'{sha((APP / p).read_bytes())}  {p}\n' for p in files).encode())


def fingerprints(policy):
    if instrument_hash() != policy['instrument_source_sha256']:
        raise ValueError('Instrumentação mudou; preservar evidências e recalibrar antes de medir.')
    image = output(['docker', 'image', 'inspect', '-f', '{{.Id}}', 'tcc-pilot-analyzer:local'])
    apps = output(['docker', 'image', 'inspect', '-f', '{{.Id}}', *IMAGES]) + '\n'
    if image != policy['analyzer_image_id'] or sha(apps.encode()) != policy['application_images_sha256']:
        raise ValueError('Imagens diferem da calibração; não reconstruir/reclassificar silenciosamente.')
    for field, name in [('base_compose_sha256', 'docker-compose.yml'), ('observer_compose_sha256', 'experimento/compose.yml')]:
        if sha((APP / name).read_bytes()) != policy[field]:
            raise ValueError(f'Compose alterado: {name}')


def make_plan(policy):
    rng = random.Random(policy['seed']);rows = []
    conditions = [('steady', 12), ('steady', 24), ('steady', 36), ('steady', 48), ('burst', 48), ('postgres-stop', 12), ('consumer-stop', 12)]
    for block in range(1, 6):
        order = list(enumerate(conditions));rng.shuffle(order)
        for index, (profile, rate) in order:
            dataset = str(uuid.uuid4())
            variants = ['async'] if profile == 'consumer-stop' else (['sync', 'async'] if (block + index) % 2 else ['async', 'sync'])
            for variant in variants:
                rows.append(dict(block=block, profile=profile, variant=variant, rate=rate, run_id=str(uuid.uuid4()), dataset_id=dataset, vus=176 if 'stop' in profile else 128))
    return rows


def csv_bytes(rows):
    stream = io.StringIO(newline='');writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
    writer.writeheader();writer.writerows(rows);return stream.getvalue().encode()


def plan_rows(path):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key in ('block', 'rate', 'vus'): row[key] = int(row[key])
        for key in ('run_id', 'dataset_id'): uuid.UUID(row[key])
    return rows


def validate_plan(rows):
    if len(rows) != 65 or len({r['run_id'] for r in rows}) != 65:
        raise ValueError('Plano deve ter 65 UUIDs únicos.')
    counts, pairs = {}, {}
    for row in rows:
        key = (row['profile'], row['rate'], row['variant']);counts[key] = counts.get(key, 0) + 1
        pairs.setdefault((row['block'], row['profile'], row['rate']), []).append(row)
        expected = 176 if 'stop' in row['profile'] else 128
        if row['vus'] != expected: raise ValueError('VUs divergentes')
    expected = {(p, r, v) for p, r in [('steady', 12), ('steady', 24), ('steady', 36), ('steady', 48), ('burst', 48), ('postgres-stop', 12)] for v in ('sync', 'async')} | {('consumer-stop', 12, 'async')}
    if set(counts) != expected or set(counts.values()) != {5}:
        raise ValueError('Matriz/repetições divergentes')
    for block in range(1, 6):
        if sum(r['block'] == block for r in rows) != 13: raise ValueError('Bloco incompleto')
    for (_, profile, _), pair in pairs.items():
        if profile == 'consumer-stop':
            if len(pair) != 1 or pair[0]['variant'] != 'async': raise ValueError('Consumidor não pareado')
        elif len(pair) != 2 or {r['variant'] for r in pair} != {'sync', 'async'} or pair[0]['dataset_id'] != pair[1]['dataset_id']:
            raise ValueError('Par inválido')


def prepare():
    if STATE.exists(): raise ValueError('Sessão já existe; usar status/audit, nunca sobrescrever.')
    policy = read(POLICY);rows = make_plan(policy);validate_plan(rows)
    for file in ('plan.csv', 'pilot-plan.json'):
        if (REPORT / file).exists(): raise ValueError('Plano já existe; não substituir UUIDs.')
    (REPORT / 'plan.csv').write_bytes(csv_bytes(rows))
    pilots = []
    for index, (profile, rate) in enumerate([('model', 5), ('steady', 48), ('burst', 48), ('postgres-stop', 12), ('consumer-stop', 12)]):
        dataset = str(uuid.uuid4())
        variants = ['async'] if profile == 'consumer-stop' else (['sync', 'async'] if index % 2 == 0 else ['async', 'sync'])
        for variant in variants:
            pilots.append(dict(block=1, profile=profile, rate=rate, variant=variant, run_id=str(uuid.uuid4()), dataset_id=dataset, vus=1 if profile == 'model' else 176 if 'stop' in profile else 128))
    write(REPORT / 'pilot-plan.json', pilots)
    write(STATE, dict(phase='prepared', policy_sha256=sha(POLICY.read_bytes()), pilot_completed=[], campaign_completed=[], created_utc=now(), updated_utc=now()))
    print('Planos preservados: 9 validações/piloto, depois 65 execuções definitivas. Nenhuma carga iniciada.')


def folder(row):
    return APP / '.runtime/entrega04' / f"{row['run_id']}-{row['variant']}"


def manifest(path):
    return dict(line.split('=', 1) for line in path.read_text(encoding='utf-8').splitlines() if '=' in line)


def verify_raw(root):
    lines = (root / 'SHA256SUMS').read_text().splitlines()
    for line in lines:
        digest, name = line.split(maxsplit=1);path = (root / name.lstrip('*')).resolve()
        if path.parent != root.resolve() or sha(path.read_bytes()) != digest:
            raise ValueError(f'Checksum/caminho inválido: {root.name}/{name}')
    return len(lines)


def headroom(summary, policy):
    reasons = []
    for role in ('generator', 'observer'):
        values = summary.get('instrumentation', {}).get(role, {})
        for metric, limit in [('cpu_p95_percent_of_limit', policy[f'{role}_cpu_p95_percent_max']), ('memory_max_percent_of_limit', policy[f'{role}_memory_percent_max'])]:
            value = values.get(metric)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value > limit:
                reasons.append(f'{role}:{metric}:headroom')
    return reasons


def steady_reasons(summary):
    reasons = [];rate = summary['rate'];seconds = summary['measure_seconds'];offered = summary['offered']
    if abs(offered / (rate * seconds) - 1) > .02: reasons.append('offered_rate_outside_2pct')
    if summary['accepted'] != offered or summary['stored_at_observation_end'] != offered: reasons.append('not_all_offered_accepted_stored')
    for key in ('dropped_iterations_all_phases', 'dlq_terminal', 'pending_retained', 'accepted_unreconciled', 'integrity_mismatches'):
        if summary[key] != 0: reasons.append(key)
    if summary['completed_per_second'] < rate * .95: reasons.append('completed_below_95pct')
    windows = summary['measurement_windows_10s']
    if len(windows) != math.ceil(seconds / 10) or any(w['unique_commits'] < rate * w['duration_seconds'] * .9 for w in windows): reasons.append('10s_window_below_90pct')
    ins = summary['instrumentation']
    for key in ('database_error_samples', 'kafka_error_samples', 'clock_error_samples'):
        if ins[key] != 0: reasons.append(key)
    if ins['pending_tail_slope_events_per_second'] > .01: reasons.append('queue_growing')
    if max(ins['max_accepted_not_committed'], ins.get('max_kafka_lag') or 0) > max(5, math.ceil(rate * .25)): reasons.append('backlog_above_reference_limit')
    if ins['sample_gaps_ms']['p95'] > 2500: reasons.append('observer_cadence')
    return reasons


def audit_case(row, policy, stage):
    root = folder(row);summary = read(root / 'summary.json');meta = manifest(root / 'manifest.txt')
    for key in ('run_id', 'dataset_id', 'variant', 'profile', 'rate', 'vus'):
        if str(row[key]) != meta[key] or (key in summary and str(row[key]) != str(summary[key])): raise ValueError(f'Identidade divergente: {key}')
    if not summary['instrument_valid'] or summary['issues'] or meta.get('analyzer_exit') != '0' or meta.get('k6_exit') != '0': raise ValueError(f'Coleta inválida: {row["run_id"]}:{summary["issues"]}')
    for key in ('instrument_source_sha256', 'analyzer_image_id', 'application_images_sha256'):
        if meta[key] != policy[key]: raise ValueError('Fingerprint divergente: ' + key)
    expected_kind = 'definitive' if stage == 'campaign' else 'calibration' if row['profile'] == 'steady' else 'validation'
    if meta['kind'] != expected_kind or meta['working_tree'] != 'clean': raise ValueError('Classificação/checkout inválido')
    issues = []
    if row['profile'] != 'model':
        for key in ('warmup_seconds', 'measure_seconds', 'drain_seconds'):
            if int(meta[key]) != policy[key]: issues.append('parameter:' + key)
        issues += headroom(summary, policy)
    if stage == 'pilot':
        if row['profile'] == 'steady': issues += steady_reasons(summary)
        if 'stop' in row['profile'] and not summary['recovery']['stable_throughput_recovery'].get('observed'): issues.append('stable_recovery_not_observed_in_180s')
        if row['profile'] != 'model' and summary['accepted_unreconciled']: issues.append('unreconciled_acceptance')
        if row['profile'] == 'consumer-stop' and (summary['stored_at_observation_end'] != summary['accepted'] or summary['dlq_terminal'] or summary['pending_retained']): issues.append('consumer_backlog_not_persisted')
    if issues: raise ValueError(f'{row["run_id"]}: ' + ', '.join(issues))
    return dict(run_id=row['run_id'], variant=row['variant'], profile=row['profile'], block=row['block'], rate=row['rate'], raw_path=str(root.relative_to(APP)), summary_sha256=sha((root / 'summary.json').read_bytes()), raw_files_verified=verify_raw(root), started_utc=meta['started_utc'], collection_end_utc=meta['collection_end_utc'])


def experimental_stop():
    env = {**os.environ, 'EXPERIMENT_TOPIC': 'unused'}
    command(['docker', 'compose', '-p', 'tcc-entrega04', '-f', 'docker-compose.yml', '-f', 'experimento/compose.yml', '--profile', 'observation', 'stop', '-t', '5'], env=env, stdout=subprocess.DEVNULL)


def terminate_child():
    global CHILD
    if CHILD is not None and CHILD.poll() is None:
        os.killpg(CHILD.pid, signal.SIGTERM)
        try: CHILD.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(CHILD.pid, signal.SIGKILL);CHILD.wait()
    CHILD = None


def checked_amendment():
    import qualified_analysis as qualified
    frozen = read(APP / 'experimento/FROZEN-PROTOCOL.json')
    qualified.verify_extension(frozen)
    if sha(Path(__file__).read_bytes()) != frozen['controller_sha256']:
        raise ValueError('Controlador diverge da emenda congelada')
    return frozen


def published_checkout():
    clean()
    if output(['git', 'rev-parse', 'HEAD']) != output(['git', 'rev-parse', 'refs/remotes/origin/main']):
        raise ValueError('Publicar e confirmar origin/main antes da retomada A1')


def record_assessment(state, assessment):
    import qualified_analysis as qualified
    partial = assessment['classification'] == 'partial_commit_timing'
    key = 'campaign_qualified' if partial else 'campaign_completed'
    opposite = 'campaign_completed' if partial else 'campaign_qualified'
    if assessment['run_id'] in state.get(opposite, []):
        raise ValueError('UUID não pode ser simultaneamente completo e parcial')
    qualified.save_assessment(assessment)
    state.setdefault(key, [])
    if assessment['run_id'] not in state[key]: state[key].append(assessment['run_id'])
    state['campaign_accounted'] = len(set(state['campaign_completed']) | set(state.get('campaign_qualified', [])))
    state['updated_utc'] = now()


def execute(stage, reviewed=False):
    import fcntl
    global CHILD
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read(STATE);policy = read(POLICY)
        if state['policy_sha256'] != sha(POLICY.read_bytes()): raise ValueError('Política mudou após preparar piloto')
        clean();fingerprints(policy)
        active = output(['docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=tcc-entrega04'])
        if active: raise ValueError('Projeto experimental já ativo; não interromper outra execução')
        if stage == 'pilot': rows = read(REPORT / 'pilot-plan.json')
        else:
            policy = read(APP / 'experimento/FROZEN-PROTOCOL.json')
            if policy.get('schema_version') != 2 or policy['status'] != 'ready_for_definitive_runs': raise ValueError('V2 ainda não congelada')
            if sha(Path(__file__).read_bytes()) != policy['controller_sha256']: raise ValueError('Controlador mudou após congelamento')
            if sha((REPORT / 'plan.csv').read_bytes()) != policy['plan_sha256']: raise ValueError('Plano alterado')
            rows = plan_rows(REPORT / 'plan.csv');validate_plan(rows)
            if policy.get('analytical_amendment') and not reviewed:
                raise ValueError('A1 exige o caminho explícito campaign-reviewed; não reiniciar campaign')
        approved_partial = None
        if reviewed:
            import qualified_analysis as qualified
            published_checkout()
            policy = checked_amendment()
            approved_partial = qualified.resume_preflight(state, rows, policy)
            snapshot = RUNTIME / 'state-before-a1.json'
            if snapshot.exists(): raise ValueError('Retomada A1 já iniciada; não repetir sem nova auditoria')
            # Preserve the prior journal byte for byte; only this locked controller advances it.
            with snapshot.open('xb') as stream: stream.write(STATE.read_bytes())
            state['analytical_amendment'] = policy['analytical_amendment']['revision']
            state['campaign_qualified'] = []
            state['published_resume_commit'] = output(['git', 'rev-parse', 'HEAD'])
            state['original_interruption'] = state.get('error')
            state.pop('error', None)
            adoption = read(APP / policy['analytical_amendment']['files']['adoption_audit']['path'])
            for assessment in adoption['assessments']: qualified.save_assessment(assessment)
        completed_key = stage + '_completed'
        primary = output(['docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=tcc-java-2026']).split()
        state.update(phase=stage + '_running', controller_pid=os.getpid(), updated_utc=now(), primary_previously_running=primary)
        write(STATE, state)
        if primary: command(['docker', 'stop', '-t', '10', *primary], stdout=subprocess.DEVNULL)
        owned = True
        try:
            for index, row in enumerate(rows, 1):
                if row['run_id'] in state[completed_key]:
                    audit_case(row, policy, stage);continue
                if reviewed and row['run_id'] in state.get('campaign_qualified', []):
                    record_assessment(state, qualified.assess(row, policy));continue
                root = folder(row)
                if root.exists():
                    if reviewed and row['run_id'] == approved_partial['run_id']:
                        assessment = qualified.assess(row, policy)
                        if assessment != approved_partial: raise ValueError('Parecer parcial mudou após preflight')
                        record_assessment(state, assessment);write(STATE, state)
                        print(f'{now()} A1 preserved partial collection {row["run_id"]}; no load repeated', flush=True)
                        continue
                    raise ValueError('Pasta existente não concluída no diário; não sobrescrever/reexecutar: ' + str(root))
                clean();fingerprints(policy)
                state.update(current=row, current_index=index, total=len(rows), updated_utc=now());write(STATE, state)
                print(f'{now()} {stage} {index}/{len(rows)} {row["profile"]} {row["variant"]} {row["rate"]}/s {row["run_id"]}', flush=True)
                model = row['profile'] == 'model'
                env = {**os.environ, 'KIND': 'definitive' if stage == 'campaign' else 'calibration' if row['profile'] == 'steady' else 'validation', 'PROFILE': row['profile'], 'RATE': str(row['rate']), 'RUN_ID': row['run_id'], 'DATASET_ID': row['dataset_id'], 'VUS': str(row['vus']), 'WARMUP_SECONDS': str(1 if model else policy['warmup_seconds']), 'MEASURE_SECONDS': str(6 if model else policy['measure_seconds']), 'DRAIN_SECONDS': str(5 if model else policy['drain_seconds']), 'FAULT_SECONDS': str(policy['fault_seconds']), 'OBSERVE': '1', 'STATS': '1', 'TELEMETRY': 'full'}
                with (RUNTIME / f'{row["run_id"]}-console.txt').open('x') as log:
                    CHILD = subprocess.Popen(['bash', 'experimento/run.sh', row['variant']], cwd=APP, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    state['runner_pid'] = CHILD.pid;write(STATE, state)
                    code = CHILD.wait(timeout=900);CHILD = None
                state.pop('runner_pid', None)
                if reviewed:
                    if code not in (0, 2): raise ValueError(f'Executor retornou {code}; preservar {root}')
                    assessment = qualified.assess(row, policy)
                    if code != assessment['original_analyzer_exit']: raise ValueError('Saída do executor/analisador divergente')
                    if assessment['classification'] == 'complete_original_evidence': audit_case(row, policy, stage)
                    record_assessment(state, assessment)
                    print(f'{now()} A1 {row["run_id"]} {assessment["classification"]}', flush=True)
                else:
                    if code: raise ValueError(f'Executor retornou {code}; preservar {root}')
                    audit_case(row, policy, stage)
                    state[completed_key].append(row['run_id']);state['updated_utc'] = now()
                write(STATE, state)
            if stage == 'pilot':
                models = [r for r in rows if r['profile'] == 'model'];sync = next(r for r in models if r['variant'] == 'sync');async_row = next(r for r in models if r['variant'] == 'async')
                command(['docker', 'run', '--rm', '--network', 'none', '--user', f'{os.getuid()}:{os.getgid()}', '--mount', f'type=bind,src={APP / ".runtime"},dst=/evidence', policy['analyzer_image_id'], 'model', f'/evidence/entrega04/{sync["run_id"]}-sync/database.jsonl', f'/evidence/entrega04/{async_row["run_id"]}-async/database.jsonl', f'/evidence/{RUNTIME.name}/model-comparison.json'])
            state.update(phase=stage + '_complete', finished_utc=now(), updated_utc=now());state.pop('current', None)
        except BaseException as error:
            state.update(phase='attention_required', interrupted_stage=stage, error=str(error), updated_utc=now());raise
        finally:
            errors = []
            try:
                terminate_child()
                if owned:
                    # The generator has no Compose project label; stop only this run's exact name.
                    current = state.get('current', {})
                    if current.get('run_id'):
                        name = 'tcc-e04-load-' + current['run_id']
                        subprocess.run(['docker', 'stop', '-t', '3', name], cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    experimental_stop()
            except Exception as error: errors.append(str(error))
            try:
                for container in primary:
                    label = output(['docker', 'inspect', '-f', '{{index .Config.Labels "com.docker.compose.project"}}', container])
                    if label != 'tcc-java-2026': raise ValueError('Retomada recusada: contêiner não pertence ao projeto principal')
                if primary: command(['docker', 'start', *primary], stdout=subprocess.DEVNULL)
            except Exception as error: errors.append(str(error))
            if errors: state.update(phase='attention_required', cleanup_errors=errors)
            state.pop('runner_pid', None);state.pop('controller_pid', None);write(STATE, state)


def freeze():
    state = read(STATE);policy = read(POLICY)
    if state['phase'] != 'pilot_complete': raise ValueError('Piloto ainda não aprovado')
    clean();fingerprints(policy)
    active = read(APP / 'experimento/FROZEN-PROTOCOL.json')
    if active.get('status') != 'pilot_pending' or active.get('protocol_revision') != policy['protocol_revision']: raise ValueError('Revisão pendente ativa divergente')
    if sha((APP / policy['previous_protocol']).read_bytes()) != policy['previous_protocol_sha256']: raise ValueError('V1 preservada foi alterada')
    pilots = read(REPORT / 'pilot-plan.json');records = [audit_case(r, policy, 'pilot') for r in pilots]
    model = read(RUNTIME / 'model-comparison.json')
    if model.get('same_ids_fields_payload_hash') is not True: raise ValueError('Modelo comum divergente')
    if (REPORT / 'pilot-catalog.json').exists(): raise ValueError('Congelamento já publicado; não sobrescrever')
    for row in pilots:
        target = REPORT / 'pilot-runs' / f'{row["run_id"]}-{row["variant"]}.json';target.parent.mkdir(exist_ok=True)
        shutil.copyfile(folder(row) / 'summary.json', target)
    write(REPORT / 'model-comparison.json', model)
    write(REPORT / 'pilot-catalog.json', dict(kind='reduced_protocol_validation_not_definitive', ready=True, generated_utc=now(), records=records, model=model))
    frozen = {**policy, 'status': 'ready_for_definitive_runs', 'plan_sha256': sha((REPORT / 'plan.csv').read_bytes()), 'reduced_policy_sha256': sha(POLICY.read_bytes()), 'pilot_catalog_sha256': sha((REPORT / 'pilot-catalog.json').read_bytes()), 'controller_sha256': sha(Path(__file__).read_bytes()), 'pilot_validation_run_ids': [r['run_id'] for r in pilots]}
    write(APP / 'experimento/FROZEN-PROTOCOL.json', frozen)
    print('V2 congelada após validar 9 coletas. Revisar/commitar antes de iniciar campaign.')


def launch(stage, reviewed=False):
    state = read(STATE)
    if state.get('controller_pid'):
        try:
            os.kill(state['controller_pid'], 0)
            raise ValueError('Controlador já ativo; não iniciar cópia')
        except ProcessLookupError: pass
    expected = 'attention_required' if reviewed else 'prepared' if stage == 'pilot' else 'pilot_complete'
    if state['phase'] != expected: raise ValueError('Estado não permite iniciar: ' + state['phase'])
    if reviewed:
        import qualified_analysis as qualified
        published_checkout()
        frozen = checked_amendment()
        rows = plan_rows(REPORT / 'plan.csv');validate_plan(rows)
        qualified.initial_shape(state, rows, read(qualified.POLICY))
    log = (RUNTIME / f'{stage}-controller.log').open('ab', buffering=0)
    action = 'campaign-reviewed' if reviewed else stage
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), action], cwd=APP, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    print(json.dumps({'pid': child.pid, 'stage': stage, 'log': str(RUNTIME / f'{stage}-controller.log')}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('action', choices=['prepare', 'pilot', 'campaign', 'freeze', 'status', 'launch-pilot', 'launch-campaign', 'audit-amendment', 'campaign-reviewed', 'launch-reviewed-campaign'])
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    try:
        if args.action == 'prepare': prepare()
        elif args.action in ('pilot', 'campaign'): execute(args.action)
        elif args.action == 'freeze': freeze()
        elif args.action == 'status': print(json.dumps(read(STATE) if STATE.exists() else {'phase': 'not_prepared'}, ensure_ascii=False, indent=2))
        elif args.action == 'audit-amendment':
            import qualified_analysis as qualified
            frozen = checked_amendment()
            qualified.resume_preflight(read(STATE), plan_rows(REPORT / 'plan.csv'), frozen)
            print('A1: 36 completas, 1 parcial preservada, 28 UUIDs não iniciados; sem carga ou alteração do diário.')
        elif args.action == 'campaign-reviewed': execute('campaign', reviewed=True)
        elif args.action == 'launch-reviewed-campaign': launch('campaign', reviewed=True)
        else: launch(args.action.split('-', 1)[1])
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Parado para revisão, sem sobrescrever evidências: {error}\n')


if __name__ == '__main__': main()
