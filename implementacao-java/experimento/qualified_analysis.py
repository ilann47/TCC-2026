"""A1 analytical amendment: immutable raw verdicts, metric-specific eligibility.

This is post-collection analysis, not a measurement instrument. No imputation,
image rebuild, replacement UUID, or modification of a raw evidence directory.
"""
import argparse
import json
from pathlib import Path
import sys
import review_commit_uncertainty as review

APP = review.APP
REPORT = review.REPORT
RUNTIME = review.RUNTIME
POLICY = REPORT / 'emenda-a1/policy.json'
require = review.require


def implementation_hashes():
    return {name: review.sha(path) for name, path in {
        'analysis': Path(__file__), 'review': APP / 'experimento/review_commit_uncertainty.py',
        'controller': APP / 'experimento/reduced_campaign.py', 'policy': POLICY}.items()}


def classify(audit, summary, policy):
    """Eligibility does not modify or replace summary.instrument_valid."""
    partial = not audit['original_instrument_valid']
    findings = audit['findings']
    if partial:
        require(audit['variant'] == policy['allowed_variant'] and
                audit['profile'] == policy['allowed_profile'], 'A1: variant/profile not covered')
        require(audit['original_analyzer_exit'] == 2 and findings, 'A1: no reviewed mismatch')
        require(all(f['finding'] == 'persisted_with_unobserved_commit_time_and_http_503'
                    and f['phase'] == 'measure' and f['row_observed'] and f['commit_time'] is None
                    for f in findings), 'A1: unexplained or non-measurement mismatch')
        expected = sorted(f['event_id'] + ':incomplete_commit_db_evidence' for f in findings)
        require(sorted(audit['original_issues']) == expected, 'A1: additional instrument failure')
    else:
        require(not findings and not audit['original_issues'] and audit['original_analyzer_exit'] == 0,
                'A1: contradictory complete evidence')
    counts = audit['counts_crosschecked']
    unknown = audit['stored_without_observed_commit_time']
    require(unknown == len(findings), 'A1: timing coverage mismatch')
    within = summary['stored_within_measurement']
    duration = summary['measure_seconds']
    require(duration > 0 and 0 <= within <= audit['stored_with_observed_commit_time'], 'A1: invalid completion count')
    return {'run_id': audit['run_id'], 'variant': audit['variant'], 'profile': audit['profile'],
            'block': audit['block'], 'rate': audit['rate'],
            'classification': 'partial_commit_timing' if partial else 'complete_original_evidence',
            'original_instrument_valid': audit['original_instrument_valid'],
            'original_issues': audit['original_issues'], 'original_analyzer_exit': audit['original_analyzer_exit'],
            'original_summary_sha256': audit['summary_sha256'],
            'raw_inventory_sha256': audit['raw_inventory_sha256'],
            'amendment_revision': policy['revision'], 'policy_sha256': review.sha(POLICY),
            'implementation_hashes': implementation_hashes(),
            'eligibility': {'http': True, 'persistence_at_observation_end': True, 'resources': True,
                            'commit_latency_primary': not partial, 'commit_latency_sensitivity': True,
                            'throughput': 'conservative_bounds' if partial else 'observed_exact',
                            'recovery': 'observed_milestones_only'},
            'counts': counts, 'http_status_counts': audit['http_status_counts'],
            'timing': {'stored_with_observed_time': audit['stored_with_observed_commit_time'],
                       'stored_without_observed_time': unknown,
                       'unobserved_event_ids': [f['event_id'] for f in findings],
                       'imputed_timestamps': 0},
            'completion_in_measurement': {'observed_count': within, 'lower_count': within,
                                          'upper_count': within + unknown, 'duration_seconds': duration,
                                          'lower_per_second': within / duration,
                                          'upper_per_second': (within + unknown) / duration,
                                          'interpretation': 'accounting sensitivity bounds, not a confidence interval'},
            'raw_verdict_rewritten': False}


