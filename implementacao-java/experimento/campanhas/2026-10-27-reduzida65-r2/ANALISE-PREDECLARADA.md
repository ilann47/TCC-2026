# Plano de análise antes da coleta definitiva

**Proveniência:** este plano foi registrado antes das coletas. Após observar a 37ª tentativa, o usuário autorizou a [emenda analítica A1](emenda-a1/README.md). Ela mantém o texto original arquivado, o veredito bruto e a análise estrita, mas acrescenta elegibilidade por métrica para confirmação incerta: sem timestamp imputado, latência primária exclui a execução parcial e seu par, vazão apresenta limites e n efetivo é explícito. A1 é retrospectiva nas primeiras 37 e declarada antes das 28 restantes; não alegar que a exceção abaixo estava prevista desde o início.

Esta revisão é um experimento local de comparação com orçamento de cinco repetições por condição, não um estudo dimensionado por poder estatístico. Os resultados só permitem conclusões delimitadas ao ambiente e às implementações medidas. Não há autorização para repetir até uma hipótese vencer, trocar métricas após observar qual favorece uma variante ou tratar eventos correlacionados como repetições independentes.

## Unidades e apresentação

- Unidade experimental: uma execução completa. Unidade de comparação: um par do mesmo bloco, condição, taxa e dataset. Consumidor parado tem cinco execuções assíncronas sem par síncrono fictício.
- Publicar os cinco valores por condição/variante; resumir por média, mediana, desvio-padrão amostral, mínimo e máximo. Mostrar diferenças pareadas e sua dispersão; não concatenar todos os eventos como se o tamanho amostral experimental fosse seu número.
- HTTP de todas as respostas e HTTP dos aceites válidos são estimandos distintos. O segundo será calculado com `events.csv`, somente `phase=measure`, código 201/202 esperado e UUID correspondente, e usado para discutir latência de aceitação. Sempre mostrar quantidade de observações/exclusões e erros; respostas de erro rápidas não devem virar vantagem de aceitação.
- Tempo envio→commit: somente commits conciliados com linhas exportadas; apresentar amostras e destinos dos não persistidos. Não atribuir zero a evento sem commit.
- Throughput: commits únicos na janela / 180 s. Contagem final/drenagem será mostrada separadamente.
- CPU/memória: mesmas definições do comparador; totais do caminho de negócio e componentes separados. k6/observador fora do total. Em falha, médias incluem períodos indisponíveis e não representam eficiência condicionada ao processo ativo.
- Recuperação: primeiro commit, persistência de todo backlog aceito antes da retomada e confirmação de três janelas saudáveis. Se não observada, registrar censura/falta de observação na janela; não substituir por zero, média de só sucessos sem declarar ou duração artificial igual ao fim do teste. Informar quantas recuperações foram observadas em cinco.
- Intervalos de confiança/testes populacionais não serão apresentados sem pressupostos justificáveis. Com n=5 e um computador, não afirmar superioridade estatística geral ou equivalência pela ausência de significância. Diferenças absolutas e razões descritivas podem ser apresentadas com denominador e dispersão explícitos.

## Expectativas do texto e decisões descritivas

Para indicadores quantitativos pareados, direção consistente nas cinco diferenças dá respaldo **descritivo naquela condição**, não prova populacional. Direção contrária consistente contradiz a expectativa naquele recorte; sinais mistos/empates/observações insuficientes são inconclusivos. A classificação deve informar condição, indicador e escopo, nunca produzir um vencedor global por contagem de métricas.

| Expectativa original | Indicador/critério observável |
|---|---|
| Menor custo básico síncrono em carga baixa | CPU e memória médias do caminho completo em steady 12/s, diferenças pareadas das cinco execuções. Não extrapolar para custo financeiro. Se CPU e memória apontarem sentidos diferentes, explicitar o trade-off. |
| Menor complexidade síncrona | Descrever componentes, dependências e fluxo. Esforço de manutenção/implantação não foi medido; essa parte não será declarada comprovada quantitativamente. |
| Menor latência de aceitação assíncrona | p95 HTTP dos aceites válidos como indicador primário, por condição pareada; média/mediana/p99 e todos os erros também reportados. Não interpretar como menor tempo até gravação e não ocultar mudança na população de sucessos durante falha. |
| Retenção durante indisponibilidade do consumidor | Em cada consumer-stop, relacionar confirmações durante a pausa às evidências Kafka, banco final e DLQ. Retenção com persistência posterior só é observada se esses destinos forem conciliados; Kafka ativo e 202 não bastam. |
| Maior consumo assíncrono | CPU/memória médias do caminho completo por condição e par, com os quatro componentes assíncronos discriminados. Não atribuir exclusivamente ao conceito de EDA o custo dos componentes adicionais. |
| Distinção entre aceite e conclusão | Apresentar distribuições separadas e, quando útil, diferenças por evento com ambos os marcos. Commit pode preceder a chegada do 202 ao cliente; isso é válido e não deve ser removido. A API não aguardar commit é propriedade do fluxo, não uma promessa de atraso positivo em todo evento. |

## Integridade, falhas e honestidade da amostra

Manter todos os 65 resultados previstos, inclusive 503, timeout, drops, DLQ e recuperação não observada. Descartes apenas por critérios instrumentais predeclarados, preservando pasta, motivo e identificação de qualquer substituição revisada. Nenhuma substituição automática é autorizada pelo controlador.

Contar separadamente não persistência final, pendência retida, DLQ e aceite sem destino conciliado. DLQ não desapareceu, mas também não foi salvo no banco; não escrever “sem perda” para esconder não persistência. Ausência de evidência exige investigação, não atribuição automática ao Kafka. Duplicidade no banco e reentrega são medidas diferentes.

As hipóteses serão tratadas como confirmadas/refutadas **nas observações delimitadas**, ou inconclusivas, com essa qualificação explícita. O Capítulo 6 apenas resume o que foi demonstrado no 5; não acrescenta métricas, resultados ou recomendações para cargas/falhas que não foram medidas.
