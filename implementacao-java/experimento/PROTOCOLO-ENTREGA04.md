# Protocolo experimental — campanha da Entrega 04

Revisão reduzida autorizada antes de qualquer execução definitiva: **65 execuções, cinco repetições por condição e 180 s de medição**. A [política V2](campanhas/2026-10-27-reduzida65-r2/policy.json), o [plano](campanhas/2026-10-27-reduzida65-r2/plan.csv) e a [análise predeclarada](campanhas/2026-10-27-reduzida65-r2/ANALISE-PREDECLARADA.md) foram registrados antes do novo piloto. As [nove validações R2](campanhas/2026-10-27-reduzida65-r2/README.md) foram aprovadas em 27/10/2026; o controlador revalidou identidades, configuração, integridade e hashes de 200 arquivos brutos e congelou `FROZEN-PROTOCOL.json` como `ready_for_definitive_runs`. A R1 foi rejeitada e preservada; o usuário decidiu manter 48/s e investigar. A R2 troca somente a sonda administrativa Java do Kafka por TCP leve no override experimental, mantendo criação de tópicos e prontidão da API antes da carga. A [V1 arquivada](protocolos/2026-10-26-v1-130/README.md) e o candidato R2 predeclarado não foram reescritos; seus estados históricos não substituem o estado do congelamento ativo. A campanha só deve iniciar após revisão, testes, commit e push da liberação, sem reclassificar o piloto como definitivo.

A [calibração original](calibracao/2026-10-26-529e0349/README.md) confirmou referência comum de 48 eventos/s, com instrumentos e imagens que não serão reconstruídos. O estado efetivo é consultado com `python3 experimento/reduced_campaign.py status`, no WSL. Capítulos finais só podem incorporar resultados efetivamente reconciliados; piloto e calibração não confirmam hipóteses comparativas.

## Escopo e instrumentos

As aplicações continuam em Java 21. k6 é um instrumento de carga escrito em JavaScript; não é uma terceira implementação do sistema. O analisador e a comparação do modelo são Java. A imagem k6 é fixada em 2.3.0 por digest. `compose.yml` cria um projeto independente, `tcc-entrega04`, sem portas públicas, com volumes distintos do ambiente interativo. Somente dados sintéticos desse projeto podem ser reinicializados.

O k6 controla a taxa de chegada, não espera a conclusão da requisição anterior para definir a taxa. `dropped_iterations` é relatado: significa que o gerador não iniciou toda a carga agendada, não que o sistema perdeu um registro. Não usar Swagger para obter as métricas experimentais.

## Quadro de decisão: JMeter e k6

| Critério | Apache JMeter | Grafana k6 | Decisão neste trabalho |
|---|---|---|---|
| Plano de teste | Plano JMX, preparado em interface gráfica e configurável por propriedades | Cenários e funções em JavaScript | k6 facilita revisar a geração determinística de UUIDs e registrar o script no Git. |
| Execução de carga | Modo CLI recomendado; listeners gráficos aumentam o consumo | Modo CLI e imagem Docker | Ambas atendem; não se trata de comparação de desempenho entre ferramentas. |
| Modelo de chegada | Possui Open Model Thread Group, documentado como experimental | Executors constant/ramping-arrival-rate | k6 integra diretamente a taxa de chegada adotada no protocolo. |
| Evidências | JTL/CSV; documentação recomenda salvar somente o necessário | JSONL, inclusive comprimido, com tags por amostra | O analisador Java já concilia as tags do k6 com os marcos de commit. |

