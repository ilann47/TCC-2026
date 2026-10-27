# Campanha definitiva R2/A1: resultados e auditoria final

Concluída em **27/10/2026 às 17h01 de Brasília** (`20:01:08Z`). São exatamente os **65 UUIDs planejados: 64 completos no critério original e um parcial sob A1**, sem UUID repetido/substituído, cinco tentativas em cada uma das treze condições, trinta pares e cinco casos de consumidor parado. O controlador encerrou e restaurou os cinco serviços interativos; não há nova medição a iniciar.

Os [dados públicos](resultados-a1/) e os capítulos 5/6 são a análise definitiva, distintos do piloto e das entregas históricas. A [entrega datada de 27/10](../../../../entregas/2026-10-27-entrega-04-java-final/README.md) reúne o PDF consolidado, apresentação final e roteiro, mantendo as limitações e a declaração de IA. Isso é fechamento técnico do documento e campanha, não confirmação de aprovação institucional ou submissão ao portal.

## Integridade e proveniência

- União dos 65 UUIDs do plano, sem duplicatas/interseção completa-parcial; datasets iguais dentro de cada par.
- **1.495 arquivos brutos verificados antes/depois** da leitura: 23 por execução. Os 65 pareceres recalculados são iguais aos gravados pelo controlador. Nenhum resumo ou veredito bruto foi alterado.
- 37 tentativas foram coletadas sob `f5d77b500ac9e1afe26d1d52068054e59a17f74d`; 28 sob `cb3e9b30e9d86ce4b288a6d8f0f917c4b342d409`, com os mesmos instrumentos, imagens, plano e parâmetros. O parecer formal intermediário é `effa20b9a1c9c597e1154d526e503715ad09876d`.
- [Catálogo final](resultados-a1/catalog.json): identidades, classificação, hashes dos resumos/pareceres/inventários, commit de coleta e hash do agregador executado. [SHA256SUMS](resultados-a1/SHA256SUMS) protege os arquivos publicados. Checksums detectam alteração, não são assinatura digital.
- A pasta `runs/` preserva os resumos byte a byte; `assessments/` contém a camada A1; `raw-checksums/` indexa os brutos locais; `manifests/` é projeção sanitizada, não cópia integral do manifesto privado. Brutos integrais, diário e logs permanecem localmente em `.runtime/`.
- R1 rejeitada, nove pilotos R2 e calibração de vinte coletas permanecem separados, sem somar suas amostras à campanha. A pausa operacional e a revisão A1 não autorizaram repetir referência ou substituir a 37ª.

## Unidade analítica e arquivos

O n é a execução/par, nunca o número de eventos. [per-run.csv](resultados-a1/per-run.csv) e `per-run.json` mostram as 65 repetições. `group-summary.json` oferece média, mediana, desvio-padrão amostral, extremos e valores individuais por indicador. `paired.json` contém as trinta diferenças assíncrona menos síncrona e sua dispersão; não há teste de significância, intervalo de confiança ou alegação de equivalência. `per-run-details.json` mantém distribuições dentro de cada execução, lotes de recursos, folga dos instrumentos e a prova temporal dos aceites durante consumidor parado.

HTTP principal: p95 nativo de respostas 201/202 válidas com UUID correto, calculado por execução usando posto mais próximo. Categorias de erro e carga efetiva são informadas à parte. Não se confunde essa medida com envio→retorno ou envio→commit. Médias dos p95 não são percentis de eventos agrupados.

CPU/memória de negócio somam amostras simultâneas: API+PostgreSQL na síncrona e API+consumidor+PostgreSQL+Kafka na assíncrona. Gerador e observador separados; 100% CPU equivale a uma CPU lógica. Amostras ausentes não são preenchidas com zero. Médias em falhas incluem períodos de componentes parados, não comprovam eficiência, energia, dinheiro ou esforço de manutenção.

## Principais achados (descritivos, configuração local)

