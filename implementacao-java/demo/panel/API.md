# Contrato do painel local de demonstração

Aplicativo local em `127.0.0.1:5666`, executado no WSL. Não é o produto Web
Dashboard da Grafana: controla o k6 da demonstração já existente. Não executa a
campanha, não aceita destinos/scripts/comandos arbitrários e não publica arquivos
brutos nem HTML exportado pelo k6.

| Método e rota | Contrato |
| --- | --- |
| `GET /api/state` | Token CSRF da instância, execução ativa e histórico de até 100 testes deste painel. Não inicia carga. |
| `GET /api/jobs/<UUID>` | Detalhe registrado, console limitado e métricas; 404 se não pertencer ao painel. |
| `POST /api/run` | JSON exato `{"variant":"sync" ou "async","rate":1..10,"seconds":1..30}`; inteiros, não booleanos. 202 com execução criada; 409 se já houver execução local ativa. |
| `POST /api/jobs/<UUID>/stop` | JSON `{}`. Interrompe somente o grupo de processos criado por este painel para esse teste. Resultado interrompido, nunca aprovado. |
| `POST /api/check` | JSON `{}`. Verifica Docker, imagens, cinco serviços e saúde das APIs, sem enviar eventos nem iniciar/parar serviços; 409 durante carga. |

Toda escrita exige `Host` local exato, `Origin` local da mesma origem,
`Content-Type: application/json` e `X-CSRF-Token` retornado por `/api/state`.
Limite de corpo: 4 KiB; chaves desconhecidas são recusadas. Sem CORS. Ativos
estáticos têm rotas fixas. Acesso não local e DNS rebinding são recusados.

O executor reutiliza `apresentacao.sh --run-sync/--run-async` com argumentos fixos,
sem shell interpolado, mantendo lock e bloqueios de campanha/carga concorrente.
O painel desliga o Web Dashboard nativo no filho: fechar a aba não controla a
vida do teste e o painel permanece disponível depois dele. Não baixa imagens,
não reconstrói Java, não muda Compose nem reinicia os cinco serviços.

Métricas ao vivo são provisórias, filtradas por `phase=demo`. O resumo final do
mesmo teste é a fonte dos valores finais. HTTP 202 não é confirmação de commit.
Respostas inválidas e iterações não iniciadas são separadas; código não zero ou
resumo ausente/inválido significa falha. Não há repetição automática. Execuções
pendentes encontradas após reiniciar o painel ficam interrompidas, sem retomada.
O watchdog limita cada processo filho a 150 segundos (preparação de leitura,
carga de até 30 s, término de requisições e limpeza).

Histórico e console próprios: `.runtime/demonstracao/painel/jobs/`. Os arquivos
originais do teste continuam em `.runtime/demonstracao/<sessão>/k6-<UUID>-<variante>/`.
Nada altera evidências, diário, classificação ou resultados da campanha.
