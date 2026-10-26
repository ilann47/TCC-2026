# Calibração e instrumentação — 26/10/2026

Estado: **pronto para iniciar a campanha**, sem nenhuma repetição definitiva executada nesta sessão. Referência comum: **48 eventos/s**.

Sessão: 529e0349-d5b4-4001-a862-a0755cd69b72. Início UTC: 2026-10-26T22:20:32.699561347Z; término UTC: 2026-10-26T23:39:14.878832625Z. Código medido: f50b498ccfcfaf052267dc61561c627bc79928d8. As 20 execuções desta sessão são calibração/validação, não repetições dos cenários finais.

Ambiente: AMD Ryzen 7 5825U with Radeon Graphics, 16 CPUs lógicas visíveis no WSL. O inventário complementar está em [environment.json](environment.json); versões e limites efetivos também constam dos manifestos. Frequência dinâmica, temperatura e processos do Windows não foram controlados.

## Como foi escolhida a referência

A política foi registrada antes da exploração. Foram avaliadas taxas crescentes e escolhida uma candidata comum elegível nas duas variantes; o arredondamento para múltiplo de quatro permite níveis C2 exatos. A candidata foi confirmada em cada variante com 60 s de aquecimento e 300 s de medição. Isso não estima a capacidade máxima do sistema.

| Etapa | Variante | Taxa/s | Eventos medidos | Salvos ao final | Elegível como referência |
|---|---|---:|---:|---:|---|
| exploration | sync | 10 | 600 | 600 | sim |
| exploration | async | 10 | 601 | 601 | sim |
| exploration | async | 25 | 1500 | 1500 | sim |
| exploration | sync | 25 | 1501 | 1501 | sim |
| exploration | sync | 50 | 3000 | 3000 | sim |
| exploration | async | 50 | 3000 | 3000 | sim |
| exploration | async | 100 | 6001 | 6001 | não: dropped_iterations, queue_growing, backlog_above_reference_limit |
| exploration | sync | 100 | 6001 | 6001 | não: dropped_iterations |
| confirmation | async | 48 | 14401 | 14401 | sim |
| confirmation | sync | 48 | 14401 | 14401 | sim |

Na execução 691084d7-1c86-442d-bf26-c9756f7e85ce, as iterações não iniciadas pelo gerador se distribuíram por cenário: {"warmup":28}. Elas não representam registros enviados e perdidos; todos os destinos devem ser conferidos separadamente. A rejeição como referência é conservadora e não estima sozinha a capacidade da API.

Na execução 3c6aaabf-e52b-4890-a1af-caef4bfd50e9, as iterações não iniciadas pelo gerador se distribuíram por cenário: {"warmup":9}. Elas não representam registros enviados e perdidos; todos os destinos devem ser conferidos separadamente. A rejeição como referência é conservadora e não estima sozinha a capacidade da API.

## Controle de interferência dos instrumentos

Dois blocos pareados por variante, com a ordem controle/completo invertida. O controle preserva o logging do aplicativo e usa apenas resumo HTTP e verificação independente do banco; remove JSON por evento, observador e amostragem de recursos. O p95 abaixo usa o mesmo estimador nativo do k6 nos dois modos, não compara algoritmos diferentes de percentil.

| Variante | Bloco | p95 controle (ms) | p95 completo (ms) | Diferença (ms) |
|---|---:|---:|---:|---:|
| sync | 1 | 6,27 | 6,12 | -0,15 |
| sync | 2 | 5,99 | 6,01 | 0,03 |
| async | 1 | 23,90 | 25,77 | 1,88 |
| async | 2 | 23,29 | 28,08 | 4,79 |

O critério de triagem exige investigação se a diferença exceder max(2 ms, 25% do p95 de controle) em ambos os blocos de uma variante. O resultado não demonstra overhead zero nem constitui teste estatístico de equivalência. As comparações definitivas medirão o protótipo instrumentado, com configuração igual entre repetições. O observador consulta SQL nas duas variantes e Kafka Admin apenas na assíncrona; os controles expõem parte desse efeito, mas não eliminam todo possível viés de instrumentação.

## Recursos na confirmação de cinco minutos

| Variante | CPU p95 gerador (% da quota) | Memória máxima gerador (% limite) | CPU p95 observador (% quota) | Memória máxima observador (% limite) |
|---|---:|---:|---:|---:|
| async | 12,11 | 27,50 | 5,84 | 33,91 |
| sync | 9,25 | 28,28 | 2,32 | 29,58 |

