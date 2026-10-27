# A1: emenda analítica qualificada e retomada limitada

Em 27/10/2026, Ilan autorizou: **“Adotar a emenda qualificada e retomar após validação (recomendado)”**, em resposta à decisão que explicita a preservação da 37ª coleta como parcial, quatro pares completos para latência de conclusão nessa condição e retomada somente dos 28 UUIDs nunca iniciados.

Esta é uma **emenda analítica pós-início**, não uma nova tentativa de carga ou configuração de medição. A política original R2, seu plano de 65 UUIDs, referência 48/s, imagens, quotas, Compose, `run.sh`, `load.js` e Java instrumentador permanecem iguais. O [parecer anterior](../revisao-confirmacao-incerta/README.md) e seu `audit.json` são preservados, assim como o [protocolo/controlador originais](../../../protocolos/2026-10-27-r2-before-a1/). A imagem Java não é reconstruída.

## Regra e elegibilidade

A [política A1](policy.json) é aplicada igualmente aos definitivos. A revisão é retrospectiva nas 37 primeiras tentativas e declarada antes dos 28 UUIDs restantes. Sua motivação foi um resultado observado; não afirmar que essa exceção era predeclarada antes da campanha.

O escopo é conservador: somente `postgres-stop` síncrono, evento medido, HTTP 503, conteúdo correto no banco, cliente completo, um recebimento e uma falha `database_unavailable`, sem nenhum marco de confirmação, retry, replay ou DLQ, e sem outra questão instrumental. Casos assíncronos, aquecimento, outros perfis/códigos, sucesso sem marco, marco sem banco, conteúdo errado, relógio/coletor inválido ou margem insuficiente continuam bloqueados.

| Aspecto | Completa no critério original | Parcial sob A1 |
|---|---|---|
| `summary.json`, `instrument_valid`, `issues`, manifest, hashes | preservados | preservados, inclusive `false` e saída 2 |
| HTTP, persistência final, recursos | elegíveis | elegíveis após auditoria; 503 continua erro |
| Latência de conclusão primária | elegível | execução e contraparte excluídas desse indicador pareado |
| Latência parcial | observações conciliadas | somente sensibilidade, com cobertura observado/persistido e viés de ausência declarado |
| Vazão na janela | contagem observada / duração | limites `[c/T, (c+u)/T]`, sem preencher timestamp |
| Recuperação | marcos observados | marcos observados; não reconstruir o primeiro commit real desconhecido |

`c` é a quantidade de commits com marco conciliado dentro da janela; `u`, os registros medidos persistidos sem marco temporal; `T`, a duração de medição. O intervalo é sensibilidade contábil, não intervalo de confiança. Drenagem não aumenta a vazão da janela. `persisted_at`, horário de 503 e comando de retomada nunca substituem o commit ausente.

O [audit de adoção](adoption-audit.json) aplica a nova camada ao snapshot: nove pilotos íntegros, 36 definitivos completos, uma coleta parcial, zero resumos originais modificados e 28 UUIDs ainda não iniciados. Os 1.051 arquivos catalogados foram conferidos antes e depois da leitura. Os testes offline incluem rejeições e um fluxo simulado que prova 28 lançamentos, nenhuma repetição da 37ª e interrupção na primeira falha não coberta. Simulação não conta como ensaio real.

Não há novo piloto de carga: o ajuste é exclusivamente na análise offline e no controle de admissão. A calibração dos instrumentos de medição permanece a mesma. Isso não elimina a limitação metodológica da decisão pós-hoc.

Se as restantes tiverem cobertura completa, o catálogo final terá 65 UUIDs observados, **64 completos e um parcial**, não 65 válidos no critério original. Para latência de conclusão síncrona em `postgres-stop`, haverá quatro repetições/pares completos. Outras métricas identificadas poderão manter cinco observações. Novos casos parciais reduzem o n efetivo e serão relatados, não substituídos. Mostrar também a análise estrita original; não adicionar execuções até favorecer uma hipótese.

## Proveniência e controladores

`FROZEN-PROTOCOL.json` conserva todos os campos originais, exceto o hash do controlador, e acrescenta `analytical_amendment`: versão e hashes da política, camada Python, auditor independente, auditorias de base/adoção e arquivos originais preservados. Os verificadores Python/Node exigem essa igualdade e a integridade dos arquivos vinculados. O guard Java segue conferindo os mesmos parâmetros e fingerprints medidos.

A análise A1 grava pareceres derivados em `.runtime/reduzida65-2026-10-27-r2/assessments-a1/`, nunca na pasta bruta. Não há conversão de `instrument_valid=false` em `true`. `campaign_completed` continua contando apenas completas pelo critério original; `campaign_qualified` registra parciais separadamente; `campaign_accounted` é sua união sem duplicatas.

Somente o controlador, com lock exclusivo e preflight aprovado, cria `state-before-a1.json` byte a byte e avança o diário. A pasta existente da 37ª é auditada e contabilizada como parcial, sem chamar o gerador. O executor só recebe UUIDs sem pasta prévia; qualquer outra pasta não concluída provoca recusa. Uma nova interrupção não se torna automaticamente retomável pelo comando inicial A1.

## Liberação e execução

Dentro de `implementacao-java`, com a sessão parada:

```bash
# Só leituras e conferências; nunca envia carga nem altera o diário:
python3 -m unittest discover -s experimento/tests -p 'test_*.py'
node experimento/verify-frozen.mjs  # Node no Windows, se indisponível no WSL
python3 experimento/reduced_campaign.py audit-amendment
```

Depois de revisar/commitar/push e confirmar que o remoto é exatamente o HEAD publicado:

```bash
python3 experimento/check_reduced_plan.py experimento/campanhas/2026-10-27-reduzida65-r2/plan.csv
python3 experimento/reduced_campaign.py launch-reviewed-campaign
python3 experimento/reduced_campaign.py status
```

Não usar `launch-campaign`, `campaign`, `prepare`, `freeze` ou editar o JSON para contornar a recusa. O comando A1 exige o estado inicial auditado, os 36 UUIDs completos, a 37ª parcial conhecida, nenhuma pasta dos 28 posteriores, checkout limpo e HEAD igual a `origin/main`. O processo filho repete o preflight sob lock, antes de parar somente os contêineres interativos deste TCC. O início real só é confirmado quando houver controlador **e executor da 38ª coleta** ativos. A configuração `ready_for_definitive_runs` sozinha não libera retomada.

Durante a campanha, nenhuma edição rastreada, reconstrução, compilação de PDF ou demonstração. O monitor lê estado/logs e permanece silencioso enquanto normal. Ao final, auditar os 65 UUIDs, categorias e elegibilidade por métrica; finalizar capítulos 5/6, compilar e revisar o PDF, publicar e confirmar remoto. O TCC ainda não está finalizado por esta liberação.
