# Instrumentação e execução dos experimentos

A instrumentação foi validada e a referência comum foi calibrada em **48 eventos/s** em 26/10/2026. Consulte o [relatório de calibração](calibracao/2026-10-26-529e0349/README.md), o [protocolo](PROTOCOLO-ENTREGA04.md) e a [configuração congelada](FROZEN-PROTOCOL.json). **As 130 execuções definitivas ainda não foram iniciadas.** Calibração não constitui resultado final do TCC nem permite confirmar suas hipóteses.

## O que é medido

| Medida | Evidência e interpretação |
|---|---|
| Tempo HTTP | `http_req_duration` do k6, somente `phase=measure`; não inclui todos os custos anteriores de conexão/bloqueio. |
| Envio → retorno | Marcadores instrumentados do cliente, incluindo a chamada e a conferência da resposta. Não é idêntico ao tempo HTTP nativo. |
| Envio → persistência | Envio no cliente até `commit_completed`, emitido após o retorno da transação; não é o instante físico de fsync nem o valor de `persisted_at`. |
| Throughput concluído | UUIDs únicos com commit dentro da janela de medição / duração dessa janela. Registros concluídos na drenagem são informados separadamente. |
| Pendências no tempo | Série de aceites ainda sem commit, calculada pelos marcadores, e contagens de registros visíveis no banco. Não mede diretamente requisições HTTP em voo. |
| Lag Kafka | Diferença entre fim do tópico e offset confirmado pelo grupo, aproximadamente a cada segundo; específico da variante assíncrona. |
| CPU e memória | Amostras Docker por contêiner, inclusive gerador e observador, em lotes de aproximadamente três segundos. CPU também normalizada pela quota atribuída. |
| Recuperação | Primeiro commit, conclusão do backlog anterior e recuperação operacional sustentada são medidas separadas. A última exige três janelas consecutivas de dez segundos com entrada ativa. |

HTTP `201` significa persistência concluída na síncrona. HTTP `202` significa publicação confirmada pelo Kafka na assíncrona, **não** persistência no PostgreSQL. A conciliação verifica cada UUID, conteúdo completo e SHA-256 por encoder independente do código de produção.

O gerador recebe 2 CPUs/2 GiB; o observador, 0,25 CPU/256 MiB. A calibração verificou a folga dos dois e comparou coleta reduzida/completa em dois blocos por variante. Os critérios são margens de engenharia predefinidas, não limites universais nem prova de overhead zero.

## Antes da campanha

Use WSL/Linux, Docker e Compose >=2.24.4. Não é necessário instalar k6 ou Java no WSL: gerador e analisador executam em contêineres. Preserve as imagens medidas; reconstrução de imagens ou mudança relevante de ambiente exige revisar/recalibrar o protocolo. O analisador recusa IDs de imagem, código instrumentador ou parâmetros diferentes dos congelados.

Dentro de `implementacao-java`, confira o plano sem gerar carga:

```bash
bash experimento/campaign.sh --check experimento/calibracao/2026-10-26-529e0349/plan.csv
```

Para iniciar a campanha, em uma janela reservada sem outros trabalhos pesados:

```bash
docker compose -p tcc-java-2026 stop
bash experimento/campaign.sh experimento/calibracao/2026-10-26-529e0349/plan.csv
```

O primeiro comando para somente o ambiente interativo deste TCC, sem apagar dados. O executor não encerra projetos alheios; registra os contêineres concorrentes. Não execute dois ensaios simultâneos e não edite scripts enquanto estiverem em execução. O plano tem dez blocos/130 execuções: somente aquecimento e medição somam 13 horas, antes de inicialização, exportação e drenagem.

O projeto experimental `tcc-entrega04` não publica portas e tem volumes próprios. Somente suas linhas sintéticas são reinicializadas, após a exportação anterior. Tópicos/grupos são novos a cada execução, mas o broker e os volumes permanecem: não se trata de reinicialização física de caches ou da máquina.

## Evidências e validade

Os dados brutos ficam em `.runtime/entrega04/<run_id>-<variante>/`, fora do Git. Cada pasta contém manifesto, dados k6 comprimidos, logs de marcos, exportações de banco/tópico/DLQ, `observation.jsonl`, `timeline.csv`, recursos, `summary.json`, `events.csv` e `SHA256SUMS`. A confirmação de cobertura temporal inclui observador e gerador. Falha de consulta durante a interrupção planejada é registrada, não convertida em zero saudável.

`instrument_valid=true` indica consistência da coleta, não aprovação da hipótese ou ausência de falhas do sistema. HTTP 503, DLQ, pendências e drops em sobrecarga podem ser resultados válidos, mas precisam de interpretação. Drops são iterações que o gerador não iniciou, não registros enviados e perdidos. DLQ é não persistência terminal, não desaparecimento nem recuperação automática. Um HTTP não confirmado pode coexistir com um registro salvo.

Os percentis do analisador usam nearest rank por execução. A comparação de interferência usa o mesmo percentil nativo do k6 nos dois modos. Não misture os estimadores nem transforme eventos individuais em repetições experimentais independentes. A agregação e discussão entre repetições dependem da campanha posterior.

O Docker exibiu CPU/memória zero para contêineres parados. As médias em falhas misturam períodos ativos e indisponíveis; não demonstram economia, energia, custo operacional ou eficiência. Relógios de parede e amostragem também limitam a precisão dos intervalos. Os resultados valem apenas para o ambiente observado.

Para conferir os arquivos brutos: `sha256sum -c SHA256SUMS` na pasta da execução. Os checksums detectam alterações; não são assinatura digital. Consulte os [comandos detalhados](ENTREGA04.md), inclusive encerramento sem remover volumes. Após os testes, `docker compose -p tcc-java-2026 up -d` retoma o ambiente interativo.

## Validações e histórico

O analisador passou em 46 testes no JDK 21; a aplicação mantém sua suíte e smoke REST/Kafka/PostgreSQL no CI. Para executar os testes do analisador: `./mvnw -B -f experimento/analyzer/pom.xml verify` no WSL ou `./mvnw.cmd -f experimento/analyzer/pom.xml verify` no PowerShell.

O [piloto inicial de 05/10/2026](PILOTO-2026-10-05.md) e os scripts `pilot.sh`/`pilot.js` são históricos de validação curta. Seus dados ficam em `.runtime/pilot/`; não definem a carga atual nem devem ser somados às repetições definitivas. Entregas acadêmicas históricas não foram reescritas.

Fontes dos instrumentos: [k6 — modelo de chegada e VUs](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/arrival-rate-vu-allocation/), [Docker stats](https://docs.docker.com/reference/cli/docker/container/stats/) e [Kafka Admin](https://kafka.apache.org/39/javadoc/org/apache/kafka/clients/admin/Admin.html). São documentação técnica, não novos artigos científicos do referencial teórico.
