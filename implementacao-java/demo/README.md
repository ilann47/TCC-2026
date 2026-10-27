# Demonstração ao vivo com menu

Este roteiro permite apresentar o protótipo sem depender de uma IA para executar comandos. Você escolhe as etapas no terminal. O menu explica o que está fazendo, guarda o último UUID e mostra uma fala sugerida. **Não executa as 130 repetições, não inicia `campaign.sh` e não produz resultados científicos definitivos.**

## 1. Abrir o menu

Use um terminal **WSL/Ubuntu ou Linux com Bash**, não o PowerShell nem o Git Bash. No computador atual:

```bash
cd /mnt/c/Users/ilan.wendling/OneDrive/sistemasDeInformacao/TCC/TCC-2026/implementacao-java
bash demo/apresentacao.sh
```

Se o repositório estiver em outra pasta, entre em `implementacao-java` dessa cópia. O script encontra seus arquivos pelo próprio diretório e não depende de caminhos pessoais fixos no código.

Pré-requisitos: Docker com Compose, `curl`, Python 3 e as imagens Java já preparadas. Python usa apenas a biblioteca padrão para criar/formatar JSON e verificar UUID/status; não é outra implementação do sistema. Java e k6 executam em contêineres. O menu informa qualquer pré-requisito ausente; não instala pacotes no sistema.

**Antes da banca**, use a opção **1**. Ela inicia o projeto `tcc-java-2026` sem recompilar, aguarda a saúde das APIs e baixa a imagem fixada do k6 se estiver ausente. Isso pode exigir internet; não deixe downloads/builds para os dez minutos de apresentação. Se faltarem imagens Java, siga a preparação do [README da implementação](../README.md). Não reconstrua as imagens medidas da campanha congelada apenas para demonstrar.

Uma conferência sem enviar eventos, iniciar/parar contêineres ou baixar imagens:

```bash
bash demo/apresentacao.sh --check
```

## 2. O que cada serviço faz

| Serviço | Papel nesta implementação |
|---|---|
| `sync-api` | Recebe o evento, valida, grava no PostgreSQL e então devolve 201. |
| `async-api` | Recebe o evento e aguarda confirmação do Kafka; devolve 202 sem aguardar a gravação no PostgreSQL. |
| `kafka` | Retém eventos no tópico `audit-events`. O grupo do consumidor acompanha sua posição. |
| `consumer` | Lê Kafka, valida e grava no mesmo repositório PostgreSQL; trata reentrega, tentativas e DLQ. |
| `postgres` | Destino final dos registros das duas variantes. |

`audit-core` e `audit-storage` são bibliotecas compartilhadas, não processos que precisam ser iniciados separadamente. Swagger é a interface de teste manual. k6 é o cliente que gera requisições controladas, não um sexto serviço de negócio.

