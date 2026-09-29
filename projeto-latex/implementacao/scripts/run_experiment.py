"""Collect isolated, reproducible functional runs; gate scientific collection explicitly.

Run in WSL/Linux from implementacao/. Docker Engine and Compose must already work.
Never exports environment values, deletes output, or resets another Compose project.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import hashlib
import json
import math
import os
import platform
import random
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from normalize import checksums, normalize, parse_lag, read_jsonl, seal_inputs
from protocol import phases_for, validate_protocol

PROJECT = 'tcc-revisao-20260907'
K6_IMAGE = 'grafana/k6:1.4.0'
BASE = Path(__file__).resolve().parent.parent
APP_SERVICES = ('sync-api', 'async-api', 'consumer')
ALL_SERVICES = ('postgres', 'kafka', *APP_SERVICES)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def execute(command, *, timeout=60, check=True):
    result = subprocess.run(command, cwd=BASE, text=True, encoding='utf-8', errors='replace',
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if check and result.returncode:
        # Do not include command stderr: configuration diagnostics may expose environment.
        raise RuntimeError(f'{command[0]} command failed (exit {result.returncode}); inspect the local runtime')
    return result


class Compose:
    def __init__(self, env_file):
        env_path = Path(env_file).resolve()
        if not env_path.is_file():
            raise ValueError(f'Private environment file does not exist: {env_path}')
        self.command = ['docker', 'compose', '--project-name', PROJECT, '--env-file', str(env_path),
                        '-f', str(BASE / 'docker-compose.yml')]

    def run(self, *args, timeout=60, check=True):
        return execute([*self.command, *args], timeout=timeout, check=check)

    def container_ids(self):
        return self.run('ps', '--all', '--quiet', *ALL_SERVICES).stdout.split()

    def inspect_safe(self):
        records = []
        for container_id in self.container_ids():
            # Only selected fields are serialized; never Config.Env.
            template = '{{json .Config.Labels}}\n{{.Image}}\n{{.Config.Image}}\n{{json .HostConfig.NanoCpus}}\n{{json .HostConfig.Memory}}\n{{.State.Status}}'
            lines = execute(['docker', 'inspect', '--format', template, container_id]).stdout.splitlines()
            labels = json.loads(lines[0])
            if labels.get('com.docker.compose.project') != PROJECT:
                raise ValueError('Container is not owned by the isolated TCC project')
            working = labels.get('com.docker.compose.project.working_dir')
            if working and Path(working).resolve() != BASE:
                raise ValueError('Compose project label points to another checkout')
            records.append({'id': container_id, 'service': labels.get('com.docker.compose.service'),
                            'image_id': lines[1], 'image': lines[2], 'nano_cpus': int(lines[3]),
                            'memory_limit_bytes': int(lines[4]), 'status': lines[5]})
        return records

    def stop_start(self, service, action):
        if service not in ALL_SERVICES or action not in ('stop', 'start'):
            raise ValueError('Invalid scoped fault operation')
        self.inspect_safe()
        return self.run(action, service, timeout=60)

    def reset_isolated_state(self):
        self.inspect_safe()
        # Resolve every volume's ownership before destructive reset of this dedicated experiment.
        volumes = execute(['docker', 'volume', 'ls', '--quiet', '--filter',
                           f'label=com.docker.compose.project={PROJECT}']).stdout.split()
        for volume in volumes:
            label = execute(['docker', 'volume', 'inspect', '--format',
                             '{{index .Labels "com.docker.compose.project"}}', volume]).stdout.strip()
            if label != PROJECT or not volume.startswith(PROJECT + '_'):
                raise ValueError('Volume ownership check failed; reset refused')
        self.run('down', '--volumes', '--remove-orphans', timeout=120)
        self.run('up', '-d', '--wait', '--wait-timeout', '180', timeout=240)




def prepare_run(output_root, config, *, protocol=None, pilot_evidence_path=None):
    run_id = str(uuid.uuid4())
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    config = dict(config, run_id=run_id, url=f"http://{'sync-api:8000' if config['variant'] == 'sync' else 'async-api:8001'}")
    if config.get('profile') == 'definitive':
        if protocol is None or pilot_evidence_path is None:
            raise ValueError('Definitive collection requires the frozen protocol and pilot report file')
        write_json(run_dir / 'protocol.json', protocol)
        shutil.copyfile(pilot_evidence_path, run_dir / 'pilot_evidence.snapshot')
        config['protocol_sha256'] = hashlib.sha256((run_dir / 'protocol.json').read_bytes()).hexdigest()
        config['pilot_evidence_sha256'] = hashlib.sha256((run_dir / 'pilot_evidence.snapshot').read_bytes()).hexdigest()
    config['phases'] = phases_for(config)
    count = sum(phase['rate'] * phase['seconds'] for phase in config['phases'])
    namespace = uuid.UUID(run_id)
    instant = utc_now()
    payloads = [{'event_id': str(uuid.uuid5(namespace, str(index))), 'event_type': 'config.updated',
                 'entity_type': 'synthetic_record', 'entity_id': f'entity-{index % 100:03d}',
                 'actor_id': 'synthetic-actor', 'source': 'tcc-load-generator', 'occurred_at': instant,
                 'payload': {'run_id': run_id, 'sequence': index, 'padding': 'x' * config['payload_padding_bytes']}}
                for index in range(count)]
    write_json(run_dir / 'config.json', config)
    write_json(run_dir / 'payloads.json', payloads)
    return run_dir, config


def source_hashes():
    paths = [BASE / 'docker-compose.yml', BASE / 'Dockerfile', BASE / 'requirements.txt']
    paths += list((BASE / 'app').rglob('*.py'))
    paths += list((BASE / 'scripts').rglob('*.py')) + list((BASE / 'scripts').glob('*.js'))
    paths += list((BASE / 'tests').rglob('*.py'))
    return {path.relative_to(BASE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths) if path.exists()}


def environment_manifest(compose):
    containers = compose.inspect_safe()
    if not containers or not set(ALL_SERVICES).issubset({r['service'] for r in containers}):
        raise RuntimeError('Start all five application services in the isolated Compose project first')
    if any(c['status'] != 'running' for c in containers):
        raise RuntimeError('All isolated services must be running before collection')
    effective_parameters = {}
    allowed = ['DELIVERY_TIMEOUT_SECONDS', 'DB_TIMEOUT_SECONDS', 'RETRY_ATTEMPTS', 'RETRY_BACKOFF_SECONDS',
               'RETRY_BACKOFF_MAX_SECONDS', 'RECONNECT_SECONDS', 'KAFKA_TOPIC', 'KAFKA_DLQ_TOPIC']
    for service in APP_SERVICES:
        code = 'import os,json; print(json.dumps({k:os.environ.get(k) for k in ' + repr(allowed) + '}))'
        effective_parameters[service] = json.loads(compose.run('exec', '-T', service, 'python', '-c', code).stdout)
    clock_code = ('import os,time,json; from pathlib import Path; '
                  'print(json.dumps({"wall_time_ns":time.time_ns(),"clock_resolution_seconds":time.get_clock_info("time").resolution,'
                  '"kernel_release":os.uname().release,"time_namespace":os.readlink("/proc/self/ns/time"),'
                  '"time_namespace_offsets":Path("/proc/self/timens_offsets").read_text()}))')
    clock_evidence = {'collector': json.loads(execute(['python3', '-c', clock_code]).stdout)}
    for service in APP_SERVICES:
        clock_evidence[service] = json.loads(compose.run('exec', '-T', service, 'python', '-c', clock_code).stdout)
    image_records = []
    for image in sorted({r['image'] for r in containers} | {K6_IMAGE}):
        result = execute(['docker', 'image', 'inspect', '--format', '{{.Id}}\n{{json .RepoDigests}}', image], check=False)
        lines = result.stdout.splitlines()
        image_records.append({'reference': image, 'image_id': lines[0] if lines else None,
                              'repo_digests': json.loads(lines[1]) if len(lines) > 1 else []})
    cpu_model = None
    cpu_file = Path('/proc/cpuinfo')
    if cpu_file.exists():
        cpu_model = next((line.split(':', 1)[1].strip() for line in cpu_file.read_text().splitlines()
                          if line.startswith('model name')), None)
    docker_info = execute(['docker', 'info', '--format',
                           '{{.ServerVersion}}|{{.OSType}}|{{.Architecture}}|{{.NCPU}}|{{.MemTotal}}']).stdout.strip().split('|')
    return {'os': platform.platform(), 'python': platform.python_version(), 'cpu_count': os.cpu_count(),
            'cpu_model': cpu_model, 'docker_server': docker_info,
            'compose_version': compose.run('version', '--short').stdout.strip(),
            'containers': containers, 'images': image_records, 'sources_sha256': source_hashes(),
            'clock_notes': 'Same Docker/WSL host; client Date.now millisecond wall clock and post-commit Python time_ns. No cross-process monotonic subtraction.',
            'effective_nonsecret_application_parameters': effective_parameters,
            'clock_environment_observations': clock_evidence,
            'runtime_secret_values_included': False}


def sample_runtime(compose, run_dir, stop_event, interval):
    ids = compose.container_ids()
    config = json.loads((run_dir / 'config.json').read_text())
    lag_method = config.get('lag_method', 'cli')
    lag_context = (run_dir / 'lag.jsonl').open('w', encoding='utf-8') if lag_method == 'cli' else nullcontext(None)
    with (run_dir / 'resources.jsonl').open('w', encoding='utf-8') as resource_stream, \
         lag_context as lag_stream:
        while not stop_event.is_set():
            started = time.monotonic()
            timestamp = time.time_ns()
            try:
                extra = []
                for prefix in ('tcc-lag-', 'tcc-k6-'):
                    extra.extend(execute(['docker', 'ps', '--quiet', '--filter',
                        'name=^/' + prefix + config['run_id'] + '$'], timeout=10, check=False).stdout.split())
                result = execute(['docker', 'stats', '--no-stream', '--format', '{{json .}}', *ids, *extra], timeout=20, check=False)
                containers = []
                for line in result.stdout.splitlines():
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
                resource_stream.write(json.dumps({'wall_time_ns': timestamp, 'sample_finished_ns': time.time_ns(), 'containers': containers,
                                                   'exit_code': result.returncode}) + '\n')
                resource_stream.flush()
            except subprocess.TimeoutExpired:
                resource_stream.write(json.dumps({'wall_time_ns': timestamp, 'sampling_error': 'timeout'}) + '\n')
            if lag_method != 'cli':
                stop_event.wait(max(0, interval - (time.monotonic() - started)))
                continue
            try:
                result = compose.run('exec', '-T', 'kafka', '/opt/kafka/bin/kafka-consumer-groups.sh',
                                     '--bootstrap-server', 'localhost:9092', '--group', 'audit-persistence',
                                     '--describe', timeout=20, check=False)
                lag_stream.write(json.dumps({'wall_time_ns': time.time_ns(), 'sample_started_ns': timestamp,
                                              'partitions': parse_lag(result.stdout), 'exit_code': result.returncode}) + '\n')
                lag_stream.flush()
            except subprocess.TimeoutExpired:
                lag_stream.write(json.dumps({'wall_time_ns': time.time_ns(), 'sampling_error': 'timeout'}) + '\n')
            stop_event.wait(max(0, interval - (time.monotonic() - started)))


def export_database(compose, run_id, run_dir):
    # run_id was locally created as UUID, never interpolated from untrusted input.
    validated = str(uuid.UUID(run_id))
    sql = ("COPY (SELECT event_id, content_hash, persisted_at, payload->>'run_id' AS run_id "
           f"FROM audit_records WHERE payload->>'run_id' = '{validated}' ORDER BY event_id) TO STDOUT WITH CSV HEADER")
    result = compose.run('exec', '-T', 'postgres', 'psql', '-U', 'audit', '-d', 'auditdb', '-c', sql,
                         timeout=30, check=False)
    if result.returncode == 0:
        (run_dir / 'database.csv').write_text(result.stdout, encoding='utf-8')
    return result.returncode


def fault_control(compose, run_dir, fault, stop_event, manifest):
    if not fault:
        return
    service = fault['service']
    stopped = False
    try:
        # Anchor interruption to actual generator measurement, excluding Docker startup.
        while not stop_event.wait(.1):
            sent = [r for r in read_jsonl(run_dir / 'generator.jsonl')
                    if r.get('kind') == 'request_sent' and r.get('phase') == 'measurement']
            if sent:
                phase_offsets = {p['name']: p['start_seconds'] for p in json.loads((run_dir / 'config.json').read_text())['phases']}
                cfg = json.loads((run_dir / 'config.json').read_text())
                start_ms = min(r['phase_start_ms'] - phase_offsets[r['segment']] * 1000 for r in sent) + cfg['warmup_seconds'] * 1000
                remaining = start_ms / 1000 + fault['at_seconds'] - time.time()
                if remaining > 0 and stop_event.wait(remaining):
                    return
                manifest['fault_events'].append({'action': 'stop_requested', 'service': service, 'wall_time_ns': time.time_ns()})
                compose.stop_start(service, 'stop')
                stopped = True
                manifest['fault_events'].append({'action': 'stopped', 'service': service, 'wall_time_ns': time.time_ns()})
                stop_event.wait(fault['seconds'])
                manifest['fault_events'].append({'action': 'start_requested', 'service': service, 'wall_time_ns': time.time_ns()})
                compose.stop_start(service, 'start')
                stopped = False
                manifest['fault_events'].append({'action': 'started', 'service': service, 'wall_time_ns': time.time_ns()})
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    if service == 'postgres':
                        ready = compose.run('exec', '-T', 'postgres', 'psql', '-U', 'audit', '-d', 'auditdb',
                                            '-tAc', 'SELECT 1', timeout=10, check=False).returncode == 0
                    else:
                        ready = compose.run('ps', '--status', 'running', '--quiet', service, check=False).stdout.strip() != ''
                    if ready:
                        manifest['fault_events'].append({'action': 'ready', 'service': service, 'wall_time_ns': time.time_ns(),
                                                        'probe': 'SELECT 1' if service == 'postgres' else 'container_running_only'})
                        break
                    if stop_event.wait(.5):
                        break
                else:
                    manifest['fault_errors'].append('readiness_timeout')
                return
    except Exception as error:
        manifest['fault_errors'].append(type(error).__name__)
    finally:
        if stopped:
            try:
                compose.stop_start(service, 'start')
                manifest['fault_events'].append({'action': 'started', 'service': service,
                                                'wall_time_ns': time.time_ns(), 'reason': 'cleanup'})
            except Exception as error:
                manifest['fault_errors'].append('cleanup:' + type(error).__name__)


def collect(compose, output_root, config, *, protocol=None, pilot_evidence_path=None):
    run_dir, config = prepare_run(output_root, config, protocol=protocol, pilot_evidence_path=pilot_evidence_path)
    manifest = {'run_id': config['run_id'], 'profile': config['profile'], 'started_utc': utc_now(),
                'fault_events': [], 'fault_errors': [], 'errors': [], 'load_exit_code': None}
    write_json(run_dir / 'manifest.json', manifest)
    sampler_stop, fault_stop = threading.Event(), threading.Event()
    sampler = fault_thread = load = observer = None
    observer_stream = None
    observer_name = 'tcc-lag-' + config['run_id']
    load_name = 'tcc-k6-' + config['run_id']
    try:
        manifest['environment'] = environment_manifest(compose)
        for relative in manifest['environment']['sources_sha256']:
            destination = run_dir / 'source_snapshot' / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(BASE / relative, destination)
        write_json(run_dir / 'manifest.json', manifest)
        if config.get('lag_method') == 'observer':
            observer_image = next(c['image_id'] for c in manifest['environment']['containers'] if c['service'] == 'consumer')
            observer_command = ['docker', 'run', '--rm', '--name', observer_name,
                '--network', PROJECT + '_default', '--cpus', '0.25', '--memory', '128m',
                '--user', f'{os.getuid()}:{os.getgid()}',
                '--mount', f'type=bind,source={BASE / "scripts"},target=/scripts,readonly',
                observer_image, 'python', '-u', '/scripts/kafka_lag_probe.py',
                '--bootstrap', 'kafka:9092', '--group', 'audit-persistence', '--topic', 'audit-events',
                '--interval', str(config['sample_interval_seconds']), '--timeout', '5', '--run-id', config['run_id']]
            manifest['lag_observer'] = {'image_id': observer_image, 'cpus': .25, 'memory': '128m',
                                        'method': 'persistent_read_only_client', 'timeout_seconds': 5}
            observer_stream = (run_dir / 'lag.jsonl').open('w', encoding='utf-8')
            observer = subprocess.Popen(observer_command, cwd=BASE, stdout=observer_stream,
                                        stderr=subprocess.DEVNULL, text=True)
        sampler = threading.Thread(target=sample_runtime, args=(compose, run_dir, sampler_stop, config['sample_interval_seconds']), daemon=True)
        fault_thread = threading.Thread(target=fault_control, args=(compose, run_dir, config.get('fault'), fault_stop, manifest), daemon=True)
        command = ['docker', 'run', '--rm', '--name', load_name,
                   '--network', PROJECT + '_default', '--cpus', str(config['generator_cpus']),
                   '--memory', config['generator_memory'],
                   '--user', f'{os.getuid()}:{os.getgid()}',
                   '--mount', f'type=bind,source={run_dir},target=/input,readonly',
                   '--mount', f'type=bind,source={run_dir},target=/output',
                   '--mount', f'type=bind,source={BASE / "scripts"},target=/scripts,readonly',
                   K6_IMAGE, 'run', '--quiet', '--log-format', 'raw',
                   '--console-output', '/output/generator.jsonl', '--out', 'json=/output/k6-points.jsonl',
                   '/scripts/load.js']
        manifest['generator_command'] = command
        sampler.start()
        with (run_dir / 'generator-process.log').open('w', encoding='utf-8') as stream:
            load = subprocess.Popen(command, cwd=BASE, stdout=stream, stderr=stream, text=True)
            fault_thread.start()
            print(json.dumps({'run_id': config['run_id'], 'profile': config['profile'], 'variant': config['variant'],
                              'state': 'collecting', 'directory': str(run_dir)}), flush=True)
            deadline = config['warmup_seconds'] + config['measurement_seconds'] + config['http_timeout_seconds'] + 120
            manifest['load_exit_code'] = load.wait(timeout=deadline)
        # Keep collecting through a bounded observation/drain window, even after HTTP completes.
        fault_thread.join(timeout=config.get('fault', {}).get('seconds', 0) + 65 if config.get('fault') else 1)
        time.sleep(config['drain_seconds'])
        manifest['database_export_exit_code'] = export_database(compose, config['run_id'], run_dir)
        result = compose.run('logs', '--no-color', '--no-log-prefix', '--since', manifest['started_utc'],
                             *APP_SERVICES, timeout=30, check=False)
        # Keep structured app milestones only; library stderr/connection diagnostics are not evidence logs.
        sanitized = []
        for line in result.stdout.splitlines():
            if line.lstrip().startswith('{'):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get('run_id') == config['run_id'] and record.get('milestone'):
                    sanitized.append(record)
        with (run_dir / 'application.jsonl').open('w', encoding='utf-8') as stream:
            for record in sanitized:
                stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        manifest['application_log_export_exit_code'] = result.returncode
    except (Exception, KeyboardInterrupt) as error:
        manifest['errors'].append(type(error).__name__)
        if load and load.poll() is None:
            execute(['docker', 'stop', load_name], timeout=30, check=False)
            load.wait(timeout=15)
    finally:
        fault_stop.set()
        if fault_thread and fault_thread.is_alive():
            fault_thread.join(timeout=65)
        sampler_stop.set()
        if sampler and sampler.is_alive():
            sampler.join(timeout=45)
        if observer:
            execute(['docker', 'stop', '--time', '10', observer_name], timeout=20, check=False)
            manifest['lag_observer_exit_code'] = observer.wait(timeout=15)
            observer_stream.close()
        manifest['finished_utc'] = utc_now()
        manifest['observation_end_ns'] = time.time_ns()
        write_json(run_dir / 'manifest.json', manifest)
        try:
            seal_inputs(run_dir)
            summary = normalize(run_dir)
        except Exception as error:
            manifest['errors'].append('normalization:' + type(error).__name__)
            write_json(run_dir / 'manifest.json', manifest)
            summary = None
        checksums(run_dir)
    state = 'collected' if summary and not summary['instrumentation_issues'] else 'incomplete'
    print(json.dumps({'run_id': config['run_id'], 'state': state,
                      'errors': manifest['errors'], 'load_exit_code': manifest['load_exit_code'],
                      'directory': str(run_dir)}), flush=True)
    return run_dir, manifest, summary




def base_config(args):
    return {'profile': args.profile, 'scenario': args.stage if args.profile == 'pilot' else 'functional', 'rate': args.rate,
            'warmup_seconds': args.warmup, 'measurement_seconds': args.duration,
            'drain_seconds': args.drain, 'sample_interval_seconds': args.sample_interval,
            'preallocated_vus': args.vus, 'max_vus': args.max_vus,
            'http_timeout_seconds': args.http_timeout, 'payload_padding_bytes': args.payload_padding,
            'generator_cpus': 1, 'generator_memory': '512m', 'lag_method': args.lag_method}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', choices=['validation', 'pilot', 'definitive', 'check-protocol'])
    parser.add_argument('--stage', default='calibration')
    parser.add_argument('--lag-method', choices=['cli', 'observer', 'none'], default='observer')
    parser.add_argument('--burst-rate', type=int)
    parser.add_argument('--burst-at', type=int)
    parser.add_argument('--burst-seconds', type=int)
    parser.add_argument('--env-file', type=Path, default=BASE / '.runtime' / 'compose.env')
    parser.add_argument('--output', type=Path, default=BASE / 'evidence' / 'runs')
    parser.add_argument('--variant', choices=['sync', 'async', 'both'], default='both')
    parser.add_argument('--duration', type=int, default=10)
    parser.add_argument('--warmup', type=int, default=0)
    parser.add_argument('--rate', type=int, default=5)
    parser.add_argument('--drain', type=int, default=10)
    parser.add_argument('--sample-interval', type=float, default=2)
    parser.add_argument('--vus', type=int, default=10)
    parser.add_argument('--max-vus', type=int, default=50)
    parser.add_argument('--http-timeout', type=int, default=20)
    parser.add_argument('--payload-padding', type=int, default=128)
    parser.add_argument('--fault-service', choices=ALL_SERVICES)
    parser.add_argument('--fault-at', type=int, default=3)
    parser.add_argument('--fault-seconds', type=int, default=3)
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--reset-isolated-state', action='store_true')
    args = parser.parse_args()
    if any(value <= 0 for value in (args.duration, args.rate, args.drain, args.sample_interval,
                                    args.vus, args.max_vus, args.http_timeout)) or args.warmup < 0:
        parser.error('durations/rate/VUs must be positive; warmup must be nonnegative')
    if args.max_vus < args.vus:
        parser.error('max VUs cannot be smaller than preallocated VUs')
    if args.profile in ('definitive', 'check-protocol'):
        if not args.protocol:
            parser.error('--protocol is required; no scientific default is inferred')
        protocol = json.loads(args.protocol.read_text(encoding='utf-8'))
        validate_protocol(protocol)
        if args.profile == 'check-protocol':
            print('Protocol fields validated. This is not evidence that pilot or collection ran.')
            return 0
        if not args.reset_isolated_state:
            parser.error('independent repetitions require --reset-isolated-state for the dedicated project only')
    if os.name == 'nt':
        parser.error('Run under WSL/Linux connected to Docker Engine')
    compose = Compose(args.env_file)
    # Image pull precedes measurement. Its digest is then frozen in the run manifest.
    execute(['docker', 'pull', K6_IMAGE], timeout=300)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    common = base_config(args)
    runs = []
    if args.profile in ('validation', 'pilot'):
        if args.fault_service and (args.fault_at < 0 or args.fault_seconds <= 0 or args.fault_at + args.fault_seconds >= args.duration):
            parser.error('functional fault must fit within the measurement duration')
        for variant in (('sync', 'async') if args.variant == 'both' else (args.variant,)):
            config = dict(common, variant=variant)
            if any(v is not None for v in (args.burst_rate, args.burst_at, args.burst_seconds)):
                if (not all(isinstance(v, int) and v > 0 for v in (args.burst_rate, args.burst_at, args.burst_seconds))
                        or args.burst_at + args.burst_seconds >= args.duration):
                    parser.error('burst must have positive explicit parameters inside measurement duration')
                config['burst'] = {'rate': args.burst_rate, 'at_seconds': args.burst_at, 'seconds': args.burst_seconds}
            if args.fault_service:
                config['fault'] = {'service': args.fault_service, 'at_seconds': args.fault_at, 'seconds': args.fault_seconds}
            runs.append(collect(compose, output, config))
    else:
        common.update(protocol['generator'])
        schedule = []
        rng = random.Random(protocol['random_seed'])
        for repetition in range(protocol['repetitions']):
            for case in protocol['cases']:
                variants = ['sync', 'async']
                rng.shuffle(variants)
                for variant in variants:
                    schedule.append((repetition, case, variant))
        batch_dir = output / ('batch-' + str(uuid.uuid4()))
        batch_dir.mkdir(exist_ok=False)
        write_json(batch_dir / 'protocol.json', protocol)
        write_json(batch_dir / 'schedule.json', schedule)
        for repetition, case, variant in schedule:
            compose.reset_isolated_state()
            config = dict(common, profile='definitive', variant=variant, scenario=case['scenario'],
                          rate=case['rate'], warmup_seconds=60, measurement_seconds=300,
                          drain_seconds=protocol['drain_seconds'], sample_interval_seconds=protocol['sample_interval_seconds'],
                          repetition=repetition, repetitions=protocol['repetitions'], random_seed=protocol['random_seed'],
                          common_reference_rate=protocol['common_reference_rate'],
                          recovery_stable_seconds=protocol['recovery_stable_seconds'],
                          offered_rate_tolerance_fraction=protocol['offered_rate_tolerance_fraction'])
            if case.get('burst'):
                config['burst'] = case['burst']
            if case.get('level_fraction') is not None:
                config['level_fraction'] = case['level_fraction']
            if case.get('fault_by_variant'):
                config['fault'] = case['fault_by_variant'][variant]
            record = collect(compose, batch_dir, config, protocol=protocol,
                             pilot_evidence_path=Path(protocol['pilot_evidence_path']))
            runs.append(record)
            if (record[1]['errors'] or record[1]['load_exit_code'] != 0
                    or not record[2] or not record[2]['eligible_definitive_observation']):
                break
        checksums(batch_dir)
    return 1 if any(manifest['errors'] or manifest['load_exit_code'] != 0 or not summary
                    or summary['instrumentation_issues']
                    or (manifest['profile'] == 'definitive' and not summary['eligible_definitive_observation'])
                    for _, manifest, summary in runs) else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f'Collection stopped: {error}', file=sys.stderr)
        raise SystemExit(2)
