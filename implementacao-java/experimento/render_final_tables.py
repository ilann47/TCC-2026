"""Render descriptive thesis tables from the audited R2/A1 publication dataset."""
import argparse
import json
from pathlib import Path
import review_commit_uncertainty as review


def read(root, name): return json.loads((root / name).read_text(encoding='utf-8'))
def number(value, digits=2): return '--' if value is None else f'{value:.{digits}f}'.replace('.', ',')
def ms(stat, digits=2):
    if not stat['n']: return '--'
    return number(stat['mean'], digits) + (r' $\pm$ ' + number(stat['sd_sample'], digits) if stat['sd_sample'] is not None else '')
def condition(row):
    return {'steady': f"Constante {row['rate']}/s", 'burst': 'Rajada', 'postgres-stop': 'Banco parado', 'consumer-stop': 'Consumidor parado'}[row['profile']]
def variant(row): return 'S' if row['variant'] == 'sync' else 'A'
def order(row): return ({'steady': 0, 'burst': 1, 'postgres-stop': 2, 'consumer-stop': 3}[row['profile']], row['rate'], row.get('variant') != 'sync')


def table(caption, label, headers, rows, note):
    cols = 'l' + 'r' * (len(headers) - 1)
    return '\n'.join([r'\begin{table}[htbp]', r'\centering', r'\caption{' + caption + '}', r'\label{' + label + '}',
                      r'\small', r'\setlength{\tabcolsep}{4pt}', r'\begin{tabular}{' + cols + '}', r'\hline',
                      ' & '.join(headers) + r' \\ \hline', *[' & '.join(map(str, row)) + r' \\' for row in rows],
                      r'\hline', r'\end{tabular}', r'\fonte{Elaborado pelo autor a partir da campanha R2/A1 de 27/10/2026.}',
                      r'\vspace{0.2cm}', r'\begin{minipage}{\textwidth}', r'\footnotesize', note,
                      r'\end{minipage}', r'\end{table}', ''])


