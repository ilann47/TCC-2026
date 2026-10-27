# Demonstração ao vivo com menu

Este roteiro permite apresentar o protótipo sem depender de uma IA para executar comandos. Você escolhe as etapas no terminal. O menu explica o que está fazendo, guarda o último UUID e mostra uma fala sugerida. **Não reinicia a campanha definitiva de 65 tentativas, não inicia `campaign.sh` e não produz resultados científicos definitivos.** A campanha concluída e os planos históricos permanecem separados desta demonstração.

Para entender cada linha da tabela e ensaiar a explicação, leia o [guia completo das 45 métricas e falas para a banca](METRICAS-E-FALAS.md). Ele inclui unidades, cálculos, cuidados, exemplo real versionado, perguntas frequentes e roteiro de dez minutos.

## 1. Abrir o menu

O menu executa em **WSL/Ubuntu ou Linux com Bash**. No Windows, você pode abri-lo pelo PowerShell usando `wsl`, ou entrar primeiro em um terminal Ubuntu/WSL.

### Pelo PowerShell no Windows

Abra o Windows Terminal/PowerShell e cole:

```powershell
wsl --cd /mnt/c/Users/ilan.wendling/OneDrive/sistemasDeInformacao/TCC/TCC-2026/implementacao-java -- bash demo/apresentacao.sh
```

A chamada abre o menu no terminal atual, mas o Bash e os comandos Docker executam pelo WSL. Os arquivos continuam na pasta do Windows, montada em `/mnt/c/`. Neste projeto, Java e k6 executam em contêineres. **O k6 mostra o teste no terminal; não há uma janela k6 para abrir neste roteiro.** O Swagger abre separadamente no navegador do Windows.

### Já dentro do Ubuntu/WSL

No computador atual:

```bash
cd /mnt/c/Users/ilan.wendling/OneDrive/sistemasDeInformacao/TCC/TCC-2026/implementacao-java
bash demo/apresentacao.sh
```

Se o repositório estiver em outra pasta, ajuste o caminho depois de `--cd` no PowerShell ou entre em `implementacao-java` dessa cópia no WSL. O script encontra seus arquivos pelo próprio diretório e não depende de caminhos pessoais fixos no código. Não execute `bash demo/apresentacao.sh` diretamente no PowerShell ou Git Bash.

### Preparar antes da banca

Pré-requisitos: Docker com Compose, `curl`, Python 3 e as imagens Java já preparadas. Python usa apenas a biblioteca padrão para criar/formatar JSON e verificar UUID/status; não é outra implementação do sistema. Java e k6 executam em contêineres. O menu informa qualquer pré-requisito ausente; não instala pacotes no sistema.

**Antes da banca**, use a opção **1**. Ela inicia o projeto `tcc-java-2026` sem recompilar, aguarda a saúde das APIs e baixa a imagem fixada do k6 se estiver ausente. Isso pode exigir internet; não deixe downloads/builds para os dez minutos de apresentação. Se faltarem imagens Java, siga a preparação do [README da implementação](../README.md). Não reconstrua as imagens medidas da campanha congelada apenas para demonstrar.

Uma conferência pelo PowerShell **sem enviar eventos, iniciar/parar contêineres ou baixar imagens**:

```powershell
wsl --cd /mnt/c/Users/ilan.wendling/OneDrive/sistemasDeInformacao/TCC/TCC-2026/implementacao-java -- bash demo/apresentacao.sh --check
```

Ou, já dentro de `implementacao-java` no WSL:

```bash
bash demo/apresentacao.sh --check
```

`--check` apenas confere a prontidão. Se algum serviço estiver parado ou faltar uma imagem, ele informa o problema. Use a opção **1** do menu para preparar/iniciar o ambiente. Se faltar uma dependência, prepare-a antes da banca conforme o README da implementação.

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
| 13 | Comparar lado a lado: carga normal, falha do PostgreSQL ou parada do consumidor. Coleta persistência, recursos e destinos em ambiente isolado. |
| 14 | Mostrar a última comparação concluída, sem gerar carga, e indicar o relatório HTML para o navegador. |
| 0 | Sair; tentar retomar o consumidor caso este menu o tenha pausado. |

Depois de cada ação, leia o resultado e pressione Enter para voltar. O menu mantém o UUID do último envio durante a sessão. Não é necessário copiar UUIDs para executar as opções 5 e 7. Para usar o Swagger em paralelo, copie o UUID exibido e consulte `GET /audit/{eventId}` na definição síncrona.