- HTTP p95 assíncrono menor nos cinco pares das seis condições comparáveis; nas cinco condições sem falha, p95 de conclusão maior. A 48/s, média dos p95 HTTP: 2,60 ms assíncrono e 4,34 ms síncrono; conclusão: 5,83 e 3,92 ms.
- CPU/memória do caminho completo maiores na assíncrona em todos os pares. A 12/s: médias por execução de 15,36%/1.020,5 MiB contra 6,79%/231,0 MiB. Não é custo financeiro nem efeito universal de REST/EDA.
- Constantes: vazão concluída igual à taxa programada; rajada: 63,99444 eventos/s nas duas variantes. Sem erro HTTP medido nessas condições. Onze drops ocorreram **no aquecimento**, conforme pontos `dropped_iterations`/`scenario=warmup` de `c759cf5f-f17f-4a84-b516-95398ee10543`; não são perda de registros enviados nem drops da medição. A observação foi preservada sem reposição.
- Banco parado síncrono: 10.803 enviados, 8.351 aceitos, 8.352 persistidos e 2.452 respostas 503, incluindo uma persistida. Assim, 2.451 não aceitos ficaram fora do banco; nenhum aceite ficou sem destino.
- Banco parado assíncrono: 10.804 aceitos, 10.790 persistidos e 14 na DLQ (3/3/3/3/2). HTTP 202 não assegurou persistência. DLQ é destino terminal não persistido, sem replay automático, não desaparecimento.
- Consumidor parado: todos os 10.801 aceitos foram persistidos, sem DLQ. Em cada bloco, 558/541/540/549/558 aceites ocorridos entre confirmação de parada e conclusão do comando de retomada foram encontrados no banco com commit observado depois da retomada.
- Nenhum UUID duplicado no banco, divergência de conteúdo/hash, pendência retida final ou aceite sem destino conciliado entre os eventos medidos. Isso não testa todos os modos de perda física ou garante exatamente uma entrega em qualquer cenário.

## Recuperação: resultado desfavorável preservado e construto

Critério congelado: três janelas completas consecutivas de 10 s após retomada, dentro da entrada ativa, ≥90% da taxa alvo concluída, sem erro HTTP, limite de aceites sem commit e observação fresca/saudável. Foi observado em 5/5 síncronas, 5/5 consumidor parado e **1/5 banco parado assíncrono**. Os outros quatro não foram aprovados pelo primeiro commit, lag final ou drenagem.

O critério implementado em `Instrumentation.stableRecovery` conta também os aceites terminais em DLQ como aceites sem commit. A 12/s, seu limite é dois; as três mensagens em DLQ nos primeiros quatro blocos, sozinhas, já impedem satisfazê-lo. Isso limita o construto: não prova indisponibilidade contínua do serviço. Preserva-se o resultado global congelado; subtrair DLQ para aprovar retrospectivamente seria outro critério, não uma correção neutra.

Primeiro commit observado, persistência integral do backlog e confirmação sustentada são marcos diferentes. Backlog do consumidor foi integralmente persistido em 5/5 (12,55–24,16 s após comando de retomada); o banco assíncrono não teve persistência integral dos aceites anteriores por causa da DLQ. Não imputar zero aos tempos ausentes nem calcular média de recuperação somente dos observados como se fossem todos os cinco. A parada solicitada foi 40 s; intervalo observado entre confirmação de parada e fim do comando de retomada foi 40,65–41,11 s no banco e 45,02–46,52 s no consumidor.

## A1 e sensibilidades

A coleta `8733a7d2-89b5-4a5e-be22-0e4ed6e6b29b` continua `instrument_valid=false`. HTTP/persistência final/recursos auditados são elegíveis. A comparação primária de conclusão exclui essa execução **e sua contraparte do bloco 3**: quatro pares completos nessa condição, sem reposição. HTTP 503 continua erro mesmo persistido.

Há 1.666 tempos observados para 1.667 persistidos nessa coleta. A distribuição parcial em `partial-latency-sensitivity.json` não corrige nem presume aleatoriedade da ausência. Vazão parcial `[1666/180,1667/180]`, isto é, `[9,25556;9,26111]`/s; média dos limites da condição síncrona `[9,27556;9,27667]`/s. São limites contábeis, não intervalo de confiança. Drenagem não infla a janela.

`strict-sensitivity.json` preserva a análise estrita com exclusão do par afetado de todos os indicadores. Valores individuais e n estão explícitos. A A1 é pós-hoc nas primeiras 37 tentativas e declarada antes das últimas 28, não predeclarada desde o início. Não se inventa timestamp de commit com `persisted_at`, resposta HTTP ou retomada.

## Reprodução offline, sem nova carga

Dentro de `implementacao-java`, após encerrar a medição:

```bash
python3 -m unittest discover -s experimento/tests -p 'test_*.py'
python3 experimento/finalize_reduced_a1.py --output .runtime/reduzida65-2026-10-27-r2/nova-auditoria-final
python3 experimento/render_final_tables.py --data experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1 --tex ../projeto-latex-java/Capitulos
```

O finalizador requer a sessão concluída, o conjunto bruto local e imagens ainda disponíveis para conferir fingerprints, não inicia carga e recusa sobrescrever seu destino. O renderizador verifica os hashes públicos e reproduz seis tabelas do capítulo 5. O verificador `verify_final_results.py` confere o conjunto público sem exigir os brutos. Não executar comandos de lançamento: todos os UUIDs já foram usados.

Limitações: um computador, um broker/partição/réplica, dados sintéticos, janela finita, relógios de parede, telemetria, cinco tentativas, pausas documentadas e emenda pós-hoc. Nenhuma medição de dinheiro/manutenção, durabilidade sob perda da máquina ou significância populacional.
