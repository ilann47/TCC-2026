# Guia das métricas e falas para a apresentação

Este guia explica **cada uma das 45 linhas da comparação** das opções 13/14, com unidades, interpretação e falas sugeridas. É material de apoio à demonstração: não substitui o método experimental nem os capítulos de resultados do TCC.

Para executar, consulte o [passo a passo do menu](README.md). Para conferir os cálculos, veja o [comparador](comparison_report.py), o [analisador Java](../experimento/analyzer/src/main/java/br/com/ilan/tcc/experiment/CampaignAnalyzer.java), a [instrumentação](../experimento/analyzer/src/main/java/br/com/ilan/tcc/experiment/Instrumentation.java) e a [carga k6](../experimento/load.js). Estes arquivos são a fonte de verdade das métricas específicas do protótipo.

## 1. Comece pela diferença entre responder e gravar

> “As duas versões salvam no PostgreSQL. O que muda é o caminho até lá. Na síncrona, a API só devolve 201 depois que a gravação termina. Na assíncrona, ela devolve 202 depois que o Kafka confirma a publicação, sem precisar esperar pelo banco. Por isso eu separo o tempo de resposta do tempo até gravar.”

O 202 **não garante que o registro já esteja no PostgreSQL**. O consumidor pode gravá-lo muito rapidamente, até antes de o cliente terminar de receber a resposta, mas a API assíncrona não aguarda essa gravação como condição para confirmar a publicação.

O comparador responde quatro perguntas: quanto demora, quanto conclui, quanto recurso consome e como reage a falhas. Leia as quatro em conjunto; uma resposta rápida isolada não determina a melhor solução.

## 2. Tempos: quanto demora?

Unidade: **milissegundos (ms)**. Mil milissegundos equivalem a um segundo.

### Média, mediana e percentis

| Resumo | Significado | Fala simples |
|---|---|---|
| Média | Soma dos valores dividida pelo número de observações. | “É o tempo médio, mas algumas requisições muito lentas podem puxá-lo para cima.” |
| Mediana | Valor central dos tempos ordenados; com quantidade par, média dos dois centrais. | “Ajuda a olhar o comportamento central, com menos influência dos extremos.” |
| p95 | Valor até o qual ficaram pelo menos 95% das observações. | “Mostra o tempo para a grande maioria, sem esconder tanto a parte lenta.” |
| p99 | Valor até o qual ficaram pelo menos 99% das observações. | “Olha ainda mais para a ponta lenta, que a média pode esconder.” |

O analisador usa a posição `ceil(percentil × n)` nos valores ordenados para p95/p99, não interpolação. Em amostras pequenas, esses percentis podem ficar próximos ou iguais ao maior valor. Percentil **não é taxa de sucesso**, prazo garantido nem intervalo de confiança.

### As nove linhas de tempo

| Métrica no relatório | O que mede |
|---|---|
| Resposta HTTP — média | Média da duração HTTP nativa do k6, incluindo respostas de sucesso e de erro da fase medida. |
| Resposta HTTP — mediana | Mediana dessas durações HTTP. |
| Resposta HTTP — p95 | Percentil 95 dessas durações HTTP. |
| Resposta HTTP — p99 | Percentil 99 dessas durações HTTP. |
| Envio → resposta — média | Média do intervalo entre o marco do script antes da chamada e o marco após seu retorno. Inclui pequenos custos adicionais do cliente/instrumentação e pode incluir estabelecimento de conexão. |
| Envio → commit no banco — média | Média do intervalo entre o envio e o primeiro marco de commit concluído, conciliado com a linha exportada do banco. |
| Envio → commit no banco — p95 | Percentil 95 desses tempos até commit. |
| Envio → commit no banco — p99 | Percentil 99 desses tempos até commit. |
| Amostras com commit observado | Quantidade de registros usados nos cálculos de tempo até commit. É uma contagem, não um tempo. |