O k6 emitiu alerta de alta cardinalidade pelas tags de correlação por evento. O alerta e seu vínculo com os UUIDs constam dos consoles brutos e do catálogo; não foram ocultados. A folga da tabela é a observada com essa instrumentação. Não extrapolar para cargas/durações maiores: a campanha deve parar para investigação se gerador ou observador ultrapassarem as margens congeladas. Referência técnica: [tags do k6](https://grafana.com/docs/k6/latest/using-k6/tags-and-groups/).

O gerador dispõe de 2 CPUs e 2 GiB; o observador, 0,25 CPU e 256 MiB. A CPU Docker é normalizada pela quota atribuída. A memória do CLI exclui cache conforme a documentação Docker; não é consumo global da máquina. O ambiente observado deve ser preservado nas repetições.

O isolamento dos dados é lógico: a tabela experimental é reinicializada e cada execução recebe tópicos e grupo novos. O broker e os volumes permanecem, com tópicos anteriores preservados. Isso não equivale a limpar caches, reinicializar a máquina ou eliminar todos os efeitos do histórico; a ordem contrabalançada e o aquecimento mitigam, mas não anulam essa limitação. Nesta versão do CLI, o contêiner parado apareceu com CPU 0 e memória 0B/0B; essas amostras brutas são preservadas. As médias dos cenários de falha misturam períodos ativos e indisponíveis: não representam eficiência, consumo condicionado ao processo ativo, energia ou custo global. A janela de parada deve acompanhar qualquer comparação de recursos.

Os limites foram escolhidos antes da exploração como margens de engenharia, não como constantes universais: 30% de reserva na quota de CPU do gerador, 25% na memória, pelo menos 95% de conclusões dentro da janela e 90% em cada janela de dez segundos. O limite de fila escala com 0,25 s de chegadas, com piso de cinco registros. A cauda não pode crescer mais que 0,01 evento/s. A comparação de controles é uma triagem de interferência, não teste de significância ou prova de equivalência.

Aceites sem commit e requisições HTTP em voo são medidas diferentes: na síncrona, o sucesso HTTP ocorre depois do commit, de modo que o primeiro indicador tende a zero mesmo quando há clientes aguardando. O lag Kafka é específico da assíncrona. Nenhum deles deve ser apresentado como uma fila física diretamente equivalente entre as arquiteturas.

## Recuperação validada

Ensaios de validação a 10 eventos/s, com 10 s de aquecimento, 90 s de medição e interrupção de 10 s. Não são as repetições definitivas de falha a 12/s por 40 s.

- consumer-stop: 901 envios, 901 aceites, 901 salvos, 0 na DLQ terminal. Recuperação operacional sustentada confirmada 42,99 s após o comando de retomada. UUID: 5bd93ee6-e52a-417e-b22c-9d7921f93d66.
- postgres-stop: 901 envios, 901 aceites, 900 salvos, 1 na DLQ terminal. Recuperação operacional sustentada confirmada 38,12 s após o comando de retomada. UUID: 9fe14337-6961-4458-ae44-7fb5458302ff.

O primeiro commit, a persistência do backlog anterior e a recuperação sustentada são medidas distintas. O último critério exige três janelas completas consecutivas de dez segundos com entrada ativa, >=90% da taxa alvo em commits únicos, zero erros HTTP e fila/lag limitados com observação saudável e recente. O instante de confirmação inclui esses trinta segundos. Uma mensagem na DLQ impede alegar recuperação completa da persistência, mesmo com throughput novamente estável.

## Plano definitivo ainda não executado

C1/C2: 12, 24, 36 e 48 eventos/s. C3: 48→96→48. C4/C5: banco parado em ambas ou consumidor parado apenas na assíncrona, à taxa comum de 12/s, falha de 40 s iniciada por volta dos 100 s de medição. Os instantes efetivos dos comandos e da parada são registrados. Essa carga de falha foi reduzida por desenho, para não confundir o acúmulo de requisições com falta de VUs; não muda entre variantes.

São 130 execuções em dez blocos, sem sobreposição, com ordem de condições embaralhada por semente 20261026 e primeira variante contrabalançada. UUIDs já foram gerados no plano. Aquecimento 60 s, intervalo até 12 s para concluí-lo, medição 300 s e observação posterior 90 s. VUs: 128 nas cargas normais e 176 nas falhas; o último valor reserva mais de 12 vezes a taxa de chegada para o timeout HTTP de 10 s. Mudança de ambiente ou parâmetros exige nova calibração.

Os dados brutos estão em `.runtime/entrega04/`; os caminhos e hashes constam de `catalog.json`. Os resumos são publicados, sem duplicar todo o volume bruto. Checksums foram verificados antes de congelar. Os testes da instrumentação passaram no JDK 21. Não foram reescritas entregas históricas nem preenchidos capítulos 5 e 6 com estes ensaios.

A sessão preliminar 24cbb534-4a69-45ee-8b12-7f0da8082182 foi interrompida por uma lacuna de 7,03 s no observador durante a reconexão com PostgreSQL parado. A política não foi afrouxada. O observador passou a usar o IP experimental capturado antes da parada e loginTimeout de 2 s; os dados preliminares e a causa foram preservados. A confirmação usa somente a nova versão consistente dos instrumentos.

Fontes técnicas: [Kafka Admin](https://kafka.apache.org/39/javadoc/org/apache/kafka/clients/admin/Admin.html), [Docker stats](https://docs.docker.com/reference/cli/docker/container/stats/), [k6: alocação de VUs](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/arrival-rate-vu-allocation/).
