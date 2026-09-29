"""Descriptive standalone figure from real short validation runs, not TCC inference."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sync_run', type=Path)
    parser.add_argument('async_run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--replace-generated', action='store_true', help='Replace only generated chart files, never raw run data')
    args = parser.parse_args()
    configs, summaries, event_sets = [], [], []
    for path in (args.sync_run, args.async_run):
        configs.append(json.loads((path / 'config.json').read_text(encoding='utf-8')))
        summaries.append(json.loads((path / 'analysis' / 'summary.json').read_text(encoding='utf-8')))
        with (path / 'analysis' / 'events.csv').open(encoding='utf-8', newline='') as stream:
            event_sets.append([row for row in csv.DictReader(stream) if row['phase'] == 'measurement'])
    if any(c['profile'] != 'validation' for c in configs):
        raise ValueError('This plotting tool is only for explicitly labeled functional validation')
    for key in ('rate', 'measurement_seconds', 'warmup_seconds', 'payload_padding_bytes'):
        if configs[0][key] != configs[1][key]:
            raise ValueError(f'Incompatible run configurations: {key}')
    if any(c.get('fault') or c.get('burst') for c in configs):
        raise ValueError('Figure expects the same uncomplicated validation workload in both variants')
    if any(s['instrumentation_issues'] for s in summaries):
        raise ValueError('Resolve or disclose instrumentation issues before comparing the measurements')
    args.output.mkdir(parents=True, exist_ok=args.replace_generated)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titleweight': 'bold', 'savefig.facecolor': 'white'})
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 6.1))
    colors = ['#245B8A', '#BC5D22']
    fields = [('end_to_end_ms', 'Conclusão: envio → pós-commit'),
              ('http_wall_duration_ms', 'Resposta HTTP observada pelo cliente')]
    for axis, (field, title) in zip(axes, fields):
        values = [[float(row[field]) for row in rows if row[field]] for rows in event_sets]
        boxes = axis.boxplot(values, tick_labels=['Síncrona', 'Assíncrona'], widths=.48, patch_artist=True,
                             medianprops={'color': 'white', 'linewidth': 2},
                             flierprops={'marker': 'o', 'markersize': 4, 'alpha': .65})
        for patch, color in zip(boxes['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(.9)
        axis.set_title(title, fontsize=11.5, pad=13)
        axis.set_ylabel('Duração (ms)')
        axis.set_ylim(bottom=0)
        axis.grid(axis='y', alpha=.20)
        axis.set_axisbelow(True)
        axis.yaxis.set_major_formatter(FuncFormatter(lambda value, position: f'{value:g}'.replace('.', ',')))
        axis.set_xticklabels([f"{label}\nMediana: {summary[field]['median']:.2f} ms".replace('.', ',')
                              for label, summary in zip(('Síncrona', 'Assíncrona'), summaries)], fontsize=10)
    fig.suptitle('Validação funcional do instrumento de coleta', x=.5, y=.98,
                 fontsize=18, fontweight='bold', color='#172534')
    warmup = 'sem aquecimento' if not configs[0]['warmup_seconds'] else f"aquecimento de {configs[0]['warmup_seconds']} s"
    fig.text(.5, .91, f"Uma execução por variante • {configs[0]['rate']} eventos/s • {configs[0]['measurement_seconds']} s • {warmup}",
             ha='center', fontsize=11, color='#475569')
    counts = '; '.join(f"{label}: {summary['offered_events']} enviados, {summary['completed_after_send_by_observation_end']} persistidos"
                       for label, summary in zip(('Síncrona', 'assíncrona'), summaries))
    fig.text(.5, .125,
             counts + '.',
             ha='center', fontsize=10, color='#334155')
    fig.text(.5, .077, 'Dados de desenvolvimento: não constituem o experimento definitivo nem demonstram superioridade.',
             ha='center', fontsize=10.5, fontweight='bold', color='#7C2D12')
    fig.text(.5, .029, 'Caixa: P25–P75; linha: mediana; círculos: valores além de 1,5 IQR. Dados e marcos preservados por UUID.',
             ha='center', fontsize=8.7, color='#475569')
    fig.subplots_adjust(top=.79, bottom=.24, left=.085, right=.98, wspace=.28)
    for extension in ('png', 'svg', 'pdf'):
        fig.savefig(args.output / f'validacao_instrumentacao.{extension}', dpi=180)
    plt.close(fig)
    summary_rows = []
    for summary in summaries:
        summary_rows.append({'run_id': summary['run_id'], 'variant': summary['variant'],
                             'offered': summary['offered_events'], 'accepted': summary['http_accepted_events'],
                             'persisted': summary['completed_after_send_by_observation_end'],
                             'throughput_events_s': summary['throughput_persisted_events_s'],
                             'http_median_ms': summary['http_wall_duration_ms']['median'],
                             'completion_mean_ms': summary['end_to_end_ms']['mean'],
                             'completion_median_ms': summary['end_to_end_ms']['median'],
                             'completion_p95_ms': summary['end_to_end_ms']['p95']})
    with (args.output / 'comparison.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)
    provenance = {'profile': 'validation', 'interpretation': 'descriptive development measurements only',
                  'plot_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'matplotlib_version': matplotlib.__version__, 'sources': []}
    for path in (args.sync_run, args.async_run):
        provenance['sources'].append({'run_id': path.name, 'summary_sha256': hashlib.sha256(
            (path / 'analysis' / 'summary.json').read_bytes()).hexdigest(), 'events_sha256': hashlib.sha256(
            (path / 'analysis' / 'events.csv').read_bytes()).hexdigest()})
    (args.output / 'provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print(str(args.output.resolve()))


if __name__ == '__main__':
    main()
