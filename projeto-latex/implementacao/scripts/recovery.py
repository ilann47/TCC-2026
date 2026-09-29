"""Offline recovery timelines. Criteria are supplied explicitly, never scientific defaults.

API: analyze_recovery(config, manifest, generator, application, lag,
    sustained_window_seconds=..., rate_fraction=..., reference_rate_events_s=...,
    throughput_bin_seconds=...)

The caller must verify raw-file completeness/checksums independently. This module
does not approve a protocol, infer a winner, mutate inputs, or execute services.
Readiness observation: manifest.fault_events action='ready', service=<dependency>,
wall_time_ns=<UTC nanoseconds>, probe=<nonempty name>; optional exit_code must be 0.
Existing action='started' records mean completion of the start command, NOT readiness.
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
from itertools import groupby
from pathlib import Path


def _number(value, *, positive=False):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and (value > 0 if positive else True))


def _ns(value, unit=1):
    return int(value * unit) if _number(value, positive=True) else None


def _delay(later, earlier):
    return (later - earlier) / 1_000_000_000 if later is not None and earlier is not None else None


def _first(mapping, key, timestamp):
    if timestamp is not None and (key not in mapping or timestamp < mapping[key]):
        mapping[key] = timestamp


def _timed_result(timestamp, anchor, end, *, reason):
    return {'status': 'observed' if timestamp is not None else 'right_censored',
            'wall_time_ns': timestamp, 'seconds_after_start_command': _delay(timestamp, anchor),
            'followup_seconds': max(0, _delay(end, anchor)) if end is not None else None,
            'reason': None if timestamp is not None else reason}


def analyze_recovery(config, manifest, generator, application, lag, *,
                     sustained_window_seconds, rate_fraction, reference_rate_events_s,
                     throughput_bin_seconds):
    """Return descriptive episodes and exact criteria, with explicit right censoring.

    Throughput is UNIQUE status=persisted post-commit observations, NOT HTTP ACKs,
    duplicate recognitions or DLQ deliveries. A sustained interval consists of
    consecutive complete, nonoverlapping bins, EACH meeting the supplied threshold.
    Bins are anchored at start-command completion and confined to scheduled load.
    Report both the onset of the qualifying interval and its confirmation at end.
    Offered counts and commits for requests sent after restart are also exposed:
    draining old backlog alone must not be hidden behind an aggregate throughput.

    Accepted means a correlated 2xx response observed by the client. A broker ACK
    with a missing/failed HTTP response is not silently reclassified as that state.
    A fixed restart cohort distinguishes successful persistence from mere resolution
    as either persistence OR DLQ. DLQ therefore never demonstrates successful drain.
    """
    for name, value in (('sustained_window_seconds', sustained_window_seconds),
                        ('reference_rate_events_s', reference_rate_events_s),
                        ('throughput_bin_seconds', throughput_bin_seconds)):
        if not _number(value, positive=True):
            raise ValueError(name + ' must be an explicitly supplied positive finite number')
    if not _number(rate_fraction, positive=True) or rate_fraction > 1:
        raise ValueError('rate_fraction must be explicitly supplied in (0, 1]')
    bins_required = sustained_window_seconds / throughput_bin_seconds
    if not math.isclose(bins_required, round(bins_required), abs_tol=1e-9) or bins_required < 1:
        raise ValueError('sustained window must be a positive integer multiple of the bin duration')
    bins_required = round(bins_required)
    bin_ns = int(round(throughput_bin_seconds * 1_000_000_000))
    if bin_ns < 1:
        raise ValueError('bin duration is below nanosecond representation')
    threshold = reference_rate_events_s * rate_fraction
    run_id = config.get('run_id')
    if not run_id:
        raise ValueError('config.run_id is required for correlation')
    issues = []

    def issue(message):
        if message not in issues:
            issues.append(message)

    for key in ('load_exit_code', 'application_log_export_exit_code'):
        if type(manifest.get(key)) is not int or manifest[key] != 0:
            issue('successful complete observation not established: ' + key)
    if manifest.get('run_id') != run_id:
        issue('manifest run_id differs from config')
    if manifest.get('errors') or manifest.get('fault_errors'):
        issue('manifest contains collection/fault-control errors')
    observation_end = _ns(manifest.get('observation_end_ns'))
    if observation_end is None:
        issue('observation end is unavailable; followup cannot be established')
    generator = [r for r in generator if r.get('run_id') == run_id]
    application = [r for r in application if r.get('run_id') == run_id]
    phase_map = {p.get('name'): p for p in config.get('phases', [])}
    starts = []
    sent = {}
    for record in generator:
        if record.get('kind') != 'request_sent' or record.get('phase') != 'measurement':
            continue
        event_id, timestamp = record.get('event_id'), _ns(record.get('sent_at_ms'), 1_000_000)
        if not event_id or timestamp is None:
            issue('measurement send has no identity or valid timestamp')
            continue
        if event_id in sent:
            issue('generator submitted a measurement UUID more than once')
        _first(sent, event_id, timestamp)
        phase = phase_map.get(record.get('segment'))
        phase_start = _ns(record.get('phase_start_ms'), 1_000_000)
        if phase and _number(phase.get('start_seconds')) and phase_start is not None:
            starts.append(phase_start - int(phase['start_seconds'] * 1_000_000_000)
                          + int(config.get('warmup_seconds', 0) * 1_000_000_000))
        else:
            issue('scheduled measurement boundary cannot be verified from phase timestamps')
    measurement_start = min(starts) if starts else None
    measurement_end = None
    if starts and max(starts) - min(starts) > 1_000_000:
        issue('phase timestamps imply inconsistent measurement origins')
    if measurement_start is not None and _number(config.get('measurement_seconds'), positive=True):
        measurement_end = measurement_start + int(config['measurement_seconds'] * 1_000_000_000)
    else:
        issue('scheduled measurement interval is unavailable')
    accepted, persisted, successful, dlq, responses = {}, {}, {}, {}, {}
    for record in generator:
        event_id = record.get('event_id')
        if record.get('kind') != 'http_response' or event_id not in sent:
            continue
        timestamp = _ns(record.get('finished_at_ms'), 1_000_000)
        if timestamp is None or timestamp < sent[event_id]:
            issue('HTTP response timestamp is absent or precedes send')
            continue
        if observation_end is not None and timestamp > observation_end:
            issue('HTTP response lies outside the observation horizon')
            continue
        responses[event_id] = record
        if 200 <= record.get('http_status', 0) < 300:
            _first(accepted, event_id, timestamp)
    if set(sent) - set(responses):
        issue('measurement sends lack complete HTTP response observations')
    for record in application:
        event_id = record.get('event_id')
        if event_id not in sent:
            continue
        kind, timestamp = record.get('milestone'), _ns(record.get('wall_time_ns'))
        if timestamp is None or timestamp < sent[event_id]:
            issue('application milestone lacks a valid post-send wall timestamp')
            continue
        if observation_end is not None and timestamp > observation_end:
            issue('application milestone lies outside the observation horizon')
            continue
        if kind == 'commit_completed' and record.get('status') in ('persisted', 'duplicate'):
            _first(successful, event_id, timestamp)
            if record['status'] == 'persisted':
                _first(persisted, event_id, timestamp)
        elif kind == 'dlq_acknowledged':
            _first(dlq, event_id, timestamp)

    # A simultaneous commit and delayed 2xx does not create a false pending UUID.
    transitions = sorted([(time, 'accepted', key) for key, time in accepted.items()]
                         + [(time, 'persisted', key) for key, time in successful.items()]
                         + [(time, 'dlq', key) for key, time in dlq.items()])
    backlog = []
    accepted_now, persisted_now, dlq_now = set(), set(), set()
    pending, pending_terminal, pending_unresolved = set(), set(), set()
    for instant, group in groupby(transitions, key=lambda item: item[0]):
        touched = set()
        for _, kind, key in group:
            {'accepted': accepted_now, 'persisted': persisted_now, 'dlq': dlq_now}[kind].add(key)
            touched.add(key)
        for key in touched:
            if key in accepted_now and key not in persisted_now:
                pending.add(key)
                if key in dlq_now:
                    pending_terminal.add(key)
                    pending_unresolved.discard(key)
                else:
                    pending_unresolved.add(key)
            else:
                pending.discard(key)
                pending_terminal.discard(key)
                pending_unresolved.discard(key)
        backlog.append({'wall_time_ns': instant, 'http_accepted_uuids': len(accepted_now),
                        'accepted_not_persisted_uuids': len(pending),
                        'accepted_terminal_dlq_not_persisted_uuids': len(pending_terminal),
                        'accepted_unresolved_excluding_dlq_uuids': len(pending_unresolved)})

    lag_points = []
    for sample in lag or []:
        timestamp = _ns(sample.get('wall_time_ns'))
        partitions = sample.get('partitions', [])
        known = (type(sample.get('exit_code')) is int and sample['exit_code'] == 0 and bool(partitions)
                 and all(type(p.get('lag')) is int and p['lag'] >= 0 for p in partitions))
        if timestamp is not None and (observation_end is None or timestamp <= observation_end):
            lag_points.append({'wall_time_ns': timestamp,
                               'lag': sum(p['lag'] for p in partitions) if known else None,
                               'known': known})
    lag_points.sort(key=lambda r: r['wall_time_ns'])
    criteria = {'sustained_window_seconds': sustained_window_seconds, 'rate_fraction': rate_fraction,
                'reference_rate_events_s': reference_rate_events_s, 'threshold_events_s': threshold,
                'throughput_bin_seconds': throughput_bin_seconds, 'consecutive_bins_required': bins_required,
                'bin_anchor': 'start_command_completed', 'bin_interval': '[start, end)',
                'qualifies': 'every complete bin reaches the unique persisted-event rate threshold',
                'measurement_only': True, 'dlq_counts_as_success': False}
    result = {'run_id': run_id, 'variant': config.get('variant'), 'profile': config.get('profile'),
              'criteria': criteria, 'measurement_start_ns': measurement_start,
              'measurement_end_ns': measurement_end, 'observation_end_ns': observation_end,
              'instrumentation_issues': issues, 'backlog_timeline': backlog,
              'lag_timeline': lag_points, 'episodes': [], 'scientific_conclusion_produced': False,
              'notes': [
                  'Start-command completion is not dependency readiness. Readiness requires an explicit named successful probe.',
                  'First zero lag is a sampled position observation, not sustained recovery or proof of persisted audit records.',
                  'DLQ resolves a delivery attempt but never counts as a successful persistence or successful cohort drain.',
                  'Acceptance is a correlated client-observed 2xx; uncertain HTTP outcomes are not silently reclassified.',
                  'Window onset is retrospective; recovery is only confirmed after the entire qualifying interval is observed.',
                  'Only complete bins during scheduled measurement can qualify. Partial tails and post-load drain cannot.',
                  'Counts of offered load and newly sent events expose generator starvation and contribution from older backlog.',
                  'The caller supplies all rate/window criteria and must validate artifact completeness separately.',
              ]}
    service = config.get('fault', {}).get('service')
    if not service:
        result['status'] = 'not_applicable_no_configured_fault'
        return result
    faults = sorted((r for r in manifest.get('fault_events', []) if r.get('service') == service
                     and _ns(r.get('wall_time_ns')) is not None), key=lambda r: r['wall_time_ns'])
    stops = [r for r in faults if r.get('action') == 'stopped']
    if not stops:
        result['status'] = 'not_applicable_no_observed_stop'
        return result
    all_commit_times = sorted(persisted.values())
    all_send_times = sorted(sent.values())
    for index, stop in enumerate(stops):
        next_stop = stops[index + 1]['wall_time_ns'] if index + 1 < len(stops) else None
        local_faults = [r for r in faults if r['wall_time_ns'] >= stop['wall_time_ns']
                        and (next_stop is None or r['wall_time_ns'] < next_stop)]
        resumed = next((r for r in local_faults if r.get('action') == 'started'), None)
        episode = {'service': service, 'stop_command_completed_ns': stop['wall_time_ns'],
                   'start_command_completed_ns': resumed['wall_time_ns'] if resumed else None,
                   'start_reason': resumed.get('reason', 'planned') if resumed else None}
        result['episodes'].append(episode)
        if not resumed:
            episode['status'] = 'right_censored_restart_not_observed'
            continue
        anchor = resumed['wall_time_ns']
        horizon = min(t for t in (observation_end, next_stop) if t is not None) if observation_end is not None else None
        ready = next((r for r in local_faults if r.get('action') == 'ready' and r['wall_time_ns'] >= anchor
                      and r.get('probe') and r.get('exit_code', 0) == 0
                      and (horizon is None or r['wall_time_ns'] <= horizon)), None)
        ready_time = ready['wall_time_ns'] if ready else None
        episode['dependency_ready'] = {'status': 'observed_by_probe' if ready else 'not_observed',
            'wall_time_ns': ready_time, 'probe': ready.get('probe') if ready else None,
            'seconds_after_start_command': _delay(ready_time, anchor)}
        post_restart = [t for t in all_commit_times if t >= anchor and (horizon is None or t <= horizon)]
        episode['first_post_restart_new_persistence'] = _timed_result(
            post_restart[0] if post_restart else None, anchor, horizon,
            reason='no new persistence observed before the observation ended')

        cohort = {key for key, accepted_time in accepted.items() if accepted_time <= anchor
                  and (key not in successful or successful[key] > anchor)}
        terminal_at_restart = {key for key in cohort if dlq.get(key, math.inf) <= anchor}
        persisted_cohort = {key: successful[key] for key in cohort if key in successful
                            and (horizon is None or successful[key] <= horizon)}
        terminal_cohort = {key for key in cohort if key in dlq and (horizon is None or dlq[key] <= horizon)
                           and key not in persisted_cohort}
        resolved_times = {key: min(successful.get(key, math.inf), dlq.get(key, math.inf)) for key in cohort}
        resolved = {key: value for key, value in resolved_times.items()
                    if value != math.inf and (horizon is None or value <= horizon)}
        success_time = max(anchor, max(persisted_cohort.values())) if cohort and set(persisted_cohort) == cohort else None
        resolved_time = max(anchor, max(resolved.values())) if cohort and set(resolved) == cohort else None
        episode['restart_cohort'] = {'definition': 'client-accepted measurement UUIDs not persisted at start-command completion',
            'event_ids': sorted(cohort), 'count': len(cohort), 'terminal_dlq_already_at_restart': len(terminal_at_restart),
            'persisted_by_observation_end': len(persisted_cohort),
            'terminal_dlq_not_persisted_by_observation_end': len(terminal_cohort),
            'unresolved_by_observation_end': len(cohort - set(resolved)),
            'successful_drain': _timed_result(success_time, anchor, horizon,
                reason='terminal DLQ is not successful drain' if terminal_cohort else 'cohort not fully persisted within observation'),
            'resolved_as_persisted_or_dlq': _timed_result(resolved_time, anchor, horizon,
                reason='cohort still has unresolved UUIDs')}
        if not cohort:
            for key in ('successful_drain', 'resolved_as_persisted_or_dlq'):
                episode['restart_cohort'][key].update(status='not_applicable_empty_cohort', reason='no pending accepted UUID at restart')
        elif terminal_cohort and success_time is None:
            episode['restart_cohort']['successful_drain']['status'] = 'terminal_dlq_present_not_successfully_drained'
        zero = next((r for r in lag_points if r['wall_time_ns'] >= anchor and r['lag'] == 0
                     and (horizon is None or r['wall_time_ns'] <= horizon)), None)
        episode['first_observed_zero_lag'] = _timed_result(zero['wall_time_ns'] if zero else None, anchor, horizon,
            reason='no known zero-lag sample after restart; this is not proof of positive lag')
        if not lag_points:
            episode['first_observed_zero_lag']['status'] = 'not_observed_no_lag_samples'

        bins = []
        usable_end = min(horizon, measurement_end) if horizon is not None and measurement_end is not None else None
        fresh_times = sorted(t for key, t in persisted.items() if sent[key] >= anchor)
        complete_bins = max(0, (usable_end - anchor) // bin_ns) if usable_end is not None else 0
        for ordinal in range(complete_bins):
            start, end = anchor + ordinal * bin_ns, anchor + (ordinal + 1) * bin_ns
            count = bisect.bisect_left(all_commit_times, end) - bisect.bisect_left(all_commit_times, start)
            offered = bisect.bisect_left(all_send_times, end) - bisect.bisect_left(all_send_times, start)
            fresh = bisect.bisect_left(fresh_times, end) - bisect.bisect_left(fresh_times, start)
            rate = count / throughput_bin_seconds
            during_load = measurement_start is not None and start >= measurement_start
            bins.append({'start_ns': start, 'end_ns': end, 'seconds_after_start_command': ordinal * throughput_bin_seconds,
                         'new_persisted_uuids': count, 'throughput_events_s': rate,
                         'offered_requests': offered, 'offered_rate_events_s': offered / throughput_bin_seconds,
                         'persisted_uuids_sent_after_restart': fresh, 'complete': True,
                         'qualifies_rate_threshold': during_load and rate >= threshold})
        streak = 0
        qualifying = None
        for ordinal, bucket in enumerate(bins):
            streak = streak + 1 if bucket['qualifies_rate_threshold'] else 0
            if streak >= bins_required:
                qualifying = (bins[ordinal - bins_required + 1]['start_ns'], bucket['end_ns'])
                break
        if issues:
            status, reason = 'inconclusive_instrumentation', 'see instrumentation_issues; no positive recovery claim'
        elif qualifying:
            status, reason = 'observed', None
        elif len(bins) < bins_required:
            status, reason = 'right_censored_insufficient_followup', 'fewer complete observed load bins than the required sustained interval'
        else:
            status, reason = 'right_censored_recovery_not_observed', 'no sustained qualifying interval before observation/load ended'
        onset, confirmed = qualifying if qualifying and not issues else (None, None)
        episode['throughput_recovery'] = {
            'status': status, 'reason': reason, 'window_start_ns': onset, 'confirmed_at_ns': confirmed,
            'window_onset_seconds_after_start_command': _delay(onset, anchor),
            'confirmation_seconds_after_start_command': _delay(confirmed, anchor),
            'confirmation_seconds_after_ready_probe': _delay(confirmed, ready_time)
                if confirmed is not None and ready_time is not None and confirmed >= ready_time else None,
            'confirmed_before_first_ready_probe': bool(confirmed is not None and ready_time is not None and confirmed < ready_time),
            'usable_observation_seconds': max(0, _delay(usable_end, anchor)) if usable_end is not None else None,
            'complete_bins': len(bins),
            'unscored_partial_tail_seconds': max(0, (usable_end - anchor) % bin_ns / 1_000_000_000)
                if usable_end is not None and usable_end >= anchor else None,
            'bins': bins}
        episode['status'] = 'analyzed_with_instrumentation_limits' if issues else 'analyzed'
    result['status'] = 'analyzed_with_instrumentation_limits' if issues else 'analyzed'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--sustained-window-seconds', type=float, required=True)
    parser.add_argument('--rate-fraction', type=float, required=True)
    parser.add_argument('--reference-rate-events-s', type=float, required=True)
    parser.add_argument('--throughput-bin-seconds', type=float, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    def records(name, *, optional=False):
        path = args.run_dir / name
        if optional and not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

    result = analyze_recovery(json.loads((args.run_dir / 'config.json').read_text(encoding='utf-8')),
        json.loads((args.run_dir / 'manifest.json').read_text(encoding='utf-8')),
        records('generator.jsonl'), records('application.jsonl'), records('lag.jsonl', optional=True),
        sustained_window_seconds=args.sustained_window_seconds, rate_fraction=args.rate_fraction,
        reference_rate_events_s=args.reference_rate_events_s, throughput_bin_seconds=args.throughput_bin_seconds)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        # Exclusive creation; use a new destination, never overwrite a prior analysis.
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(encoded + '\n')
    else:
        print(encoded)


if __name__ == '__main__':
    main()
