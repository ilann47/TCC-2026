# Conferência dos instrumentos e do protótipo — 06/10/2026

## Ambiente e limites

Computador Windows com AMD Ryzen 7 5825U (8 núcleos físicos, 16 processadores lógicos) e 31,36 GiB de memória visível ao sistema. Docker em WSL, Compose 2.40.3. Aplicações Java 21 e PostgreSQL/Kafka com limites do Compose anterior; gerador k6 2.3.0 fixado por digest, com limite de 2 CPUs e 1 GiB. Existiam contêineres de outros trabalhos, registrados nos manifestos: esta validação não é uma campanha de capacidade em ambiente exclusivo.

O sistema preservou seu código de produção. Foram acrescentados instrumentos no diretório `experimento`. O modelo é determinístico por `dataset_id`; `run_id` correlaciona HTTP, cabeçalho Kafka e marcos de persistência, sem alterar o hash. O conjunto é sintético, com payload inteiro de um campo. A igualdade para esse conjunto não cobre todos os tipos de payload existentes.

## Testes executados

`./mvnw.cmd -B -q verify`: **11 testes** do sistema, zero falhas. `./mvnw.cmd -B -q -f experimento/analyzer/pom.xml verify`: **25 testes** dos instrumentos, zero falhas. O target é Java 21; as verificações nativas usaram Java 25.0.2. Os Dockerfiles do analisador também executam os testes no JDK 21. Não atribuir os resultados anteriores da CI como se essa nova versão já tivesse passado remotamente.

Os novos testes cobrem: sucesso com resposta e commit distintos, HTTP 503 como resultado de falha, DLQ versus pendência, ausência de aceite conciliado, falta de marco de commit, hash incorreto, conflito para UUID já salvo, estatística por execução e equivalência/alteração/falta de registro na comparação do modelo. Isso não substitui os experimentos controlados.

## Ensaios reais válidos

| Perfil | UUID da execução | Observação na fase medida |
|---|---|---|
| Modelo síncrono | `e71d7147-04f8-41bc-b44c-30b6857b41cb` | 50/50 salvos; reenvio duplicate; conflito HTTP 409. |
| Modelo assíncrono | `6cdf03fd-1d50-45b3-b77e-1afd41691e95` | 50/50 salvos; reenvio duplicate; tentativa conflitante na DLQ, sem alterar a linha original. |
| PostgreSQL parado — síncrona | `f53dad57-5b76-425a-8bad-44add2111a9f` | 91 envios, 39 respostas 201, 52 respostas 503, 39 registros salvos. |
| PostgreSQL parado — assíncrona | `a5f30182-e7de-47d1-a13a-1a6c1047e6f4` | 90 envios/202, 89 salvos e um na DLQ por três tentativas esgotadas; zero aceite não conciliado. |
| Rajada — síncrona | `0cc8785b-c5fb-4d60-925b-67417ac7f4de` | 120 observados, 120 aceitos e salvos, sem DLQ. |
| Rajada — assíncrona | `b0730237-bd62-4845-bcba-3c3cc7c572d2` | 119 observados, 119 aceitos e salvos, sem DLQ. |
| Consumidor parado — observação curta | `3744207b-00e6-492c-b90d-ab3242e30f51` | 91 aceitos; 37 salvos e 54 retidos pendentes no encerramento da coleta inicial. Não representa perda. |
| Consumidor parado — observação ampliada | `4734b17b-e48b-48bc-b02e-f99d7f9e1f4b` | 91 aceitos/salvos, sem DLQ ou pendências; 51 estavam sem commit na retomada. |

Um ensaio síncrono anterior do perfil modelo (`beb235fc-d9bc-4ed2-a259-2e1b55be3cc9`) também teve coleta consistente, mas não foi o par escolhido para a comparação de conteúdo, porque seu par assíncrono teve exportação inválida. O catálogo inclui esse histórico sem inflar o número de repetições.