## 4. Passo a passo e falas para a banca

Comece com **1** para preparar e **2** para conferir os serviços. Depois siga esta sequência, pressionando Enter entre as ações:

| Etapa | Opções do menu, nesta ordem | Resultado a mostrar |
|---|---|---|
| Síncrona | **3**, **5** | 201 e consulta 200. |
| Assíncrona normal | **4**, **7**, **5** | 202 e consulta 200 após processamento. |
| Consumidor parado | **6**, **4**, **5**, **8** | Novo evento com 202, ainda ausente do banco (404), e eventual lag. |
| Retomada | **7**, **5** | O mesmo evento passa a ser encontrado no banco, se a persistência for confirmada. |
| Carga curta | **9**, **10** | k6 nas duas APIs, com consumidor retomado, 5 eventos/s por 20 s em cada teste. |
| Recursos e saída | **11**, **0** | Amostra de recursos/logs e encerramento do menu, mantendo os serviços. |

Deixe comparações completas prontas **antes da banca** com **13**, cenário **1**. Use **14** durante a apresentação para ver a última tabela e abrir seu HTML sem repetir a carga. Confira o cenário/UUID exibidos. Veja a seção 8 para os tempos e o isolamento desses ensaios.

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

Sair do menu não desliga as APIs, o Kafka ou o PostgreSQL. O menu tenta retomar o consumidor somente se ele próprio o tiver pausado. Se desejar parar o projeto depois da apresentação, sem apagar os volumes, execute no WSL dentro de `implementacao-java`: `docker compose -p tcc-java-2026 stop`. Não use remoção de volumes para encerrar uma demonstração.

Uma distribuição sugerida para dez minutos: arquitetura e síncrona (3 min), assíncrona com pausa/retomada (4 min), k6 e interpretação (2 min), limitações e encerramento (1 min). Prepare e ensaie antes; não rode a campanha longa durante a banca.

## 5. Segurança e arquivos

- As opções 1..12 operam no projeto interativo `tcc-java-2026`; conferem os rótulos dos contêineres antes de parar/retomar o consumidor. A opção 13 usa o projeto experimental isolado, descrito na seção 8; a 14 apenas lê o último relatório.
- Recusa ações de preparação, envio, pausa e carga se houver contêineres ativos do projeto experimental `tcc-entrega04`. Não misture apresentação e campanha.
- Nas opções 1..12, não executa TRUNCATE, exclusão de registros, remoção de volumes ou reset de offsets. Não apaga mensagens/tópicos e não recompila o analisador nem as aplicações. A opção 13 é a exceção explícita: reinicia somente a tabela experimental isolada, conforme a seção 8; nunca o banco principal.
- Os eventos são sintéticos e permanecem no banco. Os envios manuais usam `source=demo-apresentacao-<sessão>`; k6 usa `source=demo-k6-<execução>`. UUIDs novos evitam sobrescrever conteúdo de demonstrações anteriores.
- Na saída normal, Ctrl+C ou SIGTERM, tenta retomar o consumidor **somente se este menu o tiver pausado**. Não encerra os demais serviços. Fechar abruptamente o computador/processo pode impedir essa limpeza.
- Se Docker ficar indisponível e a retomada não puder ser confirmada, use depois: `docker compose -p tcc-java-2026 start consumer`.

Arquivos locais das opções 1..12 em `.runtime/demonstracao/<sessão>/`, fora do Git: manifesto, ações TSV, JSONs enviados, respostas/consultas e subpastas k6 com console, resumo JSON e amostras comprimidas. Essas opções não colocam arquivos em `.runtime/entrega04/`. Já a comparação 13 reutiliza o coletor isolado e guarda ali suas evidências brutas com `kind=validation`, sem entrar na contagem da campanha definitiva. Uma falha de transporte mantém o UUID para consulta; não provoque novo envio às cegas supondo que nada foi gravado.

## 6. Problemas comuns

| Problema | O que conferir |
|---|---|
| `bash` não encontrado ou comando recusado no PowerShell | Use a chamada completa com `wsl --cd ... -- bash demo/apresentacao.sh`. O script precisa de Bash no WSL/Linux, não de execução direta no PowerShell/Git Bash. |
| O caminho de `--cd` não existe | Ajuste o caminho Linux da pasta do clone; no WSL, a unidade C: aparece em `/mnt/c/`. |
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

