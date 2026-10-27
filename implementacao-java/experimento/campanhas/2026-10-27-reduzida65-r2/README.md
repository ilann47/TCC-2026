# Validação R2 e liberação da campanha reduzida

Em 27/10/2026, o piloto concluiu os nove casos predeclarados, mantendo a referência de **48 eventos/s**. O controlador auditou novamente as identidades, o checkout limpo de cada coleta, parâmetros, imagens, instrumentação e os checksums de **200 arquivos brutos** antes de publicar o [catálogo](pilot-catalog.json) e o [congelamento ativo](../../FROZEN-PROTOCOL.json), com `status=ready_for_definitive_runs`.

**Esses nove casos são validação/calibração, não as 65 repetições definitivas.** O estado local de execução é consultado no WSL com `python3 experimento/reduced_campaign.py status`; este relatório registra a liberação, não prova por si só início ou término da campanha.

## O que mudou e o que foi preservado

A [R1 não elegível](../2026-10-26-reduzida65/PILOTO-REJEITADO.md) permanece publicada. A R2 substituiu somente a sonda administrativa Java periódica do broker experimental por conexão TCP leve. Criação de tópicos e verificação semântica da API permanecem antes da carga; imagens, quotas, código instrumentador, referência e critérios não foram relaxados. Isso remove a JVM da sonda da medição de recursos, mas não comprova que ela tenha sido a única causa do pico anterior.

A [política candidata](policy.json), o [plano de pilotos](pilot-plan.json), o [plano de 65](plan.csv) e a [análise predeclarada](ANALISE-PREDECLARADA.md) são preservados. `policy.json` conserva `status=pilot_pending` como registro anterior aos dados; o estado pronto pertence ao congelamento ativo e ao catálogo aprovado. Errata apenas de caminho: o campo descritivo `pilot_plan` herdado na política dizia `pilot-plan.csv`; o arquivo efetivamente executado sempre foi `pilot-plan.json`, identificado no controlador e preservado com os mesmos nove UUIDs. O campo foi corrigido no congelamento derivado, sem mudar a política candidata ou os ensaios.

A pausa operacional após os dois casos de modelo decorreu de edição documental e bloqueio temporário de commit, não de falha de referência. O diário local `operational-resume-audit.json` preserva a auditoria dos dois modelos e dos sete UUIDs ainda não iniciados; somente estes foram retomados. Nenhum ensaio de referência foi repetido para obter aprovação.

## Resultados do piloto (não comparações definitivas)

| Perfil / variante | Oferecidos | Aceites esperados | Salvos ao fim | DLQ terminal da carga | Aceites não conciliados |
|---|---:|---:|---:|---:|---:|
| Modelo / síncrona | 50 | 50 | 50 | 0 | 0 |
| Modelo / assíncrona | 50 | 50 | 50 | 0 | 0 |
| Referência 48/s / síncrona | 8.641 | 8.641 | 8.641 | 0 | 0 |
| Referência 48/s / assíncrona | 8.641 | 8.641 | 8.641 | 0 | 0 |
| Rajada 48→96→48 / síncrona | 11.519 | 11.519 | 11.519 | 0 | 0 |
| Rajada 48→96→48 / assíncrona | 11.519 | 11.519 | 11.519 | 0 | 0 |
| PostgreSQL parado / síncrona | 2.160 | 1.676 | 1.676 | 0 | 0 |
| PostgreSQL parado / assíncrona | 2.161 | 2.161 | 2.159 | 2 | 0 |
| Consumidor parado / assíncrona | 2.161 | 2.161 | 2.161 | 0 | 0 |

Todos os resumos têm `instrument_valid=true` e `issues=[]`. As 50 linhas de cada modelo têm os mesmos UUIDs, campos, payloads e hashes, excluindo apenas `persisted_at`, conforme [comparação independente](model-comparison.json). O teste de contrato separado confirmou reenvio igual (201/202) e conteúdo conflitante (409 síncrono; publicação 202 assíncrona seguida de tratamento de conflito). Os conflitos injetados após a carga funcional não integram as 50 amostras do resumo; os brutos preservam suas evidências.

Na referência assíncrona, o pico de aceites sem commit foi **10**, o lag máximo amostrado foi **2** e a inclinação da cauda foi **0,0001115 evento/s**. Respeitaram os limites de 12 e 0,01; não houve erro HTTP, drop ou pendência final. Na síncrona, o pico pós-aceite foi zero, o que não mede requisições em voo. A aprovação verifica a referência nesta configuração; não estima capacidade máxima nem confirma uma hipótese comparativa.

As falhas apresentaram recuperação operacional sustentada dentro da entrada ativa. O critério exige três janelas completas de dez segundos; os instantes abaixo incluem essa confirmação:

| Perfil / variante | Confirmação após comando de retomada |
|---|---:|
| PostgreSQL / síncrona | 38,936 s |
| PostgreSQL / assíncrona | 37,840 s |
| Consumidor / assíncrona | 34,539 s |

**Recuperação operacional não significa recuperação completa da persistência.** No PostgreSQL assíncrono, dois aceites terminaram na DLQ, e não no banco; não foram ocultados ou reclassificados como sucesso. Na síncrona, nem todos os eventos oferecidos obtiveram aceite. Erros previstos na indisponibilidade são resultados do sistema, não invalidade automática da instrumentação. Os valores acima são de um piloto por caso, não média de cinco repetições nem evidência de superioridade.

Nas sete coletas de carga, os máximos entre execuções do p95 de CPU do gerador/observador foram 13,63%/5,16% das quotas; os máximos de memória foram 23,37%/45,78% dos limites. São verificações de folga do instrumento, não consumo global do Windows ou custo da arquitetura. Os valores individuais permanecem nos resumos byte a byte em `pilot-runs/`, com SHA-256 no catálogo.

## Próxima etapa autorizada

Após revisar, testar, commitar e publicar esta liberação, executar exclusivamente os 65 UUIDs do plano, em cinco blocos, pelo controlador. Não mudar arquivos rastreados, reconstruir imagens, compilar o PDF ou rodar demonstrações durante a medição. Em falha de coleta ou instrumento, preservar a execução e investigar; não iniciar cópia concorrente, sobrescrever UUID ou trocar critérios silenciosamente. Ver [roteiro operacional](ACOMPANHAMENTO.md).

Os capítulos 5 e 6 só serão encerrados após a campanha e a análise por execução/par, sem pseudorreplicação. Continuam valendo as limitações de um computador, um broker/partição/réplica, dados sintéticos e cinco repetições.