Fontes técnicas oficiais, consultadas em 06/10/2026: [JMeter — boas práticas](https://jmeter.apache.org/usermanual/best-practices.html), [JMeter — componentes](https://jmeter.apache.org/usermanual/component_reference.html#Open_Model_Thread_Group), [k6 — chegada constante](https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/), [k6 — cenários](https://grafana.com/docs/k6/latest/using-k6/scenarios/), [k6 — JSON](https://grafana.com/docs/k6/latest/results-output/real-time/json/). São documentação de ferramentas, não novos artigos científicos nem livros do referencial teórico.

## Conjunto de dados e validação funcional

O `dataset_id` identifica o mesmo conteúdo nas duas variantes; o `run_id`, diferente por execução, fica no cabeçalho HTTP/metadados Kafka, fora do hash. UUID, instante de ocorrência, campos e payload derivam do conjunto e da iteração, não do relógio de envio.

O perfil `model` envia **exatamente 50 registros** a cada variante. O comparador exige igualdade de UUIDs, campos, payload e SHA-256, desconsiderando apenas `persisted_at`, pois as inserções ocorrem em momentos diferentes. Em seguida, reenvia um UUID com conteúdo igual e depois com conteúdo diferente. O banco deve continuar contendo 50 linhas. Na versão síncrona, o conteúdo divergente deve resultar em 409; na assíncrona, 202 confirma publicação e o consumidor deve encaminhar o conflito à DLQ. A confirmação no banco e na DLQ precisa ser conferida, não inferida do HTTP.

`validate.sh` executa ensaios curtos de modelo, rajada, banco parado nas duas variantes e consumidor parado apenas na assíncrona. **Nenhum deles conta como repetição definitiva.**

## Calibração e congelamento

1. Verificar as aplicações, a integridade da coleta, os relógios dos contêineres e a ausência de reinicialização externa.
2. Explorar taxas progressivas nas duas variantes. Confirmar uma taxa comum por 300 s, após aquecimento de 60 s. A referência é uma taxa estável observada, não uma estimativa universal de capacidade máxima.
3. Exigir zero iterações não iniciadas, nenhuma resposta inválida em condição normal e conciliação de todo o conjunto aceito. Examinar contagens de commit em janelas de 10 s e pendências no decorrer do tempo; o encerramento sem pendências sozinho não prova estabilidade durante a carga.
4. Fixar taxa absoluta, arredondamentos, VUs, tempos, parâmetros de falha, prazo de drenagem, ordem, critérios de descarte e versões no arquivo `FROZEN-PROTOCOL.json`. Registrar o commit e o hash do plano. Não criar esse arquivo como se já estivesse aprovado enquanto a calibração permanecer incompleta.

Os recursos do computador e os contêineres concorrentes são registrados. Não parar aplicativos/projetos alheios ao TCC sem autorização. Havendo atividade concorrente relevante, registrar a interferência e repetir, em vez de selecionar somente o resultado favorável.

A política de seleção foi registrada antes dos dados: exploração em 10/25/50/100 eventos/s, escolha comum conservadora e arredondamento para múltiplo de quatro. Ambas passaram em 50; 100 não foi elegível. Os drops em 100 ocorreram no aquecimento, não são perda de registros enviados nem demonstração da capacidade máxima da API. A candidata 48 foi confirmada nas duas variantes em 60 s de aquecimento + 300 s de medição. Dois blocos de controle por variante inverteram a ordem de coleta reduzida/completa. Os números, alertas de cardinalidade e tentativas rejeitadas estão no relatório.

Critérios de referência: zero erros/drops/DLQ/pendências finais; pelo menos 95% da taxa em conclusões na janela e 90% em cada janela de dez segundos; fila máxima <=max(5,ceil(taxa×0,25)), crescimento de cauda <=0,01 evento/s; gerador com CPU p95 <=70% da quota e memória máxima <=75% do limite; observador <=80%/85%, com p95 de intervalo <=2,5 s. São margens de engenharia predefinidas, não constantes universais ou teste de equivalência. Ambos os modos de controle usam o mesmo estimador HTTP nativo do k6.

O gerador recebe 2 CPUs/2 GiB e o observador 0,25 CPU/256 MiB. O executor confere hashes do plano/Compose e, antes de tocar o estado experimental, confere imagens, código instrumentador e parâmetros congelados. Exige checkout limpo. A campanha para se a coleta falhar ou se gerador/observador não tiverem a folga prevista, preservando a execução para investigação. Isso não autoriza descartar resultados por contrariar hipóteses.

## Matriz congelada

| Identificação | Perfil | Variante | Finalidade |
|---|---|---|---|
| C1 / C2-25 | 12 eventos/s | Ambas | Carga baixa; a mesma coleta atende aos dois objetivos, sem duplicar o tamanho amostral. |
| C2-50 / C2-75 / C2-100 | 24, 36 e 48 eventos/s | Ambas | Carga crescente, com taxas absolutas comuns. |
| C3 | 48 → 96 → 48 eventos/s | Ambas | Rajada; duas transições de 1 s, delimitadas no script. |
| C4 / C5-PG | 12 eventos/s; PostgreSQL interrompido por 40 s e retomado | Ambas | Mesma dependência indisponível, comando por volta dos 60 s de medição; instantes efetivos registrados. |
| C4 / C5-consumidor | 12 eventos/s; consumidor interrompido por 40 s e retomado | Apenas assíncrona | Kafka/PG ativos. Não é par equivalente da falha de PG. |

Cada combinação terá **5 repetições**, com **60 s de aquecimento**, intervalo de 12 s para conclusão das requisições de aquecimento e **180 s de medição**. A janela de drenagem é separada, de 90 s. A matriz totaliza **65 execuções**: 6 condições pareadas × 2 variantes × 5 + 1 condição assíncrona × 5. Os tempos configurados somam 6 h 10 min 30 s, sem inicialização, exportação, análise ou o piloto adicional. O prazo real será maior; a redução não preserva automaticamente a precisão/poder estatístico do plano anterior.

As repetições são unidades experimentais. Não transformar milhares de registros em milhares de amostras independentes. São cinco blocos completos com condições embaralhadas por semente registrada e mesmo conteúdo por par. A primeira variante é contrabalançada em 3/2 ou 2/3 por condição pareada e 15/15 globalmente. Os estados são reinicializados somente após exportar a coleta anterior. Mostrar valores por repetição, média, mediana, dispersão, extremos e diferenças pareadas, sem afirmar significância/ equivalência estatística não demonstrada. Resultados mistos permanecerão inconclusivos.

VUs: 128 nas cargas normais e 176 nas falhas, acomodando o timeout HTTP de 10 s à taxa comum de 12/s. Drenagem: 90 s. O reset é lógico: tabela sintética reinicializada, tópico/grupo novos; broker, tópicos anteriores, volumes e caches não são zerados. Preserve o ambiente medido, sem reconstruir imagens; mudanças relevantes exigem nova calibração.

## Métricas, conciliação e interpretação

- Tempo HTTP nativo do k6, envio → retorno instrumentado e envio → `commit_completed` são medidas distintas. A última usa relógios de parede entre processos; intervalos negativos invalidam a coleta, mas a ausência deles não prova perfeita sincronização.
- `commit_completed` é emitido após o retorno da transação. `persisted_at` pertence ao INSERT e não substitui o instante de confirmação.
- Throughput concluído: UUIDs únicos com commit dentro da janela de medição / 180 s na R2 (300 s apenas nas confirmações originais de calibração). Linhas salvas depois pertencem à drenagem, não inflacionam o throughput da janela.
- HTTP esperado: 201 síncrono e 202 assíncrono. 503, timeout ou resposta sem o UUID são relatados por categoria. Um HTTP não confirmado pode coexistir com persistência e precisa de conciliação.
- Destinos finais: salvo, DLQ terminal, retido pendente ou aceite não conciliado. Kafka retém mensagens já processadas; presença no tópico isoladamente não é backlog. DLQ não é persistência no banco e não é desaparecimento da mensagem.
- Reenvio idempotente: múltiplos commits `duplicate` não são múltiplas linhas. Campos e hash são conferidos por encoder independente, específico do conjunto sintético.
- CPU e memória: Docker por contêiner (~3 s, início/fim de lote preservados), incluindo gerador e observador. CPU também normalizada pela quota. O CLI exibiu zero para contêineres parados: médias em falhas misturam períodos ativos e indisponíveis, não demonstram eficiência. Não medem Windows inteiro, energia, custos de operação ou esforço de manutenção.
- Série temporal: observação SQL/Kafka aproximadamente a cada segundo, mais `timeline.csv` dos aceites sem commit. Lag e pendência pós-aceite não equivalem a requisições HTTP em voo: na síncrona o sucesso já ocorre depois do commit. O observador SQL/Kafka não captura instantes físicos de commit e seus snapshots não são atômicos entre sistemas.
- Recuperação: separar primeiro commit, conclusão de todo o backlog aceito antes da retomada e estabilidade operacional. A última exige três janelas completas consecutivas de 10 s, após a retomada, com entrada ativa, >=90% da taxa alvo em commits únicos, zero erros HTTP, pendências/lag <=max(2,ceil(taxa×0,1)) e observação saudável com idade <=3 s. O resumo informa início retrospectivo e instante de confirmação, que inclui os 30 s. O critério foi validado com consumidor e PostgreSQL interrompidos. Se eventos forem à DLQ, não alegar recuperação completa da persistência: não há reprocessamento automático.

A calibração validou cobertura dos instrumentos, recursos do gerador, série temporal, critério de recuperação sustentada e triagem de interferência da coleta. Permanecem pendentes a execução definitiva e sua agregação por repetição com dispersão. O protocolo congelado e o checkout limpo são proteções, não comprovação automática de validade científica. O overhead não é zero: as comparações avaliam estes protótipos instrumentados, neste computador, com Kafka de uma partição/réplica e dados sintéticos.

## Descartes e conservação

Descartar com motivo explícito: falha de coleta/correlação, hash inconsistente, logs corrompidos, intervalos impossíveis, reinicialização externa ou configuração diferente da congelada. Não descartar um ensaio por refutar hipótese. Drops em sobrecarga são resultados a reportar, mas exigem cuidado porque a carga efetiva ficou menor que a prevista.

Cada pasta local contém manifesto, dados k6 comprimidos, eventos/recursos, banco, tópico, DLQ, lag final, logs do controlador/analisador e SHA256SUMS. Os dados brutos não são publicados indiscriminadamente no Git. O catálogo e os resumos identificam cada UUID e qualquer ensaio inválido. Entregas históricas não são reescritas.