## 8. Comparação lado a lado — opções 13 e 14

**Para mostrar as métricas na banca:** execute **13 → 1** antes da apresentação. Depois, use **14** para consultar a tabela já pronta e abra `relatorio.html` no navegador pelo caminho exibido. A tabela do terminal adapta as três colunas à largura da janela; o HTML funciona offline e permite imprimir/salvar PDF. A opção 14 não repete os testes. Use zoom ou tela cheia do navegador ao projetar.

O comparador reutiliza `experimento/run.sh` e o analisador Java existente, **sem modificar a instrumentação congelada**. k6 gera a carga; logs de marcos/commit, exportação do PostgreSQL, Kafka e amostras de Docker alimentam o relatório. Não é apenas um cronômetro de HTTP nem uma tabela com valores estimados. Todos os arquivos ficam locais e são identificados como `presentation_comparison_not_definitive`.

### Cenários disponíveis na opção 13

| Escolha | O que executa | Parâmetros padrão |
|---|---|---|
| 1 — normal | Síncrona e depois assíncrona, separadamente. Recuperação: não se aplica. | 5 eventos/s, 5 s de aquecimento, 20 s medidos e 10 s de drenagem por versão; 32 VUs. |
| 2 — PostgreSQL | Mesma dependência interrompida por 5 s em cada versão. | 5 eventos/s, 10 s de aquecimento, 90 s medidos, 20 s de drenagem; 64 VUs. |
| 3 — consumidor | Consumidor interrompido por 5 s, somente na assíncrona. | Mesmos parâmetros do cenário de falha. Síncrona: **não se aplica**, pois ela não tem consumidor. |

No cenário normal, `TCC_DEMO_RATE` (1..10/s) e `TCC_DEMO_SECONDS` (6..30 s para comparar) ajustam a carga. Nos cenários de falha, somente a taxa é ajustável por essa variável; a janela de 90 s é mantida para permitir observar recuperação. A falha começa aproximadamente em um terço da janela; o manifesto registra os instantes efetivos. Os 5 s são de indisponibilidade solicitada, não um resultado de recuperação.

**Há preparação, intervalo de 12 s após aquecimento, coleta e exportação além do tempo medido.** A comparação normal leva alguns minutos; falhas levam mais. Não execute todas as opções nos dez minutos da apresentação. Deixe o relatório pronto e use o teste HTTP curto (9/10) e uma pausa manual do consumidor para ilustrar o funcionamento ao vivo.

### Métricas e leitura correta

O resumo abaixo agrupa as medidas. As definições individuais e as falas sugeridas estão no [guia das métricas](METRICAS-E-FALAS.md).

| Grupo | O que aparece nas duas colunas |
|---|---|
| Tempos | HTTP média/mediana/p95/p99; envio→resposta; envio→commit média/p95/p99 e quantidade de commits observados. |
| Vazão e contagens | Registros gravados/s na janela; enviados, aceitos, gravados na janela e gravados até o fim da coleta. |
| Erros e integridade | Códigos HTTP, erros HTTP/contrato, iterações não iniciadas, DLQ, pendentes, aceitos sem destino reconciliado, gravações sem confirmação HTTP, UUIDs duplicados no banco, divergências de conteúdo/hash e reentregas idempotentes. |
| Fila | Pico de aceitos ainda não gravados; pico amostrado de lag Kafka (não se aplica à síncrona). |
| Recursos | CPU e memória médias dos componentes, soma do fluxo; consumo de k6/observador separado. |
| Recuperação | Primeiro commit após retomada, drenagem completa dos aceitos pendentes e confirmação de recuperação sustentada. Apenas cenários de falha. |

O p95 representa o tempo até o qual ficaram 95% das observações. O tempo de persistência inclui **somente os registros com commit observado**, portanto leia a quantidade de amostras e os destinos pendentes/DLQ junto com a latência. A taxa de gravação usa apenas commits dentro da janela medida; não soma drenagem posterior como se tivesse ocorrido durante a carga.

