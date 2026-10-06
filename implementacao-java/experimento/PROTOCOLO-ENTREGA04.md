# Protocolo experimental — preparação da Entrega 04

Status: **instrumentos em validação; protocolo ainda não congelado**. Este arquivo não comprova execução da campanha definitiva. Os capítulos finais só podem incorporar resultados efetivamente reconciliados.

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

## Matriz planejada

| Identificação | Perfil | Variante | Finalidade |
|---|---|---|---|
| C1 / C2-25 | Chegada constante a 25% da referência | Ambas | Carga baixa; a mesma coleta atende aos dois objetivos, sem duplicar o tamanho amostral. |
| C2-50 / C2-75 / C2-100 | Taxas absolutas a 50%, 75% e 100% | Ambas | Carga crescente. |
| C3 | Referência → 2x referência → referência | Ambas | Rajada; duas transições de 1 s, delimitadas no script. |
| C4 / C5-PG | PostgreSQL interrompido durante entrada ativa e retomado | Ambas | Mesmo tipo de dependência indisponível e recuperação no mesmo ensaio. |
| C4 / C5-consumidor | Consumidor interrompido e retomado, Kafka/PG ativos | Apenas assíncrona | Acúmulo sem esgotar tentativas por indisponibilidade do banco. Não é par equivalente da falha de PG. |

Cada combinação terá **10 repetições**, com **60 s de aquecimento**, intervalo de até 12 s para conclusão das requisições de aquecimento e **300 s de medição**. A janela de drenagem é separada. Uma campanha com esta matriz totaliza **130 execuções**: 6 condições pareadas × 2 variantes × 10 + 1 condição assíncrona × 10. Somente aquecimento e medição somam 13 h; inicialização, exportação e drenagem aumentam esse tempo.

As repetições são unidades experimentais. Não transformar milhares de registros em milhares de amostras independentes. Ordem alternada das variantes em blocos com condições embaralhadas por semente registrada. Mesmo conteúdo por par. Os estados são reinicializados somente após exportar a coleta anterior.

## Métricas, conciliação e interpretação

- Tempo HTTP nativo do k6, envio → retorno instrumentado e envio → `commit_completed` são medidas distintas. A última usa relógios de parede entre processos; intervalos negativos invalidam a coleta, mas a ausência deles não prova perfeita sincronização.
- `commit_completed` é emitido após o retorno da transação. `persisted_at` pertence ao INSERT e não substitui o instante de confirmação.
- Throughput concluído: UUIDs únicos com commit dentro da janela de medição / 300 s. Linhas salvas depois pertencem à drenagem, não inflacionam o throughput da janela.
- HTTP esperado: 201 síncrono e 202 assíncrono. 503, timeout ou resposta sem o UUID são relatados por categoria. Um HTTP não confirmado pode coexistir com persistência e precisa de conciliação.
- Destinos finais: salvo, DLQ terminal, retido pendente ou aceite não conciliado. Kafka retém mensagens já processadas; presença no tópico isoladamente não é backlog. DLQ não é persistência no banco e não é desaparecimento da mensagem.
- Reenvio idempotente: múltiplos commits `duplicate` não são múltiplas linhas. Campos e hash são conferidos por encoder independente, específico do conjunto sintético.
- CPU e memória: amostragem Docker por contêiner (~3 s, horário no início do lote), no aquecimento e na medição. Zero durante parada é disponibilidade do processo, não eficiência. Amostras não medem o Windows inteiro, energia, custos de operação ou esforço de manutenção.
- Recuperação: separar primeiro commit após o comando de retomada, conclusão de todo o backlog aceito antes da retomada e estabilidade de throughput. O analisador inicial mede os dois primeiros; a estimativa de estabilidade permanece indisponível até validação do critério de janela móvel. Se eventos forem à DLQ, não alegar recuperação completa da persistência: não há reprocessamento automático.

Antes da campanha definitiva ainda devem ser validados: overhead do gerador, uso de recursos pelo gerador, série de backlog/lag durante a execução, critério de recuperação estável e agregação por repetição com dispersão. O executor impede chamar uma coleta de `definitive` sem protocolo congelado e checkout limpo; isso é uma proteção, não uma comprovação automática de validade científica.

## Descartes e conservação

Descartar com motivo explícito: falha de coleta/correlação, hash inconsistente, logs corrompidos, intervalos impossíveis, reinicialização externa ou configuração diferente da congelada. Não descartar um ensaio por refutar hipótese. Drops em sobrecarga são resultados a reportar, mas exigem cuidado porque a carga efetiva ficou menor que a prevista.

Cada pasta local contém manifesto, dados k6 comprimidos, eventos/recursos, banco, tópico, DLQ, lag final, logs do controlador/analisador e SHA256SUMS. Os dados brutos não são publicados indiscriminadamente no Git. O catálogo e os resumos identificam cada UUID e qualquer ensaio inválido. Entregas históricas não são reescritas.
