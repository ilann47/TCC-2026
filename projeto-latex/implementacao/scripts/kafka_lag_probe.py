"""Read-only Kafka lag observer; run once per collection in a separate container.

Reuses native clients instead of starting a Kafka JVM for every sample. No subscribe,
poll, assignment, offset storage or commit is performed. The Consumer has a separate
group identifier and is used only for uncached watermark queries. Committed offsets
of the application group are read through AdminClient.list_consumer_group_offsets.

Offsets are sampled sequentially, not atomically. Lag is an offset distance, not a
count of unique application events or proof of SQL persistence. Unknown offsets are
null, never zero. Sample duration/CPU quantify observer cost, not its causal effect
on application performance; that still requires a controlled overhead comparison.

Primary API/source references (confluent-kafka is pinned to 2.11.0 by the project):
https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html
https://github.com/confluentinc/confluent-kafka-python/blob/v2.11.0/src/confluent_kafka/admin/__init__.py
"""
from __future__ import annotations

import argparse
import json
import math
import signal
import sys
import threading
import time
import uuid
from pathlib import Path


def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError('seconds must be finite and positive')
    return number


def client_configs(bootstrap):
    common = {'bootstrap.servers': bootstrap, 'log_level': 0}
    return (dict(common, **{'client.id': 'tcc-lag-admin'}),
            dict(common, **{'client.id': 'tcc-lag-watermarks',
                            'group.id': 'tcc-lag-observer-read-only',
                            'enable.auto.commit': False,
                            'enable.auto.offset.store': False,
                            'allow.auto.create.topics': False}))


def create_probe(bootstrap, group, topic, timeout):
    # Lazy import keeps the offline suite independent of native Kafka libraries.
    from confluent_kafka import Consumer, ConsumerGroupTopicPartitions, TopicPartition
    from confluent_kafka.admin import AdminClient

    admin_config, consumer_config = client_configs(bootstrap)
    return LagProbe(AdminClient(admin_config), Consumer(consumer_config),
                    TopicPartition, ConsumerGroupTopicPartitions,
                    group=group, topic=topic, timeout=timeout)


def error_info(error):
    """Never export broker exception strings, endpoints or configuration values."""
    result = {'error_type': type(error).__name__}
    candidate = error.args[0] if isinstance(error, Exception) and error.args else error
    code = getattr(candidate, 'code', None)
    if callable(code):
        value = code()
        if type(value) is int:
            result['error_code'] = value
    return result


def offset_value(value):
    return value if type(value) is int and value >= 0 else None


class LagProbe:
    def __init__(self, admin, consumer, topic_partition, group_partitions, *,
                 group, topic, timeout, clock=time):
        self.admin, self.consumer = admin, consumer
        self.topic_partition, self.group_partitions = topic_partition, group_partitions
        self.group, self.topic = group, topic
        self.timeout, self.clock = positive_seconds(timeout), clock
        self.known_partitions = []

    def close(self):
        # With auto-commit off and no subscription/assignment, no offsets are stored.
        self.consumer.close()

    def sample(self):
        clock = self.clock
        started_ns, monotonic_start, cpu_start = clock.time_ns(), clock.monotonic_ns(), clock.process_time_ns()
        deadline = monotonic_start + int(self.timeout * 1_000_000_000)
        sample = {'observer': 'confluent-kafka-read-only', 'group': self.group, 'topic': self.topic,
                  'sample_started_ns': started_ns, 'sample_started_monotonic_ns': monotonic_start,
                  'timeout_seconds': self.timeout, 'partitions': [], 'errors': [], 'stages': []}

        def remaining():
            value = (deadline - clock.monotonic_ns()) / 1_000_000_000
            if value <= 0:
                raise TimeoutError('sample budget exhausted')
            return value

        def query(name, operation):
            start = clock.monotonic_ns()
            stage = {'stage': name, 'started_ns': clock.time_ns()}
            try:
                value = operation()
                stage['status'] = 'ok'
                return value
            except Exception as error:
                stage.update(status='error', **error_info(error))
                sample['errors'].append(dict(stage=name, **error_info(error)))
                return None
            finally:
                stage['finished_ns'] = clock.time_ns()
                stage['duration_ns'] = max(0, clock.monotonic_ns() - start)
                sample['stages'].append(stage)

        # Query all-topic metadata: a named unknown topic could auto-create on some brokers.
        metadata = query('metadata', lambda: self.admin.list_topics(timeout=remaining()))
        topic_metadata = metadata.topics.get(self.topic) if metadata is not None else None
        metadata_ok = topic_metadata is not None and topic_metadata.error is None
        partition_metadata = topic_metadata.partitions if metadata_ok else {}
        if metadata_ok and partition_metadata:
            self.known_partitions = sorted(partition_metadata)
        elif metadata is not None:
            reason = 'topic_absent' if topic_metadata is None else 'topic_metadata_unavailable'
            sample['errors'].append({'stage': 'metadata', 'error_type': reason})
            metadata_ok = False
        rows = []
        for partition in self.known_partitions:
            rows.append({'group': self.group, 'topic': self.topic, 'partition': partition,
                         'committed_offset': None, 'current_offset': None, 'log_start_offset': None,
                         'log_end_offset': None, 'lag': None, 'status': 'unknown'})
        sample['partitions'] = rows

        if metadata_ok and rows:
            requested = [self.topic_partition(self.topic, row['partition']) for row in rows]

            def committed():
                futures = self.admin.list_consumer_group_offsets(
                    [self.group_partitions(self.group, requested)], request_timeout=remaining())
                return futures[self.group].result(timeout=remaining())

            group_result = query('committed_offsets', committed)
            offsets = {(part.topic, part.partition): part for part in group_result.topic_partitions or []} \
                if group_result is not None else {}
            for row in rows:
                partition = row['partition']
                if partition_metadata[partition].error is not None:
                    row['status'] = 'partition_metadata_error'
                    continue
                part = offsets.get((self.topic, partition))
                if part is not None and part.error is None:
                    row['committed_offset'] = row['current_offset'] = offset_value(part.offset)
                elif part is not None:
                    row.update(error_info(part.error))
                watermarks = query('watermarks:' + str(partition), lambda: self.consumer.get_watermark_offsets(
                    self.topic_partition(self.topic, partition), timeout=remaining(), cached=False))
                if watermarks is not None:
                    row['log_start_offset'], row['log_end_offset'] = map(offset_value, watermarks)
                low, high, current = row['log_start_offset'], row['log_end_offset'], row['committed_offset']
                if low is None or high is None:
                    row['status'] = 'watermarks_unknown'
                elif current is None:
                    row['status'] = 'committed_offset_unknown'
                elif low > high or not low <= current <= high:
                    row['status'] = 'offsets_out_of_range'
                else:
                    row['lag'], row['status'] = high - current, 'ok'

        known = sum(row['status'] == 'ok' for row in rows)
        sample['status'] = 'ok' if rows and known == len(rows) and not sample['errors'] else ('partial' if known else 'unknown')
        sample['exit_code'] = 0 if sample['status'] == 'ok' else 1
        sample['sample_finished_ns'] = sample['wall_time_ns'] = clock.time_ns()
        sample['sample_finished_monotonic_ns'] = clock.monotonic_ns()
        sample['sample_duration_ns'] = max(0, sample['sample_finished_monotonic_ns'] - monotonic_start)
        sample['observer_process_cpu_total_ns'] = clock.process_time_ns()
        sample['observer_process_cpu_ns'] = max(0, sample['observer_process_cpu_total_ns'] - cpu_start)
        sample['wall_clock_reversed'] = sample['sample_finished_ns'] < started_ns
        if sample['wall_clock_reversed']:
            sample['status'], sample['exit_code'] = 'clock_error', 1
            for row in rows:
                row['lag'] = None
                row['status'] = 'clock_error'
        return sample


