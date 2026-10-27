# Piloto R1: referência não elegível; não é resultado definitivo

O controlador parou antes de liberar a campanha. As duas verificações de modelo concluíram 50 registros cada, com hash correspondente, reenvio idempotente e conflito preservando a linha original; a comparação final conjunta do lote de nove não foi executada porque a etapa de referência falhou antes.

Execução `bedbd896-c279-475a-94f1-712c88b7f904-async`, steady 48/s, 60 s de aquecimento, 180 s medidos, 90 s de observação. O [resumo original](rejected-runs/bedbd896-c279-475a-94f1-712c88b7f904-async.json) é preservado sem alterações. A instrumentação foi íntegra; o que falhou foi a elegibilidade da referência nesta configuração/execução.

| Resultado | Observado | Critério anterior |
|---|---:|---:|
| Enviados/aceitos/gravados ao fim | 8.641 / 8.641 / 8.641 | Todos conciliados |
| Gravados dentro da janela | 8.619 | Pelo menos 95% da taxa-alvo |
| HTTP/contrato, drops, DLQ, pendentes finais | 0 | 0 |
| Pico de aceitos ainda não gravados | 21 | Até 12 |
| Pico amostrado de lag | 15 | Até 12 |
| Inclinação da pendência no trecho final | 0,016260551 evento/s | Até 0,01 |
| Maior envio→commit | 453,54 ms | Não é um limite isolado de aceitação |

O acúmulo de 19 pendências na fronteira de 180 s pesou no indicador de cauda. O ensaio não demonstra crescimento permanente de fila nem perda de mensagens: todos foram gravados ao fim. Tampouco permite ignorar os critérios porque o resultado final foi completo.

## Investigação, sem alteração retrospectiva

O Kafka estava limitado a uma CPU e 1 GiB. Sua sonda de saúde executava `kafka-topics.sh --list` a cada dez segundos, iniciando uma JVM administrativa dentro do contêiner medido. Amostras mostraram picos próximos de 100% e aumento de memória também na drenagem, sem carga. O histórico final da sonda registra execuções de aproximadamente 2,6 s e duas finalizações por timeout de aproximadamente 5 s. O comando e os horários foram conferidos por Docker inspect.

O broker registrou, perto do fim da medição, pausas GC de 6,288 ms e 42,215 ms por volta de 03:12:12 UTC. Isso não coincide de forma suficiente para atribuir sozinho o maior atraso de aproximadamente 454 ms à coleta de lixo. As últimas sondagens retidas pelo Docker não cobrem todo o instante do pico; não se afirma causalidade exclusiva.

O volume experimental foi lido com montagem somente leitura: 143 diretórios no primeiro nível, incluindo internos/partições, não 143 tópicos. Nada foi apagado. Histórico de volumes e caches permanece uma limitação.

O usuário escolheu **manter 48/s e investigar mais**, em vez de recalibrar uma taxa menor. A [R2](../2026-10-27-reduzida65-r2/ACOMPANHAMENTO.md) testa uma sonda TCP leve somente no override experimental; a criação de tópicos e o health da API ainda conferem prontidão semântica antes da carga. Não há rebuild de imagens, alteração do processamento ou afrouxamento dos critérios. Todos os UUIDs da R2 são novos; R1 não será apagada, sobrescrita ou contada entre os 65 definitivos.

Dados brutos e log GC continuam locais em `.runtime/entrega04/` e `.runtime/reduzida65-2026-10-26/`. A V1 e os planos anteriores permanecem preservados. Esta evidência entra no histórico do piloto, não como confirmação/refutação das hipóteses comparativas definitivas.
