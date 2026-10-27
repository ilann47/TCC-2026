"""Read the existing Java instrument's evidence; never estimate missing measurements."""
import argparse
import csv
import html
import json
import math
from pathlib import Path
import shutil
import subprocess

APP = Path(__file__).resolve().parents[1]
RUNTIME = APP / '.runtime' / 'demonstracao'
NA = 'Não se aplica'
MISSING = 'Não disponível'
SCENARIOS = {'normal': 'Carga normal', 'postgres-stop': 'PostgreSQL interrompido nas duas versões',
             'consumer-stop': 'Consumidor interrompido (somente assíncrona)'}
COMPONENTS = {'sync': ('sync-api', 'postgres'), 'async': ('async-api', 'consumer', 'postgres', 'kafka')}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def number(value, suffix='', integer=False):
    if not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value):
        return MISSING
    text = f'{value:,.0f}' if integer else f'{value:,.2f}'
    return text.replace(',', '_').replace('.', ',').replace('_', '.') + suffix


def stat(summary, key, field, suffix=' ms'):
    value = summary.get(key, {})
    return number(value.get(field), suffix) if value.get('n', 0) > 0 else 'Sem observações'


def resource(summary, component):
    matches = [value for key, value in summary.get('resources', {}).items()
               if key == f'tcc-entrega04-{component}-1']
    return matches[0] if len(matches) == 1 else {}


def stack_total(summary, metric):
    values = [resource(summary, part).get(metric, {}) for part in COMPONENTS[summary['variant']]]
    if any(v.get('n', 0) <= 0 or not isinstance(v.get('mean'), (int, float)) for v in values):
        return MISSING
    return number(sum(v['mean'] for v in values), ' %' if metric == 'cpu_percent' else ' MiB')