def observe(probe, stream, *, interval, stop_event, samples=None, run_id=None, clock=time):
    """Serialize one flushed JSON object per sample; no catch-up burst on overruns."""
    interval = positive_seconds(interval)
    if samples is not None and (type(samples) is not int or samples <= 0):
        raise ValueError('samples must be a positive integer')
    index, previous_start = 0, None
    while not stop_event.is_set() and (samples is None or index < samples):
        started = clock.monotonic_ns()
        record = probe.sample()
        record.update(sample_index=index, configured_interval_seconds=interval,
                      sample_start_delta_ns=started - previous_start if previous_start is not None else None)
        previous_start = started
        if run_id is not None:
            record['run_id'] = run_id
        duration = (clock.monotonic_ns() - started) / 1_000_000_000
        record['interval_overrun_seconds'] = max(0, duration - interval)
        stream.write(json.dumps(record, allow_nan=False, ensure_ascii=False) + '\n')
        stream.flush()
        index += 1
        if samples is None or index < samples:
            stop_event.wait(max(0, interval - duration))
    return index


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bootstrap', default='kafka:9092')
    parser.add_argument('--group', default='audit-persistence')
    parser.add_argument('--topic', default='audit-events')
    parser.add_argument('--interval', type=positive_seconds, required=True)
    parser.add_argument('--timeout', type=positive_seconds, required=True)
    parser.add_argument('--samples', type=int)
    parser.add_argument('--run-id', type=uuid.UUID)
    parser.add_argument('--output', type=Path, help='New JSONL file; refuses to replace existing evidence. Default: stdout.')
    args = parser.parse_args(argv)
    if args.samples is not None and args.samples <= 0:
        parser.error('--samples must be positive')
    stop_event = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop_event.set())
    stream, probe = None, None
    try:
        # Reserve the evidence filename before opening Kafka clients; never overwrite.
        stream = args.output.open('x', encoding='utf-8') if args.output else sys.stdout
        probe = create_probe(args.bootstrap, args.group, args.topic, args.timeout)
        observe(probe, stream, interval=args.interval, stop_event=stop_event,
                samples=args.samples, run_id=str(args.run_id) if args.run_id else None)
        return 0  # Per-sample exit_code/status still records failures/unknown observations.
    except Exception as error:
        print(json.dumps({'observer_status': 'fatal', **error_info(error)}), file=sys.stderr, flush=True)
        return 2
    finally:
        if probe is not None:
            probe.close()
        if stream is not None and stream is not sys.stdout:
            stream.close()


if __name__ == '__main__':
    raise SystemExit(main())
