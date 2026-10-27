"""Read-only verification of the published R2/A1 results (no Docker or raw data)."""
import csv
import json
from pathlib import Path
import finalize_reduced_a1 as f
import qualified_analysis as q
import reduced_campaign as control
import review_commit_uncertainty as review


def verify():
    root = review.REPORT / 'resultados-a1'
    catalog = review.read(root / 'catalog.json')
    frozen = review.read(review.APP / 'experimento/FROZEN-PROTOCOL.json')
    q.verify_extension(frozen)
    review.require(catalog['frozen_protocol_sha256'] == review.sha(review.APP / 'experimento/FROZEN-PROTOCOL.json'), 'frozen protocol mismatch')
    review.require(catalog['producer_source_sha256'] == review.sha(review.APP / 'experimento/finalize_reduced_a1.py'), 'different final analysis source')
    entries = {}
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        path = (root / name).resolve()
        review.require(root.resolve() in path.parents and name not in entries and review.sha(path) == digest, 'public checksum/path mismatch')
        entries[name] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name != 'SHA256SUMS'}
    review.require(set(entries) == actual, 'public checksum inventory incomplete')
    rows = control.plan_rows(review.REPORT / 'plan.csv'); control.validate_plan(rows)
    indexed = {r['run_id']: r for r in rows}
    records = review.read(root / 'per-run.json')
    review.require(len(records) == 65 and len({r['run_id'] for r in records}) == 65 and set(indexed) == {r['run_id'] for r in records}, 'wrong UUID set')
    review.require(len(catalog['runs']) == 65 and {r['run_id'] for r in catalog['runs']} == set(indexed), 'wrong catalog UUID set')
    for item in catalog['runs']:
        row = indexed[item['run_id']]
        review.require(all(row[k] == item[k] for k in row), 'catalog plan changed')
        name = row['run_id'] + '-' + row['variant']
        summary_path, assessment_path = root / 'runs' / (name + '.json'), root / 'assessments' / (row['run_id'] + '.json')
        summary, assessment = review.read(summary_path), review.read(assessment_path)
        review.require(review.sha(summary_path) == item['summary_sha256'] == assessment['original_summary_sha256'], 'summary not original')
        review.require(review.sha(assessment_path) == item['assessment_sha256'] and not assessment['raw_verdict_rewritten'], 'assessment mismatch')
        review.require(summary['instrument_valid'] == assessment['original_instrument_valid'], 'raw verdict changed')
        review.require(item['classification'] == assessment['classification'], 'classification changed')
        review.require(review.sha(root / 'raw-checksums' / (name + '.sha256')) == item['raw_inventory_sha256'] == assessment['raw_inventory_sha256'], 'raw index changed')
        review.require(sum(summary['http_status_counts'].values()) == summary['offered'], 'HTTP accounting')
        review.require(summary['stored_at_observation_end'] + summary['dlq_terminal'] <= summary['offered'], 'overlapping destinations')
    complete = sum(r['classification'] == 'complete_original_evidence' for r in records)
    partial = [r for r in records if r['classification'] == 'partial_commit_timing']
    review.require(complete == catalog['complete_original_evidence'] == 64 and len(partial) == catalog['partial_commit_timing'] == 1, 'classification counts')
    review.require(partial[0]['run_id'] == '8733a7d2-89b5-4a5e-be22-0e4ed6e6b29b' and partial[0]['commit_unobserved_n'] == 1, 'unexpected partial case')
    pairs = f.pair_groups(records)
    for name, expected in [('group-summary.json', f.grouped(records)), ('strict-sensitivity.json', f.grouped(records, strict=True)),
                           ('partial-latency-sensitivity.json', f.grouped(records, sensitivity=True)), ('paired.json', f.paired_comparisons(pairs))]:
        review.require(review.read(root / name) == expected, 'derived aggregation mismatch: ' + name)
    with (root / 'per-run.csv').open(newline='', encoding='utf-8') as stream:
        csv_rows = list(csv.DictReader(stream))
    review.require(len(csv_rows) == 65 and {r['run_id'] for r in csv_rows} == set(indexed), 'CSV identity mismatch')
    review.require(sum(r['raw_files_verified'] for r in catalog['runs']) == catalog['raw_files_verified'] == 1495, 'raw inventory count')
    return {'published_files_verified': len(entries), 'planned_runs': 65, 'complete': complete, 'partial': len(partial), 'raw_inventory_files': 1495,
            'raw_contents_reaudited_here': False, 'full_raw_audit': 'finalize_reduced_a1.py required preserved local evidence'}


if __name__ == '__main__': print(json.dumps(verify()))