def validate(path, variant, scenario):
    root = Path(path).resolve()
    summary = read_json(root / 'summary.json')
    profile = 'steady' if scenario == 'normal' else scenario
    if (summary.get('variant') != variant or summary.get('profile') != profile
            or summary.get('kind') != 'validation' or summary.get('instrument_valid') is not True
            or summary.get('issues')):
        raise ValueError(f'{variant}: coleta não é uma validação íntegra do cenário solicitado')
    if summary.get('offered', 0) <= 0 or summary.get('instrumentation', {}).get('enabled') is not True:
        raise ValueError(f'{variant}: sem carga/instrumentação válida')
    manifest = {}
    for line in (root / 'manifest.txt').read_text(encoding='utf-8').splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            manifest[key] = value
    for key in ('run_id', 'dataset_id', 'variant', 'profile'):
        if str(summary[key]) != manifest.get(key):
            raise ValueError(f'{variant}: manifesto divergente ({key})')
    # Duplicates are checked from measured exported UUIDs, not inferred from a successful HTTP.
    with (root / 'events.csv').open(encoding='utf-8', newline='') as stream:
        measured = {r['event_id'] for r in csv.DictReader(stream) if r['phase'] == 'measure'}
    rows = [json.loads(line) for line in (root / 'database.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    measured_rows = [r for r in rows if r['event_id'] in measured]
    summary['_duplicates'] = len(measured_rows) - len({r['event_id'] for r in measured_rows})
    if len({r['event_id'] for r in measured_rows}) != summary.get('stored_at_observation_end'):
        raise ValueError(f'{variant}: resumo e exportação do banco divergem')
    summary['_path'] = str(root)
    summary['_manifest'] = manifest
    return summary


def recovery_value(summary, which):
    recovery = summary.get('recovery', {})
    if recovery.get('applicable') is not True:
        return NA
    if which == 'stable':
        stable = recovery.get('stable_throughput_recovery', {})
        if not isinstance(stable, dict) or stable.get('observed') is not True:
            return 'Não observada na janela'
        return number(stable.get('confirmed_after_restore_ms'), ' ms')
    if which == 'backlog':
        if recovery.get('accepted_not_persisted_at_restore') == 0:
            return 'Sem aceitos pendentes na retomada'
        if recovery.get('all_pre_restore_accepted_persisted') is not True:
            return 'Não concluída na observação'
        return number(recovery.get('backlog_persistence_recovery_ms'), ' ms')
    return number(recovery.get('first_commit_after_restore_ms'), ' ms')


def build_report(summaries, scenario):
    expected = {'async'} if scenario == 'consumer-stop' else {'sync', 'async'}
    if set(summaries) != expected:
        raise ValueError('Colunas ausentes ou cenário de consumidor atribuído à síncrona')
    values = list(summaries.values())
    for key in ('dataset_id', 'rate', 'measure_seconds'):
        if len({s[key] for s in values}) != 1:
            raise ValueError(f'Parâmetros diferentes: {key}')
    for key in ('warmup_seconds', 'drain_seconds', 'vus', 'application_images_sha256', 'instrument_source_sha256', 'analyzer_image_id'):
        if any(not s['_manifest'].get(key) for s in values) or len({s['_manifest'][key] for s in values}) != 1:
            raise ValueError(f'Ambientes diferentes ou não identificados: {key}')
    rows = []

    def row(group, label, getter):
        rows.append({'group': group, 'metric': label,
                     **{v: getter(summaries[v]) if v in summaries else NA for v in ('sync', 'async')}})

    for field, label in [('mean', 'média'), ('median', 'mediana'), ('p95', 'p95'), ('p99', 'p99')]:
        row('Tempos', f'Resposta HTTP — {label}', lambda s, f=field: stat(s, 'http_duration_ms', f))
    row('Tempos', 'Envio → resposta — média', lambda s: stat(s, 'send_to_response_ms', 'mean'))
    for field, label in [('mean', 'média'), ('p95', 'p95'), ('p99', 'p99')]:
        row('Tempos', f'Envio → commit no banco — {label}', lambda s, f=field: stat(s, 'send_to_commit_ms', f))
    row('Tempos', 'Amostras com commit observado', lambda s: number(s.get('send_to_commit_ms', {}).get('n'), integer=True))
    row('Carga e persistência', 'Gravados/s dentro da medição', lambda s: number(s.get('completed_per_second'), ' registros/s'))
    for key, label in [('offered', 'Requisições enviadas'), ('accepted', 'Aceitos (201 / 202 com UUID correto)'),
                       ('stored_within_measurement', 'Gravados dentro da medição'), ('stored_at_observation_end', 'Gravados até o fim da coleta')]:
        row('Carga e persistência', label, lambda s, k=key: number(s.get(k), integer=True))
    row('Erros e destinos', 'Respostas por código HTTP', lambda s: '; '.join(f'{k}: {v}' for k, v in sorted(s.get('http_status_counts', {}).items())) or MISSING)
    row('Erros e destinos', 'Erros HTTP/contrato', lambda s: number(s.get('http_error_fraction') * 100, ' %') if isinstance(s.get('http_error_fraction'), (int, float)) else MISSING)
    for key, label in [('dropped_iterations_all_phases', 'Iterações não iniciadas (inclui aquecimento)'),
                       ('dlq_terminal', 'Aceitos em DLQ, não gravados'), ('pending_retained', 'Aceitos pendentes no Kafka ao fim'),
                       ('accepted_unreconciled', 'Aceitos sem destino reconciliado'), ('stored_despite_unconfirmed_http', 'Gravados sem confirmação HTTP'),
                       ('_duplicates', 'UUIDs duplicados no banco (medição)'), ('integrity_mismatches', 'Divergências de conteúdo/hash'),
                       ('idempotent_replays', 'Reentregas idempotentes observadas')]:
        row('Erros e destinos', label, lambda s, k=key: number(s.get(k), integer=True))
    row('Fila', 'Pico de aceitos ainda não gravados', lambda s: number(s.get('instrumentation', {}).get('max_accepted_not_committed'), integer=True))
    row('Fila', 'Pico de lag Kafka amostrado', lambda s: NA if s['variant'] == 'sync' else number(s.get('instrumentation', {}).get('max_kafka_lag'), integer=True))
    row('Recursos', 'CPU média — soma dos serviços do fluxo', lambda s: stack_total(s, 'cpu_percent'))
    row('Recursos', 'Memória média — soma dos serviços do fluxo', lambda s: stack_total(s, 'memory_mib'))
    for component in ('sync-api', 'async-api', 'consumer', 'postgres', 'kafka'):
        for metric, label, unit in [('cpu_percent', 'CPU média', ' %'), ('memory_mib', 'memória média', ' MiB')]:
            row('Recursos por serviço', f'{component}: {label}', lambda s, c=component, m=metric, u=unit: NA if c not in COMPONENTS[s['variant']] else stat(resource(s, c), m, 'mean', u))
    for who, label in [('generator', 'k6'), ('observer', 'Observador')]:
        for key, suffix in [('cpu_p95_percent_of_limit', 'CPU p95 / limite'), ('memory_max_percent_of_limit', 'memória máxima / limite')]:
            row('Instrumentos (separados do sistema)', f'{label}: {suffix}', lambda s, w=who, k=key: number(s.get('instrumentation', {}).get(w, {}).get(k), ' %'))
    for which, label in [('first', 'Primeiro commit após retomada'), ('backlog', 'Todos os aceitos pendentes gravados'), ('stable', 'Recuperação sustentada confirmada')]:
        row('Recuperação', label, lambda s, w=which: recovery_value(s, w))
    warnings = [
        'Demonstração curta, uma execução por versão, em sequência (síncrona primeiro). Não é resultado definitivo nem comprova superioridade arquitetural.',
        '202 significa aceitação pelo Kafka, não persistência. Tempos de commit incluem somente registros cujo commit foi observado; leia também os destinos não gravados.',
        'Gravados/s considera a janela medida, sem somar a drenagem posterior. A contagem final inclui a observação após a carga.',
        'Fluxo síncrono: sync-api + PostgreSQL. Fluxo assíncrono: async-api + consumer + PostgreSQL + Kafka. CPU é soma das médias por contêiner; 100% equivale a um núcleo lógico e a soma pode ultrapassar 100%. Memória Docker em MiB; não é memória total do computador.',
        'k6 e observador estão separados do consumo do sistema. Outros contêineres/programas do computador podem disputar recursos; não foram encerrados.',
        'Zero UUID duplicado não implica ausência de reentrega; o banco usa chave única. DLQ não é gravação nem desaparecimento; aceitos sem destino exigem investigação.',
        'Recuperação sustentada exige três janelas completas de 10 s após a retomada, ≥90% da taxa-alvo gravada/s, sem erros HTTP e com pendências/lag limitados e observação saudável. Não observada não significa zero.',
        'Dados sintéticos e banco isolado tcc-entrega04. A cada execução, somente sua tabela experimental é reiniciada; exportações anteriores são preservadas. O banco principal/Swagger não é alterado.',
    ]
    for variant, summary in summaries.items():
        if summary.get('dropped_iterations_all_phases', 0) > 0:
            warnings.append(f'{variant}: houve iterações não iniciadas. A carga entregue não corresponde integralmente à programada.')
        for who in ('generator', 'observer'):
            instrument = summary.get('instrumentation', {}).get(who, {})
            if any(instrument.get(k, 0) >= 80 for k in ('cpu_p95_percent_of_limit', 'memory_max_percent_of_limit')):
                warnings.append(f'{variant}: {who} usou ≥80% de um limite. Investigue a interferência da instrumentação.')
    if any(cell == MISSING or cell == 'Sem observações' for r in rows for cell in (r['sync'], r['async'])):
        warnings.append('Há métricas indisponíveis/sem observações: não devem ser interpretadas como zero.')
    return {'kind': 'presentation_comparison_not_definitive', 'scenario': scenario, 'title': SCENARIOS[scenario],
            'dataset_id': values[0]['dataset_id'], 'rate': values[0]['rate'], 'measure_seconds': values[0]['measure_seconds'],
            'runs': {v: {'run_id': s['run_id'], 'evidence': s['_path']} for v, s in summaries.items()},
            'rows': rows, 'warnings': warnings}


def as_text(report):
    lines = [f"COMPARAÇÃO: {report['title']}", f"{report['rate']} eventos/s | {report['measure_seconds']} s medidos | DEMONSTRAÇÃO, NÃO DEFINITIVA", '',
             f"{'Métrica':54} | {'Síncrona':37} | Assíncrona", '-' * 132]
    group = None
    for row in report['rows']:
        if row['group'] != group:
            group = row['group']; lines.append(f'\n[{group}]')
        lines.append(f"{row['metric']:54} | {row['sync']:37} | {row['async']}")
    lines.extend(['', 'LEITURA CORRETA:'] + [f'- {w}' for w in report['warnings']])
    return '\n'.join(lines) + '\n'


def as_html(report):
    esc = html.escape
    body, group = [], None
    for row in report['rows']:
        if row['group'] != group:
            group = row['group'];body.append(f'<tr class="group"><th colspan="3">{esc(group)}</th></tr>')
        body.append(f'<tr><th scope="row">{esc(row["metric"])}</th><td>{esc(row["sync"])}</td><td>{esc(row["async"])}</td></tr>')
    warnings = ''.join(f'<li>{esc(w)}</li>' for w in report['warnings'])
    runs = ''.join(f'<li>{esc(v)}: {esc(s["run_id"])}<br><code>{esc(s["evidence"])}</code></li>' for v, s in report['runs'].items())
    return f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Comparação síncrona × assíncrona — TCC</title><style>
body{{font:18px/1.5 system-ui,sans-serif;color:#172b46;background:#f3f6fa;margin:0}}main{{max-width:1240px;margin:auto;padding:32px}}
h1{{font-size:32px;margin-bottom:6px}}.badge{{font-weight:700;color:#894300}}table{{border-collapse:collapse;width:100%;background:white;table-layout:fixed}}
th,td{{padding:12px 16px;border-bottom:1px solid #d9e2ee;text-align:left;overflow-wrap:anywhere}}thead{{position:sticky;top:0;background:#172b46;color:white}}thead th:first-child{{width:44%}}
tbody th{{font-weight:500}}.group th{{background:#e5edf7;font-weight:750}}code{{font-size:13px;overflow-wrap:anywhere}}li{{margin:12px 0}}button{{font:inherit;padding:8px 16px;cursor:pointer}}
@media(max-width:700px){{main{{padding:10px}}body{{font-size:14px}}th,td{{padding:8px}}h1{{font-size:24px}}}}@media print{{button{{display:none}}thead{{position:static}}}}
</style><main><p class="badge">DEMONSTRAÇÃO LOCAL • NÃO É RESULTADO DEFINITIVO</p>
<h1>Síncrona × assíncrona</h1><p>{esc(report['title'])} · {report['rate']} eventos/s · {report['measure_seconds']} s medidos por versão</p>
<p>Mesma configuração e conjunto determinístico; execuções sequenciais. Tempo HTTP e tempo até gravar são métricas distintas.</p>
<button onclick="window.print()">Imprimir / salvar PDF</button><p>p95: 95% das observações ficaram até esse tempo. Uma única execução não fornece uma conclusão estatística.</p>
<table><thead><tr><th>Métrica</th><th>Síncrona (201 após gravar)</th><th>Assíncrona (202 após Kafka)</th></tr></thead><tbody>{''.join(body)}</tbody></table>
<h2>Como interpretar</h2><ul>{warnings}</ul><h2>Rastreabilidade</h2><p>Dataset: <code>{esc(report['dataset_id'])}</code></p><ul>{runs}</ul></main></html>'''


def show_latest():
    pointer = read_json(RUNTIME / 'ultima-comparacao.json')
    folder = Path(pointer['folder']).resolve()
    if folder.parent != RUNTIME.resolve() or not folder.name.startswith('comparacao-'):
        raise ValueError('Ponteiro de comparação inválido')
    print((folder / 'comparacao.txt').read_text(encoding='utf-8'))
    print('Relatório HTML:', folder / 'relatorio.html')
    if shutil.which('wslpath'):
        converted = subprocess.run(['wslpath', '-w', str(folder / 'relatorio.html')], capture_output=True, text=True, check=False, timeout=3)
        if converted.returncode == 0:
            print('Abrir no navegador do Windows:', converted.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--scenario', choices=SCENARIOS)
    parser.add_argument('--sync', default='')
    parser.add_argument('--async', dest='async_path', default='')
    parser.add_argument('--latest', action='store_true')
    args = parser.parse_args()
    try:
        if args.latest:
            show_latest();return
        if args.output is None or args.scenario is None:
            raise ValueError('Informe pasta de saída e cenário')
        output = args.output.resolve()
        if output.parent != RUNTIME.resolve() or not output.is_dir() or not output.name.startswith('comparacao-'):
            raise ValueError('Saída deve ser a pasta única de comparação em .runtime/demonstracao')
        summaries = {v: validate(p, v, args.scenario) for v, p in [('sync', args.sync), ('async', args.async_path)] if p}
        report = build_report(summaries, args.scenario)
        for name, content in [('comparacao.json', json.dumps(report, ensure_ascii=False, indent=2) + '\n'),
                              ('comparacao.txt', as_text(report)), ('relatorio.html', as_html(report))]:
            with (output / name).open('x', encoding='utf-8') as stream:
                stream.write(content)
        pointer = RUNTIME / 'ultima-comparacao.json'
        temporary = pointer.with_suffix('.tmp')
        temporary.write_text(json.dumps({'folder': str(output)}), encoding='utf-8')
        temporary.replace(pointer)
        print(as_text(report))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f'Comparação não publicada: {error}\n')


if __name__ == '__main__':
    main()