A duração HTTP do k6 soma envio, espera e recebimento da resposta; não inclui a resolução inicial de DNS nem o estabelecimento inicial da conexão. Não é exatamente a mesma abrangência de nossas marcações envio→resposta. [Referência oficial das métricas k6](https://grafana.com/docs/k6/latest/using-k6/metrics/reference/).

O tempo até commit inclui, quando presentes, espera no Kafka, consumidor, tentativas e gravação. **Considera apenas registros com commit observado e linha conciliada no banco.** Falha, DLQ ou ausência de commit não recebe latência zero. A duração HTTP, por sua vez, também considera as requisições que falharam. Assim, as duas médias podem ter quantidades de observações diferentes.

> “Aqui eu olho primeiro quanto o cliente esperou pela resposta. Depois, olho quando o trabalho terminou no banco. Também mostro quantos registros entraram nessa média: um tempo baixo não seria suficiente se muitos eventos nem tivessem sido gravados.”

## 3. Carga e persistência: quanto foi concluído?

| Métrica no relatório | Significado e unidade |
|---|---|
| Gravados/s dentro da medição | Registros únicos com commit dentro da janela, divididos pela duração da janela. Unidade: registros/s. É a vazão de conclusão, ou throughput. |
| Requisições enviadas | Quantidade efetivamente enviada na fase medida; não é apenas a taxa programada multiplicada pela duração. |
| Aceitos (201 / 202 com UUID correto) | Quantidade com código esperado para a variante e identificador correspondente ao envio. O significado do aceite é diferente: gravação na síncrona, publicação na assíncrona. |
| Gravados dentro da medição | Quantidade de registros medidos cujo commit ocorreu dentro da janela de medição. |
| Gravados até o fim da coleta | Quantidade de registros medidos presentes no banco ao fim da observação, incluindo os concluídos depois da carga. Não soma os registros do aquecimento. |

Fórmula da vazão: `gravados dentro da medição / segundos medidos`. Não acrescente registros da drenagem posterior ao numerador como se tivessem sido concluídos durante a janela.

Uma iteração pode cair na fronteira temporal. Saturação também pode reduzir envios: confira a contagem efetiva e as iterações não iniciadas. Mesma taxa programada não é prova de igual número efetivamente enviado.

> “Não basta contar quantas requisições a API aceitou. Eu vejo quantos registros chegaram ao banco durante a carga e quantos terminaram depois. Isso separa aceitar trabalho de concluir trabalho.”

Mais vazão só é favorável quando carga, erros, integridade e demais condições também são consideradas. Não representa capacidade máxima por si só.

## 4. Erros, destinos e integridade

| Métrica no relatório | O que significa e como interpretar |
|---|---|
| Respostas por código HTTP | Contagem por código na fase medida. Neste contrato, 201 confirma gravação síncrona e 202 confirma publicação assíncrona. 503 indica indisponibilidade. Código 0 no k6 significa ausência de resposta HTTP válida/problema de transporte, não um código devolvido pelo servidor. |
| Erros HTTP/contrato | Percentual sem confirmação esperada: `(enviados − aceitos) / enviados × 100`. Avalia código e UUID, não somente respostas 500. Não é a taxa de não persistência assíncrona. |
| Iterações não iniciadas (inclui aquecimento) | Execuções programadas que o k6 não conseguiu iniciar; inclui todas as fases, diferentemente da maioria das contagens da tabela. Não são mensagens que o Kafka perdeu. |
| Aceitos em DLQ, não gravados | Eventos medidos encontrados na fila de falhas e sem linha no banco. DLQ é um destino de tratamento, não sucesso de persistência. |
| Aceitos pendentes no Kafka ao fim | Eventos medidos ainda identificados no tópico retido, sem linha no banco e sem destino em DLQ ao fim da coleta. Não pressupõe perda definitiva. |
| Aceitos sem destino reconciliado | Eventos com confirmação esperada, mas sem linha no banco, retenção identificada ou DLQ ao fim da coleta. Exige investigação; não é rotulado automaticamente como perda comprovada. |
| Gravados sem confirmação HTTP | Registros presentes no banco sem confirmação HTTP válida esperada para o cliente. Pode acontecer em resultado incerto/timeout; não se deve presumir ausência e reenviar cegamente. |
| UUIDs duplicados no banco (medição) | Linhas excedentes para um mesmo UUID medido na exportação. A chave única participa da prevenção. Zero duplicado no banco não demonstra ausência de reentrega. |
| Divergências de conteúdo/hash | Divergências entre o registro exportado e o conteúdo determinístico esperado, incluindo o hash canônico. O analisador verifica também o aquecimento; divergência torna a instrumentação inválida, e o comparador recusa apresentá-la como coleta íntegra. |
| Reentregas idempotentes observadas | Marcos de processamento reconhecido como duplicado para os eventos medidos, sem nova linha para o mesmo conteúdo. Pode haver repetição de processamento sem duplicidade persistida. |

Em executores de taxa de chegada, iterações não iniciadas podem decorrer de VUs insuficientes ou de respostas tão demoradas que os VUs ficam ocupados. Investigue configuração, gerador e aplicação antes de atribuir a causa a um componente. [Documentação oficial de dropped iterations](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/dropped-iterations/).

Não há reprocessamento automático de DLQ nesta implementação. Recuperar a dependência não transforma automaticamente uma mensagem em DLQ em registro salvo.

O comparador só publica coletas com `instrument_valid=true`: divergências de hash, evidências incompletas e outras inconsistências não devem virar uma tabela aparentemente aprovada. Erros HTTP no cenário de falha, porém, são resultados do sistema e podem aparecer em uma coleta instrumentalmente válida.

> “Aqui eu acompanho o destino dos eventos, não só a resposta HTTP. Consigo separar o que foi salvo, o que ficou pendente e o que foi para tratamento de falha. Também confiro se o conteúdo está correto e se uma repetição criou outra linha no banco.”

## 5. Fila: quanto trabalho ficou acumulado?

| Métrica no relatório | O que significa |
|---|---|
| Pico de aceitos ainda não gravados | Maior quantidade de eventos medidos já confirmados ao cliente e ainda sem commit observado naquele instante, reconstruída pelos marcos temporais. Não inclui todas as requisições HTTP ainda aguardando resposta. |
| Pico de lag Kafka amostrado | Maior diferença observada entre a posição final do tópico e a posição confirmada do grupo consumidor. É amostrada, portanto pode não capturar um pico muito breve. Não é número de linhas no PostgreSQL. |

Na síncrona, o primeiro pico tende a zero porque o aceite sucede a gravação. **Isso não significa zero requisições em processamento ou zero clientes aguardando.** O lag Kafka não se aplica ao caminho síncrono.

Lag zero sozinho não comprova persistência: o offset pode avançar após encaminhamento terminal à DLQ. O banco e os destinos das mensagens precisam ser conciliados. [Operações de grupos consumidores Kafka 3.9](https://kafka.apache.org/39/operations/basic-kafka-operations/).

> “Esse grupo mostra se o trabalho está se acumulando. Na assíncrona, o cliente pode já ter recebido a confirmação enquanto ainda existe processamento pendente. Eu olho o lag junto com o banco, porque zerar o lag não é, sozinho, prova de que tudo foi salvo.”

## 6. Recursos do sistema

| Métrica no relatório | O que significa |
|---|---|
| CPU média — soma dos serviços do fluxo | Soma das médias amostradas de CPU dos componentes utilizados pelo caminho de negócio. Não é pico simultâneo nem percentual global do computador. |
| Memória média — soma dos serviços do fluxo | Soma das médias amostradas de memória desses componentes, em MiB. Não é memória máxima simultânea nem uso total do Windows. |

Recortes usados:

- Síncrona: `sync-api + postgres`.
- Assíncrona: `async-api + consumer + postgres + kafka`.

No Docker/Linux, aproximadamente 100% equivale a um núcleo lógico ocupado; a soma de serviços pode ultrapassar 100%. Essa escala não é igual ao percentual do computador inteiro no Gerenciador de Tarefas. [Cálculo no código oficial do Docker CLI](https://github.com/docker/cli/blob/master/cli/command/container/stats_helpers.go).

A memória é a reportada pelo Docker CLI; no Linux, a ferramenta desconta determinada parcela de cache. Não é somente o heap Java. [Referência oficial do Docker Stats](https://docs.docker.com/reference/cli/docker/container/stats/).

### As dez linhas por serviço

| Métrica no relatório | Componente observado |
|---|---|
| sync-api: CPU média | Processamento da API que grava antes de responder. |
| sync-api: memória média | Memória do contêiner dessa API. |
| async-api: CPU média | Processamento da API que publica no Kafka. |
| async-api: memória média | Memória do contêiner dessa API. |
| consumer: CPU média | Processamento dos eventos e chamadas de persistência pelo consumidor. |
| consumer: memória média | Memória do contêiner consumidor. |
| postgres: CPU média | Processamento do banco utilizado na execução de cada variante. |
| postgres: memória média | Memória do contêiner do banco. |
| kafka: CPU média | Processamento do broker que participa do caminho assíncrono. |
| kafka: memória média | Memória do contêiner do broker. |

O Kafka experimental também é iniciado como infraestrutura/coleta no ensaio síncrono, mas não participa de seu caminho de negócio e não entra no total síncrono. Essa exclusão é um recorte explícito, não uma medida de todo o consumo do computador. k6 e observador são apresentados separadamente. Programas externos podem disputar os mesmos recursos.

Contêiner parado pode produzir amostra zero, dependendo do estado da coleta. Isso reflete indisponibilidade, não eficiência. Menor CPU/memória não determina a melhor alternativa sem considerar quanto trabalho foi concluído e com quais erros. Estas medidas não são consumo de energia, preço de infraestrutura nem custo operacional completo.

> “Eu comparo o caminho completo, não apenas as APIs. A assíncrona usa Kafka e consumidor, então esses componentes entram na conta. Também abro por serviço para mostrar de onde vem o consumo.”

## 7. Recursos de quem está medindo

O **k6** gera requisições. O **observador** coleta informações do banco e do Kafka. Nenhum deles é serviço de negócio; seu consumo é separado dos totais anteriores.

| Métrica no relatório | Significado |
|---|---|
| k6: CPU p95 / limite | CPU no p95 como percentual da capacidade atribuída ao gerador, não percentual de todo o host. |
| k6: memória máxima / limite | Maior memória observada do gerador dividida por seu limite, em percentual. |
| Observador: CPU p95 / limite | CPU no p95 como percentual da capacidade atribuída ao coletor. |
| Observador: memória máxima / limite | Maior memória observada do coletor dividida por seu limite, em percentual. |

Nesta configuração, o gerador tem limite de 2 CPUs e 2 GiB; o observador, 0,25 CPU e 256 MiB. O cálculo divide a CPU Docker pela quantidade de CPUs atribuída e divide a memória observada pelo limite correspondente. Esses percentuais **não devem ser somados** aos percentuais brutos de CPU do sistema como se fossem a mesma escala.

Uso alto pode indicar limitação do instrumento. O aviso de uso a partir de 80% no relatório é um sinal para investigar, não prova automática de que o ensaio é inválido. Uso baixo também não prova interferência nula; a análise deve considerar cobertura e erros de coleta.

> “Eu também verifico se quem está medindo não virou o gargalo. Se o gerador ou o coletor estiver saturado, isso pode influenciar os números atribuídos à aplicação.”

## 8. Recuperação: voltou quando e em que sentido?

Aplica-se aos cenários de interrupção, não ao cenário normal. O relógio de recuperação começa ao concluir o comando de retomada registrado no manifesto; iniciar um contêiner não garante prontidão imediata da dependência.

| Métrica no relatório | Significado |
|---|---|
| Primeiro commit após retomada | Intervalo até a primeira gravação medida observada depois da retomada. Uma gravação isolada não comprova estabilidade. |
| Todos os aceitos pendentes gravados | Tempo até concluir a persistência de todos os eventos que estavam aceitos e sem commit no instante da retomada. “Sem aceitos pendentes” significa ausência desse conjunto, não recuperação instantânea. Se algum não for salvo, a drenagem completa não é anunciada. |
| Recuperação sustentada confirmada | Tempo até completar a terceira janela consecutiva de 10 s que atende ao critério de estabilidade. Inclui o tempo necessário para confirmar os 30 s de funcionamento sustentado. |

Critério implementado para cada uma das três janelas completas após a retomada:

- Gravar pelo menos 90% da taxa-alvo: no mínimo `taxa × 9` registros por janela de 10 s.
- Nenhum erro HTTP/contrato com resposta naquela janela.
- Aceitos ainda não gravados no fim da janela até `max(2, ceil(taxa × 0,1))`.
- Observação do banco saudável e com no máximo 3 s de idade; na assíncrona, lag também saudável e até o mesmo limite de pendências.
- Permanecer dentro da fase de entrada ativa; não usar apenas o período sem carga para declarar recuperação operacional.

Se não houver três janelas qualificadas, aparece “Não observada na janela”. Isso **não é zero nem falha permanente comprovada**. A janela pode ter terminado antes de haver observação suficiente. A recuperação de vazão não prova que todos os eventos anteriores tenham sido gravados; confira também DLQ, pendentes e destinos.

> “Eu separo voltar a gravar um registro, eliminar o trabalho acumulado e manter o funcionamento estável. São três coisas diferentes. Por isso não trato o primeiro sucesso depois da falha como recuperação completa.”

## 9. Exemplo real, versionado e apenas demonstrativo

Ensaio de **26/10/2026 no horário de São Paulo**; os manifestos usam UTC e começam em 27/10. PostgreSQL interrompido nas duas versões; uma execução por versão, síncrona primeiro. Parâmetros: 5 eventos/s, aquecimento de 10 s, medição de 90 s, drenagem de 20 s, 64 VUs e interrupção solicitada de 5 s. A indisponibilidade efetiva e os instantes de retomada estão nos manifestos locais.

O [exemplo JSON versionado](exemplos/2026-10-26-postgres-stop.json) preserva as 45 linhas, os identificadores e as limitações do relatório original, sem caminhos pessoais. As evidências brutas continuam locais, fora do Git; o snapshot não as substitui. O checkout estava modificado durante a coleta, como registrado nos manifestos. É **validação/demonstração**, não uma repetição definitiva da campanha congelada.

| Métrica | Síncrona | Assíncrona |
|---|---:|---:|
| Resposta HTTP média | 438,51 ms | 11,67 ms |
| Envio → commit médio | 157,62 ms | 598,78 ms |
| Registros com commit observado | 423 | 451 |
| Gravados/s dentro da medição | 4,70 | 5,00 |
| Gravados até o fim da coleta | 423 | 451 |
| Erros HTTP/contrato | 6% | 0% |
| CPU média somada | 7,05% | 45,32% |
| Memória média somada | 220,61 MiB | 923,51 MiB |
| Recuperação sustentada confirmada | 44,18 s | 31,79 s |

Foram 450 envios na síncrona e 451 na assíncrona. Não são conjuntos de contagens exatamente iguais: são mesma configuração de chegada e conteúdo determinístico correspondente, com diferença na fronteira de execução. Na síncrona houve 423 respostas 201 e 27 respostas 503; na assíncrona, 451 respostas 202. Os 27 erros síncronos não entram na média de tempo até commit.

> “Nesse ensaio, quando o banco ficou indisponível, a síncrona apresentou erros e a resposta média ficou mais demorada. A assíncrona continuou confirmando publicações no Kafka, mas isso não significou gravação imediata: o tempo médio até o commit foi maior.
>
> Também houve diferença no consumo dos componentes. Então eu olho o conjunto: resposta, gravação, erros, recursos e recuperação. A média de commit da síncrona considera só os 423 registros gravados, não os envios que falharam.
>
> Esses números são dessa execução, nesse computador. Eu não uso essa demonstração isolada para afirmar que REST ou Kafka são melhores em qualquer situação.”

Não derive superioridade estatística, capacidade máxima ou escalabilidade comprovada desse par curto. Outros programas, aquecimento, ordem fixa e estado dos volumes/cache podem influenciar. O reset é lógico da tabela experimental, não a recriação física de todo o ambiente.

## 10. Roteiro de fala para dez minutos

Prepare imagens e serviços antes; use **13 → 1** antes da banca para gerar comparação normal e **14** para reapresentá-la sem carga. Se quiser mostrar falha do banco, prepare também esse relatório antes e mantenha seu HTML acessível. A opção 14 mostra somente o último relatório completo, não um histórico de seleção. Compare o título/cenário e os UUIDs para não narrar um ensaio enquanto projeta outro.

| Tempo sugerido | Ação e fala de apoio |
|---|---|
| 0–2 min | Opção 2: “As duas versões fazem a mesma gravação; muda a forma de comunicação e quem aguarda a conclusão.” |
| 2–3 min | Opções 3 e 5: “O 201 vem depois da transação. Consulto o mesmo UUID para confirmar o registro.” |
| 3–6 min | Opções 6, 4, 5, 8, 7 e 5: “Com o consumidor parado, Kafka pode aceitar um novo evento, mas ele ainda não aparece no banco. Depois retomo e verifico esse mesmo UUID.” |
| 6–9 min | Opção 14/HTML: “Aqui separo resposta HTTP e tempo até gravar; depois olho quantos foram salvos, os erros e os recursos. Se este for um cenário de falha, explico também as três medidas de recuperação.” |
| 9–10 min | Limitações e saída 0: “É uma execução demonstrativa local. A conclusão da pesquisa depende das repetições e da análise dos experimentos definitivos.” |

Não é preciso ler 45 linhas em voz alta. Priorize resposta HTTP/p95, tempo até commit, vazão, erros/destinos, recursos e recuperação aplicável. As outras linhas sustentam essas interpretações e ajudam nas perguntas da banca. Opções 9/10 podem ilustrar k6 ao vivo, mas não tente somar todos os testes de carga e falha aos dez minutos.

### Respostas curtas para perguntas frequentes

**“Qual é melhor?”**

> “Depende do critério e da situação medida. Eu preciso relacionar tempo de resposta, conclusão da gravação, falhas, recursos e recuperação. Esse ensaio demonstrativo sozinho não decide a pesquisa.”

**“202 quer dizer que salvou?”**

> “Não. Confirma que o Kafka aceitou a publicação. Eu verifico a persistência separadamente no banco.”

**“Zero duplicado quer dizer exatamente uma entrega?”**

> “Não. Pode haver reentrega. A persistência idempotente e a chave única evitam outra linha para o mesmo evento e conteúdo.”

**“Lag zero quer dizer que está tudo no banco?”**

> “Não necessariamente. Uma mensagem pode ter sido encaminhada à DLQ. Por isso eu concilio os destinos.”

**“Por que não houve recuperação na carga normal?”**

> “Porque não foi provocada falha nesse cenário. Não se aplica é diferente de zero segundos.”

**“Essa latência inclui eventos que não foram gravados?”**

> “A duração HTTP inclui os envios com resposta ou falha de transporte observada. O tempo até commit considera só os registros com gravação observada. Por isso mostro a quantidade de amostras e os destinos não gravados.”

**“Se os números de hoje forem diferentes do exemplo?”**

> “Eu apresento os valores do relatório que estou mostrando. Cada execução tem seus identificadores e condições; o exemplo versionado é uma referência de interpretação, não uma previsão.”

## 11. O que não afirmar

- Não transformar menor tempo de 202 em menor tempo de gravação.
- Não tratar “não disponível”, “sem observações”, “não se aplica” ou recuperação não observada como zero.
- Não chamar toda ausência temporária de perda; nem toda resposta 202 de sucesso final.
- Não presumir que restaurar o banco reprocessa automaticamente a DLQ.
- Não comparar médias de commit ignorando suas quantidades de registros e os erros excluídos desse cálculo.
- Não chamar menor consumo de um contêiner parado de eficiência.
- Não apresentar consumo Docker como energia, custo financeiro ou consumo global do computador.
- Não usar este exemplo/demonstração como resultado definitivo dos capítulos 5/6 ou como conclusão geral sobre REST/Kafka.

O [protocolo científico](../experimento/PROTOCOLO-ENTREGA04.md) é separado. Documentar este roteiro não inicia a campanha nem modifica as entregas históricas ou o texto do TCC.