A opção **2** mostra os serviços, os fluxos e o endereço real do Swagger. O padrão é [http://localhost:18002/swagger-ui/index.html](http://localhost:18002/swagger-ui/index.html). O menu consulta as portas publicadas pelo Compose, aceita apenas `127.0.0.1` e não envia carga a servidores externos.

## 3. Menu

| Opção | Ação |
|---|---|
| 1 | Preparar/iniciar serviços e obter k6, sem build. |
| 2 | Mostrar serviços, fluxos e link do Swagger. |
| 3 | Enviar um evento síncrono e verificar HTTP 201, UUID e status. |
| 4 | Enviar um evento assíncrono e verificar HTTP 202, UUID e status. |
| 5 | Consultar o último UUID pela API síncrona, que lê o PostgreSQL. |
| 6 | Pausar somente o consumidor. Kafka, APIs e banco permanecem ativos. |
| 7 | Retomar consumidor; se o último evento for assíncrono, aguardar sua persistência por até 60 s. |
| 8 | Consultar offsets/lag do grupo `audit-persistence-java`. |
| 9 | k6 na síncrona, por padrão 5 eventos/s durante 20 s. |
| 10 | k6 na assíncrona, com a mesma carga curta. |
| 11 | Amostra de CPU/memória dos cinco serviços e logs recentes. |
| 12 | Exibir o roteiro e falas dentro do terminal. |
| 0 | Sair; tentar retomar o consumidor caso este menu o tenha pausado. |

Depois de cada ação, leia o resultado e pressione Enter para voltar. O menu mantém o UUID do último envio durante a sessão. Não é necessário copiar UUIDs para executar as opções 5 e 7. Para usar o Swagger em paralelo, copie o UUID exibido e consulte `GET /audit/{eventId}` na definição síncrona.

## 4. Passo a passo e falas para a banca

### A. Mostrar a arquitetura

Opção **2**.

> “As duas versões salvam no PostgreSQL. Na síncrona, a API grava diretamente. Na assíncrona, ela publica no Kafka, e o consumidor faz a gravação. São dois caminhos para a mesma função.”

### B. Demonstrar a síncrona

Opção **3**, depois **5**. Resultado esperado: POST 201 e consulta 200. O script mostra o JSON enviado, a resposta, o UUID e o hash retornado pelo serviço.

> “Enviei um evento. O serviço só me respondeu sucesso depois que a transação terminou. Consultando esse UUID, consigo confirmar que o registro está no banco.”

### C. Demonstrar a assíncrona em operação normal

Opção **4**, depois **7** e **5**. Resultado esperado: POST 202 e, após o processamento, consulta 200. A consulta pode encontrar a linha rapidamente; não há uma demora mínima garantida.

> “Aqui o 202 confirma a publicação no Kafka. Quem grava é outro processo, o consumidor. O registro pode aparecer rapidamente, mas a resposta da API não significa, por si só, que a gravação já aconteceu.”

### D. Evidenciar o desacoplamento

Opção **6**, depois **4**, **5** e **8**, nesta ordem. É importante enviar um **novo evento depois de parar o consumidor**; consultar o anterior mostraria um registro que já estava salvo.

Resultado esperado: o novo POST assíncrono retorna 202; a consulta desse novo UUID retorna 404 enquanto o consumidor permanece parado. O lag pode crescer. Um aviso de grupo sem membros ativos é esperado nessa situação.

> “Parei só o consumidor. A API continua aceitando porque o Kafka permanece disponível. Este novo evento ainda não aparece no banco. Isso mostra a diferença entre aceitar o trabalho e concluir a gravação.”

LAG é a diferença entre a posição final do tópico e o offset confirmado pelo grupo. Não é a quantidade de linhas no PostgreSQL. Uma posição confirmada também pode corresponder a encaminhamento terminal à DLQ; portanto, lag zero sozinho não comprova persistência. [Operações do Kafka 3.9](https://kafka.apache.org/39/operations/basic-kafka-operations/).

### E. Retomar o consumidor

Opção **7**, depois **5** e, se desejar, **8**. O menu aguarda até 60 s pelo UUID. A inicialização e atribuição de partições levam algum tempo; se o prazo terminar, ele informa falta de confirmação, não inventa perda nem sucesso.

> “Retomei o consumidor. Agora ele pode processar o que ficou no Kafka. Confiro novamente o mesmo UUID para verificar se este evento foi salvo.”

Não substitua esta demonstração por parar o PostgreSQL e prometer que tudo será salvo depois. Com o consumidor ativo e o banco indisponível, suas tentativas podem esgotar e a mensagem seguir à DLQ. Não há reprocessamento automático da DLQ implementado.

### F. Mostrar geração de carga

Com o consumidor retomado, use **9** e depois **10**. Cada opção usa um UUID de execução novo e cria eventos sintéticos novos. O padrão é 5 eventos/s por 20 s, com oito usuários virtuais disponíveis. Esse número de VUs não significa oito requisições simultâneas constantes.

> “Antes eu enviava um evento por vez. Agora o k6 envia seguindo uma taxa programada. O resumo mostra quantos eventos foram enviados, respostas inválidas, iterações não iniciadas e os tempos HTTP.”

O resumo mostra média, mediana, p95 e p99 **apenas do HTTP dos eventos**, excluindo as consultas iniciais de prontidão. p95 é o percentil 95, não a média nem uma promessa de prazo. O teste valida código HTTP, UUID e status do corpo. Uma resposta inválida ou iteração não iniciada faz o teste falhar; não basta o comando terminar para afirmar sucesso.

> “Estes tempos são de resposta HTTP. Na síncrona, a resposta sucede a persistência. Na assíncrona, confirma o Kafka. No experimento científico, medimos a conclusão da persistência separadamente com o analisador Java.”

Essa carga curta não compara capacidade máxima, não inclui aquecimento científico e não confirma hipóteses do TCC. Os tempos dependem da máquina, do estado das aplicações e dos demais processos. Não use o menor p95 da demonstração para declarar uma arquitetura vencedora.

### G. Mostrar observabilidade e encerrar

Opção **11** para ver uma amostra Docker de recursos e logs; **0** para sair. A amostra não mede energia, custo operacional, Windows inteiro ou médias entre repetições. Zero em um contêiner parado indica indisponibilidade, não eficiência.

Uma distribuição sugerida para dez minutos: arquitetura e síncrona (3 min), assíncrona com pausa/retomada (4 min), k6 e interpretação (2 min), limitações e encerramento (1 min). Prepare e ensaie antes; não rode a campanha longa durante a banca.

## 5. Segurança e arquivos

- Opera somente no projeto interativo `tcc-java-2026`; confere os rótulos dos contêineres antes de parar/retomar o consumidor.
- Recusa ações de preparação, envio, pausa e carga se houver contêineres ativos do projeto experimental `tcc-entrega04`. Não misture apresentação e campanha.
- Não executa TRUNCATE, exclusão de registros, remoção de volumes ou reset de offsets. Não apaga mensagens/tópicos e não recompila o analisador nem as aplicações.
- Os eventos são sintéticos e permanecem no banco. Os envios manuais usam `source=demo-apresentacao-<sessão>`; k6 usa `source=demo-k6-<execução>`. UUIDs novos evitam sobrescrever conteúdo de demonstrações anteriores.
- Na saída normal, Ctrl+C ou SIGTERM, tenta retomar o consumidor **somente se este menu o tiver pausado**. Não encerra os demais serviços. Fechar abruptamente o computador/processo pode impedir essa limpeza.
- Se Docker ficar indisponível e a retomada não puder ser confirmada, use depois: `docker compose -p tcc-java-2026 start consumer`.

Arquivos locais em `.runtime/demonstracao/<sessão>/`, fora do Git: manifesto, ações TSV, JSONs enviados, respostas/consultas e subpastas k6 com console, resumo JSON e amostras comprimidas. Não são colocados em `.runtime/entrega04/` e não entram na contagem da campanha. Uma falha de transporte mantém o UUID para consulta; não provoque novo envio às cegas supondo que nada foi gravado.

## 6. Problemas comuns

| Problema | O que conferir |
|---|---|
| `Docker não está em execução` | Inicie o Docker no ambiente WSL usado pelo projeto. Não basta existir o comando. |
| Falta `curl` ou Python 3 | Prepare o WSL antes da banca. Não há bibliotecas Python externas para instalar. |
| Imagens Java ausentes | Prepare a implementação pelo README antes da apresentação; o menu deliberadamente não faz build. |
| k6 precisa baixar imagem | Use a opção 1 com internet antes da banca; depois a imagem fica local. |
| 404 mesmo após retomar | Confira UUID, inicialização do consumidor, logs, lag e eventual DLQ. O menu não converte falta de evidência em perda comprovada. |
| 202 com consumidor parado | É o comportamento esperado: confirma Kafka, não gravação. |
| Projeto experimental ativo | Aguarde o responsável encerrar o ensaio. O menu não o interrompe nem roda em paralelo. |
| Resposta errada ou k6 não aprovado | Leia a mensagem e os arquivos da sessão; não apresente essa execução como bem-sucedida. |

## 7. Verificação do próprio menu

Testes locais sem serviços (doubles de shell e biblioteca padrão Python):

```bash
bash demo/tests/test_menu.sh
python3 -m unittest discover -s demo/tests -v
```

Verificação real curta, **com escrita sintética e pausa/retomada do consumidor**:

```bash
bash demo/apresentacao.sh --smoke
```

Esse modo prepara serviços, verifica 201/200, 202/404 com consumidor parado, 200 após retomada e duas cargas de 2 eventos/s durante 3 s. Mantém os dados e retoma o consumidor em caso de saída tratável. Não é verificação somente de leitura: para isso use `--check`.

Para ajustar apenas a demonstração, sem mudar o protocolo congelado:

```bash
TCC_DEMO_RATE=2 TCC_DEMO_SECONDS=10 bash demo/apresentacao.sh
```

Limites do menu: 1..10 eventos/s e 1..30 s. Fontes técnicas: [k6 e resumos customizados](https://grafana.com/docs/k6/latest/results-output/end-of-test/custom-summary/), [checks e thresholds](https://grafana.com/docs/k6/latest/using-k6/checks/) e [Docker Compose port](https://docs.docker.com/reference/cli/docker/compose/port/). Os comandos e os resultados esperados também foram confrontados com os controllers Java e o Compose deste repositório.