def render(root, destination):
    catalog = read(root, 'catalog.json')
    review.require(catalog['planned_runs'] == 65 and catalog['complete_original_evidence'] == 64 and catalog['partial_commit_timing'] == 1, 'unexpected campaign shape')
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        file = (root / name).resolve()
        review.require(root.resolve() in file.parents and review.sha(file) == digest, 'publication checksum mismatch')
    groups = sorted(read(root, 'group-summary.json'), key=order)
    pairs = sorted(read(root, 'paired.json'), key=order)
    texts = {}
    texts['latencia'] = table('Latência: média e desvio-padrão dos p95 de cada execução, em ms', 'tab:final-latencia',
          ['Condição', 'Var.', r'$n_H$', 'HTTP válido', r'$n_C$', r'Envio $\rightarrow$ commit'],
          [[condition(g), variant(g), g['metrics']['http_success_p95_ms']['n'], ms(g['metrics']['http_success_p95_ms']), g['metrics']['commit_p95_ms']['n'], ms(g['metrics']['commit_p95_ms'])] for g in groups],
          r'S: síncrona; A: assíncrona. $n_H$ e $n_C$ contam execuções, não eventos. HTTP inclui somente 201/202 com UUID correto. A latência de conclusão usa apenas marcos conciliados; o par do bloco 3 com banco parado é excluído de ambas as variantes nesse indicador. Média de p95 não é o p95 de eventos agrupados.')
    texts['vazao'] = table('Vazão concluída na janela e erros HTTP por execução', 'tab:final-vazao',
          ['Condição', 'Var.', 'Vazão média (eventos/s)', r'Erro HTTP (\%)'],
          [[condition(g), variant(g), (r'[' + number(g['metrics']['throughput_lower']['mean'], 5) + '; ' + number(g['metrics']['throughput_upper']['mean'], 5) + ']' if g['metrics']['throughput_lower']['mean'] != g['metrics']['throughput_upper']['mean'] else ms(g['metrics']['throughput_lower'], 5)), ms(g['metrics']['http_error_percent'])] for g in groups],
          r'$n=5$ em todas as linhas. Valores pontuais mostram média $\pm$ desvio-padrão entre execuções; a única linha intervalar mostra médias dos limites inferior/superior, não intervalo de confiança. Os limites e a dispersão individuais estão no catálogo. Drenagem não amplia os 180 s. Ausência de diferença de vazão nesta carga não estabelece equivalência de capacidade.')
    texts['destinos'] = table('Destinos ao fim da observação: totais das cinco tentativas por condição', 'tab:final-destinos',
          ['Condição', 'Var.', 'Enviados', 'Aceitos', 'Banco', 'DLQ', 'Não banco'],
          [[condition(g), variant(g), *[g['totals'][k] for k in ['offered', 'accepted', 'stored_final', 'dlq_terminal', 'nonpersisted_final']]] for g in groups],
          r'Não banco é enviado menos persistido, e não sinônimo de perda. No banco parado síncrono, 2452 respostas foram 503; uma delas corresponde a registro persistido, sem marco temporal. Restam 2451 enviados não aceitos e não persistidos. Na assíncrona, os 14 aceitos não persistidos terminaram em DLQ. Em todas as linhas: pendência retida final, aceites sem destino conciliado, UUIDs duplicados no banco e divergências de conteúdo/hash iguais a zero.')
    texts['recursos'] = table('Recursos do caminho de processamento: média e desvio-padrão das médias por execução', 'tab:final-recursos',
          ['Condição', 'Var.', r'CPU (\%)', 'Memória (MiB)'],
          [[condition(g), variant(g), ms(g['metrics']['business_cpu_mean_percent']), ms(g['metrics']['business_memory_mean_mib'], 1)] for g in groups],
          r'$n=5$. Somam-se amostras simultâneas de API e PostgreSQL na síncrona; API, consumidor, PostgreSQL e Kafka na assíncrona. Gerador e observador são separados. 100\% de CPU corresponde a uma CPU lógica, não ao host inteiro. São médias aritméticas das amostras; componentes parados e o custo da telemetria limitam a interpretação, sem provar custo financeiro ou eficiência por trabalho realizado.')
    faults = [g for g in groups if 'stop' in g['profile']]
    texts['recuperacao'] = table('Recuperação observada após o comando de retomada, em segundos', 'tab:final-recuperacao',
          ['Condição', 'Var.', 'Primeiro commit', 'Estável: $n/5$', 'Confirmação', 'Backlog completo'],
          [[condition(g), variant(g), ms(g['metrics']['first_commit_after_restore_s']), str(g['stable_recovery_observed_n']) + '/5', ms(g['metrics']['stable_recovery_confirmed_s']), ms(g['metrics']['backlog_recovery_s'])] for g in faults],
          r'Primeiro commit: primeiro marco observado, não prova de primeiro commit real. Confirmação exige três janelas completas de 10 s sob entrada ativa. Média/desvio são condicionados aos casos observados: banco síncrono $n=5$, banco assíncrono $n=1$, consumidor $n=5$. Não se preenchem tempos nos quatro casos assíncronos sem sequência qualificante. Backlog síncrono não se aplica (zero aceites pendentes na retomada); no banco assíncrono, não houve persistência integral dos aceites anteriores por haver DLQ; consumidor teve backlog integralmente persistido em cinco casos.')
    texts['pares'] = table('Diferenças pareadas do p95 HTTP: assíncrona menos síncrona, em ms', 'tab:final-pares',
          ['Condição', 'Bloco 1', 'Bloco 2', 'Bloco 3', 'Bloco 4', 'Bloco 5'],
          [[condition(p), *[number(r['differences_async_minus_sync']['http_success_p95_ms']) for r in p['pairs']]] for p in pairs],
          r'Cada coluna é um par com o mesmo dataset, não uma amostra de evento. Diferenças negativas indicam menor p95 HTTP da assíncrona nestes cinco pares. Não se aplica teste de significância; todas as diferenças, dispersões e diferenças de conclusão/recursos constam de \texttt{paired.json}. Não existe par síncrono para consumidor parado.')
    destination.mkdir(exist_ok=True)
    for name, content in texts.items():
        (destination / ('resultados-' + name + '.tex')).write_text('% Generated by experimento/render_final_tables.py from audited R2/A1 data.\n' + content, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--tex', type=Path, required=True)
    args = parser.parse_args()
    render(args.data.resolve(), args.tex.resolve())