O total síncrono soma `sync-api + postgres`; o assíncrono soma `async-api + consumer + postgres + kafka`. A soma das médias de CPU usa a escala Docker (100% ≈ um núcleo lógico), não é percentual de todo o computador nem fica limitada a 100%. Memória é a exibida pelo Docker, em MiB, não memória global do Windows. O Kafka experimental também é iniciado para infraestrutura/coleta no ensaio síncrono, mas não pertence ao seu caminho de negócio e não entra naquele total. Os componentes são discriminados para deixar esse recorte explícito. Fonte: [Docker stats, CPU/memória e tratamento de cache](https://docs.docker.com/reference/cli/docker/container/stats/).

Recuperação sustentada usa o critério existente: três janelas completas consecutivas de 10 s após retomada, pelo menos 90% da taxa-alvo gravada/s, sem erros HTTP, pendências/lag limitados e observação saudável. “Não observada na janela” **não é zero**. Recuperar a vazão não prova que toda mensagem anterior foi salva; uma mensagem enviada à DLQ continua não gravada. Zero UUID duplicado não significa zero reentrega, pois a persistência é idempotente.

### Isolamento, arquivos e preparação

As duas versões recebem conteúdo determinístico do mesmo dataset; o número efetivamente enviado pode diferir em uma iteração na fronteira ou por saturação, e é mostrado. São execuções sequenciais, síncrona primeiro, com a mesma configuração de imagens/gerador/instrumentação. Há apenas uma execução por versão: **não permite declarar vencedor ou substituir a campanha científica**.

O comparador usa exclusivamente `tcc-entrega04`, sem portas publicadas. Recusa projeto experimental ativo ou outro comparador com lock. Reinicia **somente a tabela desse banco experimental** entre execuções; o runner recusa dados de origem não experimental. Não apaga volumes, não altera eventos/banco do projeto principal `tcc-java-2026`, não para projetos alheios, não inicia `campaign.sh` e não recompila imagens. Ao terminar ou tratar Ctrl+C, tenta encerrar seus processos e para o projeto experimental. Em encerramento forçado do terminal/computador, confira `docker ps` antes de prosseguir.

O projeto interativo pode permanecer ativo para o Swagger. Seus contêineres e outros programas competem por recursos: esta é uma demonstração, não o ambiente controlado da campanha. Nenhum experimento definitivo deve ocorrer simultaneamente. Não inicie outro executor manual enquanto esta comparação estiver rodando; o lock protege comparadores, não substitui a coordenação com comandos externos.

Arquivos:

- `.runtime/demonstracao/comparacao-<dataset>/`: `comparacao.txt`, `comparacao.json`, `relatorio.html`, consoles e log de controle.
- `.runtime/entrega04/<run>-<variante>/`: evidências brutas reais, manifesto, checksums e resumo do analisador. Permanecem após a parada do projeto.
- `.runtime/demonstracao/ultima-comparacao.json`: aponta **somente à última comparação concluída**. Uma nova tentativa malsucedida não substitui silenciosamente esse relatório; confira cenário e UUID ao reapresentar.

Além dos pré-requisitos do menu, precisa de `flock`, `setsid` e `timeout` (usuais no Ubuntu/WSL) e da imagem `tcc-pilot-analyzer:local`. Se estiver preparando um clone novo, sem imagens calibradas a preservar, construa antes da banca:

```bash
docker build -t tcc-pilot-analyzer:local experimento/analyzer
```

Se já houver campanha/calibração congelada nesse computador, **não reconstrua/substitua suas imagens** apenas para demonstrar; o comparador exige as imagens locais existentes e falha se faltarem. Ele nunca baixa nem compila automaticamente.

Comandos equivalentes, fora do menu:

```bash
bash demo/comparar.sh normal
bash demo/comparar.sh postgres-stop
bash demo/comparar.sh consumer-stop
python3 demo/comparison_report.py --latest
```

Teste de integração curto: `bash demo/comparar.sh --smoke` (2 eventos/s, 2 s de aquecimento, 10 s medidos, 5 s de drenagem, cada versão). Ele grava dados sintéticos **somente no ambiente experimental**, exige imagens prontas e não mede recuperação.

Fala sugerida: “Aqui eu separo duas perguntas: quanto o cliente esperou pela resposta e quando o banco terminou a gravação. Na assíncrona, o 202 confirma o Kafka; por isso eu não comparo esse tempo como se ele significasse a mesma conclusão do 201. A tabela também mostra o custo dos componentes e o destino de cada aceito. Estes números são desta execução de demonstração; a conclusão do TCC depende das repetições do experimento.”