def assess(row, frozen):
    policy = verify_extension(frozen)
    audit = review.audit_run(row, frozen, 'campaign')
    root = APP / '.runtime/entrega04' / f"{row['run_id']}-{row['variant']}"
    return classify(audit, review.read(root / 'summary.json'), policy)


def save_assessment(assessment):
    target = RUNTIME / 'assessments-a1' / (assessment['run_id'] + '.json')
    target.parent.mkdir(exist_ok=True)
    if target.exists():
        require(review.read(target) == assessment, 'A1: existing assessment differs; never overwrite')
    else:
        with target.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(assessment, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    return target


def verify_extension(frozen):
    extension = frozen.get('analytical_amendment', {})
    require(extension.get('revision') == '2026-10-27-a1-qualified-commit', 'A1: missing frozen extension')
    files = extension.get('files', {})
    required = {'policy', 'analysis', 'review', 'baseline_audit', 'adoption_audit', 'original_protocol', 'original_controller'}
    require(set(files) == required, 'A1: incomplete extension inventory')
    for entry in files.values():
        path = (APP / entry['path']).resolve()
        require(APP.resolve() in path.parents and review.sha(path) == entry['sha256'], 'A1: extension hash/path mismatch')
    original = review.read(APP / files['original_protocol']['path'])
    active = dict(frozen)
    active.pop('analytical_amendment', None)
    active['controller_sha256'] = original['controller_sha256']
    require(active == original, 'A1: measurement protocol changed beyond the analytical extension')
    require(review.sha(APP / files['original_controller']['path']) == original['controller_sha256'], 'A1: original controller changed')
    policy = review.read(POLICY)
    require(policy['allowed_variant'] == 'sync' and policy['allowed_profile'] == 'postgres-stop'
            and policy['no_imputation'] is True and policy['no_replacement_or_repeat'] is True,
            'A1: unsupported analytical rule')
    require(policy['plan_sha256'] == frozen['plan_sha256'] and policy['reference_rate'] == frozen['reference_rate'] == 48,
            'A1: plan/reference drift')
    require(policy['revision'] == extension['revision'] and policy['human_authorized'] is True, 'A1: amendment not authorized')
    adoption = review.read(APP / files['adoption_audit']['path'])
    require(adoption['implementation_hashes'] == implementation_hashes(), 'A1: adoption audit for different implementation')
    require(adoption['original_summary_changes'] == 0 and adoption['counts'] == {'pilot': 9, 'complete': 36, 'partial': 1, 'unstarted': 28},
            'A1: unexpected adoption baseline')
    return policy


def initial_shape(state, plan, policy):
    require(state['phase'] == 'attention_required' and not state.get('controller_pid') and not state.get('runner_pid'), 'A1: controller not stopped')
    n = policy['retrospective_attempts']
    require(len(plan) == 65 and len({r['run_id'] for r in plan}) == 65, 'A1: wrong plan')
    require(state['campaign_completed'] == [r['run_id'] for r in plan[:n - 1]] and not state.get('campaign_qualified'), 'A1: changed completed baseline')
    require(state['current']['run_id'] == plan[n - 1]['run_id'] == policy['initial_partial_run_id'], 'A1: different interruption needs review')
    for row in plan[n:]:
        require(not (APP / '.runtime/entrega04' / f"{row['run_id']}-{row['variant']}").exists(), 'A1: later UUID already attempted')


def resume_preflight(state, plan, frozen):
    policy = verify_extension(frozen)
    initial_shape(state, plan, policy)
    extension = frozen['analytical_amendment']['files']
    adoption = review.read(APP / extension['adoption_audit']['path'])
    require(review.sha(RUNTIME / 'state.json') == adoption['state_before_sha256'], 'A1: journal changed since adoption audit')
    baseline = review.read(APP / extension['baseline_audit']['path'])
    for item in baseline['runs']:
        root = APP / '.runtime/entrega04' / f"{item['run_id']}-{item['variant']}"
        require(review.sha(root / 'summary.json') == item['summary_sha256'] and
                review.sha(root / 'SHA256SUMS') == item['raw_inventory_sha256'], 'A1: baseline summary/inventory changed')
        require(review.verify_checksums(root) == item['raw_files_verified'], 'A1: baseline raw inventory changed')
    partial = assess(plan[policy['retrospective_attempts'] - 1], frozen)
    expected = next(a for a in adoption['assessments'] if a['run_id'] == partial['run_id'])
    require(partial == expected and partial['classification'] == 'partial_commit_timing', 'A1: partial assessment changed')
    return partial


def adoption_snapshot(plan):
    """Offline preparatory audit; cannot launch a controller or change its state."""
    policy = review.read(POLICY)
    baseline_path = REPORT / 'revisao-confirmacao-incerta/audit.json'
    require(review.sha(baseline_path) == policy['baseline_audit_sha256'], 'A1: baseline review changed')
    baseline = review.read(baseline_path)
    state = review.read(RUNTIME / 'state.json')
    before = review.sha(RUNTIME / 'state.json')
    require(before == baseline['state_sha256'], 'A1: original journal changed')
    initial_shape(state, plan, policy)
    frozen = review.read(APP / 'experimento/protocolos/2026-10-27-r2-before-a1/FROZEN-PROTOCOL.json')
    require(review.sha(REPORT / 'plan.csv') == policy['plan_sha256'] == frozen['plan_sha256'], 'A1: plan changed')
    require(review.sha(REPORT / 'policy.json') == baseline['policy_sha256'], 'A1: R2 policy changed')
    indexed = {a['run_id']: a for a in baseline['runs']}
    pilots = review.read(REPORT / 'pilot-plan.json')
    assessments = []
    files = 0
    for stage, rows in [('pilot', pilots), ('campaign', plan[:policy['retrospective_attempts']])]:
        for row in rows:
            print(f"A1 audit {stage} {row['run_id']}", file=sys.stderr, flush=True)
            audit = review.audit_run(row, frozen, stage)
            old = indexed[row['run_id']]
            require(audit == old, 'A1: original review result changed')
            files += audit['raw_files_verified']
            if stage == 'campaign':
                root = APP / '.runtime/entrega04' / f"{row['run_id']}-{row['variant']}"
                assessments.append(classify(audit, review.read(root / 'summary.json'), policy))
            else:
                require(audit['original_instrument_valid'] and not audit['findings'], 'A1: pilot invalid')
    require(review.sha(RUNTIME / 'state.json') == before, 'A1: journal changed during adoption audit')
    counts = {'pilot': len(pilots), 'complete': sum(a['classification'] == 'complete_original_evidence' for a in assessments),
              'partial': sum(a['classification'] == 'partial_commit_timing' for a in assessments), 'unstarted': len(plan) - len(assessments)}
    require(counts == {'pilot': 9, 'complete': 36, 'partial': 1, 'unstarted': 28}, 'A1: different baseline')
    return {'revision': policy['revision'], 'implementation_hashes': implementation_hashes(),
            'state_before_sha256': before, 'baseline_review_sha256': review.sha(baseline_path),
            'counts': counts, 'raw_files_verified_before_and_after': files,
            'original_summary_changes': 0, 'raw_verdicts_rewritten': 0,
            'new_measurements': 0, 'assessments': assessments}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adoption-output', type=Path, required=True)
    args = parser.parse_args()
    target = args.adoption_output.resolve()
    require(RUNTIME.resolve() in target.parents and not target.exists(), 'A1: new runtime output required')
    import csv
    with (REPORT / 'plan.csv').open(newline='', encoding='utf-8') as stream:
        plan = list(csv.DictReader(stream))
    for row in plan:
        for key in ('block', 'rate', 'vus'):
            row[key] = int(row[key])
    data = adoption_snapshot(plan)
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in data.items() if k != 'assessments'}))


if __name__ == '__main__':
    main()