No par de equivalência escolhido, o mesmo `dataset_id=199c7db3-d7fd-4296-a665-ff94a2ef0e1a` originou exatamente 50 linhas em ambas as exportações. O comparador Java confirmou todos os campos, UUIDs, payloads e hashes, excluindo somente `persisted_at`. A igualdade e o conflito posterior pertencem a tentativas diferentes com o mesmo UUID: a mensagem conflitante na DLQ **não torna ausente** a linha original já salva.

Nos perfis de falha/rajada: taxa base 5/s, aquecimento 5 s, intervalo máximo de 12 s para terminar o aquecimento, medição 18 s, 32 VUs; parada solicitada por 5 s no primeiro terço da medição. A rajada varia 5→10→5/s em três segmentos, com transições de 1 s. A observação posterior inicial foi 5 s; o segundo ensaio do consumidor usou 40 s. Os manifestos distinguem a pausa programada dos horários efetivos dos comandos.

No ensaio ampliado do consumidor, primeiro commit após o comando de retomada: **9.825,39 ms**. Confirmação de todo o conjunto aceito pendente antes da retomada: **10.440,75 ms**. Esses são dois intervalos de **uma execução**, não médias, não recuperação de throughput estável e não comparação com a síncrona.

## Tentativas inválidas ou incompletas

- `3d835b52-5990-457e-89e6-8aff51bf4c29`: corrida entre criação da saída do k6 e leitura pelo controlador; o controlador terminou sem a coleta completa.
- `07e1ba22-38cf-4f99-817b-b28d886d3c55`: edição do script enquanto Bash ainda o executava; a coleta foi interrompida. Scripts não devem ser editados durante execução.
- `e95859a7-6eae-4f96-bad4-6448322bc749`: exportação de grupo expirou antes da atribuição inicial e não leu a DLQ; o analisador rejeitou a divergência entre log e exportação. Atribuição direta à partição zero confirmou que a mensagem existia; o ensaio foi refeito, sem apagar a tentativa.

Não foram descartadas execuções por resultados desfavoráveis à hipótese. O resultado 89 salvos/90 aceitos durante falha foi conservado e descrito no texto.

## Conciliação e preservação

O catálogo registra **12 tentativas**: nove coletas funcionais consistentes, uma inválida por inconsistência de exportação e duas incompletas. **Zero repetições definitivas.** Todos os checksums existentes das coletas completas foram conferidos, sem divergência.

Uma reanálise independente v5 foi realizada no Java 25.0.2 com o JAR preservado de SHA-256 `b45183db42760dff02d3d171a9be91b739424bb819dab796588f0310dfde00cf`. Os dados brutos, os manifestos e as análises originais não foram sobrescritos. A versão atual separa uma tentativa na DLQ para UUID já salvo de uma não persistência terminal e rejeita durações HTTP impossíveis. O catálogo contém os caminhos das versões e os resumos derivados.

O estado do checkout estava em desenvolvimento durante esses ensaios; isso aparece nos manifestos. Não é a versão congelada da campanha. Evidências completas locais: `implementacao-java/.runtime/entrega04/`; reanálises atuais: `implementacao-java/.runtime/entrega04-reanalysis-v5/`. Dados k6, exportações e eventos por UUID permanecem localmente; o Git contém o inventário, hashes e resumos. A publicação desses derivados não equivale à publicação de todos os dados brutos.

## Critérios que ainda faltam

A campanha precisa confirmar uma referência estável por cinco minutos, validar consumo/overhead do gerador, observar backlog/lag durante o ensaio, definir recuperação sustentada, congelar parâmetros/ordem, executar 10 repetições por combinação e analisar variação entre elas. A CPU/memória coletada é por contêiner e tem resolução aproximada de 3 s; não prova custo global ou complexidade operacional.

`instrument_valid=true` não confirma a hipótese nem transforma um ensaio curto em experimento definitivo. Não há conclusão científica pronta. O capítulo 5 está parcial; o 6 permanece reservado.
