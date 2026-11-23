# Explorador local de resultados do TCC

Front-end React, Vite e Tailwind com componentes shadcn/ui instalados pelo
registro oficial. Os gráficos SVG mostram pontos por execução e conectam
apenas repetições com os dois valores elegíveis.

A tela abre no **Modo Banca**, em carga constante a 48 eventos/s. O roteiro
tem quatro etapas clicáveis, sem sair da página:

1. **Método:** o que 201 e 202 confirmam, fluxos de cada variante, desenho
   pareado, janelas da coleta e por que há uma parcial.
2. **Resultados:** três recortes da defesa, gráficos HTTP/commit separados,
   legenda de p95/par/diferença e cartões **O que mostrar** / **Como explicar
   à banca**, calculados a partir do mesmo relatório verificado.
3. **Falhas:** destinos de cada aceite e recuperação original versus leitura
   exploratória, sem transformar os 14 eventos da DLQ em gravações.
4. **Conclusão:** decisões de projeto, apoio e limites das hipóteses e uma
   fala de encerramento compatível com os dados.

Os destaques usam a análise principal A1 e mudam com o cenário. A lateral
seleciona indicadores úteis para cada explicação: não exibe CPU de componentes
parados como evidência de eficiência. A tabela de todas as repetições e os 16
indicadores continuam disponíveis ao expandir **Conferir os valores por repetição**
ou **Consultar dados completos**. **Outras cargas e rajada** reúne os sete recortes
em uma matriz síncrona / assíncrona. Auditoria, hashes e listas extensas ficam
recolhidos, acessíveis para responder perguntas, não como conteúdo principal.
Nenhuma informação científica foi apagada. As diferenças relativas usam a média síncrona dos
mesmos pares elegíveis. A taxa de gravação divide o total gravado pelo
total enviado, sem presumir que toda gravação veio de um aceite HTTP.
**Explorar resultados** abre os filtros de carga, rajada e
sensibilidade estrita. A apresentação dos resultados não precisa da
demo do k6 nem dos serviços da aplicação; o painel local ainda precisa
do servidor Python unificado e dos relatórios verificados.

## Uso normal: um único serviço na porta 5666

Dentro de `implementacao-java`, no WSL:

    docker compose up -d

No PowerShell, na mesma pasta, use `./Iniciar-TCC.ps1`: ele sobe esse Compose e
mantém a sessão WSL necessária em segundo plano, sem um segundo servidor de UI.

O serviço `painel` constrói a interface em uma etapa Node e a serve em uma imagem
Python com Docker CLI. Não precisa de Python/Node/Vite em outro terminal.
Resultados: http://localhost:5666/resultados. A demonstração fica em `/`.
Para atualizar somente o painel: `docker compose build painel` e
`docker compose up -d --no-deps painel`, com nenhuma carga ativa.
O histórico usa a pasta existente; o repositório e os resultados são montados
somente leitura. O socket Docker é acesso administrativo: o ambiente é exclusivamente
local e não deve ser publicado na rede. Veja o roteiro em `demo/README.md`.

### Alternativa manual

Com o contêiner `painel` parado, é possível desenvolver sem empacotar a imagem.
No diretório desta aplicação, com Node disponível para compilar:

    npm ci
    npm test
    npm run build

Depois, dentro de `implementacao-java`, no WSL:

    python3 demo/panel.py

Acesse http://localhost:5666/resultados e alterne para a demonstração pelo link
do topo. O Python serve o build de `dist/` sob `/resultados/` e a demonstração
em `/`. Não há processo Node/Vite necessário em tempo de execução, proxy,
iframe ou chamada entre portas. A porta alternativa de `panel.py --port` também
funciona porque os links e a API usam a mesma origem. Build ausente é erro
explícito, sem fallback para o painel legado.

## Desenvolvimento opcional

Para editar com recarga, `npm run dev` continua disponível na porta 5667,
em http://localhost:5667/resultados/. `npm run preview` é apenas uma prévia
isolada do build, não o comando de apresentação. Ambos escutam somente em loopback.
Se necessário, configure `TCC_REPORT_PYTHON` para o Python local nesses modos.

O endpoint GET `/api/campaign` usa o relatório científico já existente e
verifica os hashes da campanha e da reanálise exploratória antes de carregar
os dados em memória. A tela não grava os arquivos científicos, não executa
k6 nem chama as APIs Java da demonstração. O servidor unificado e o modo de
desenvolvimento usam a mesma montagem do relatório (`demo/results_report.py`),
incluindo a reanálise exploratória verificada, sem mudar a análise original.

A regra A1 conserva cinco pares HTTP na parada do PostgreSQL e exclui R3 da
conclusão primária, totalizando quatro pares de commit. A regra estrita
exclui esse par dos indicadores comparativos. No cenário de consumidor
parado não existe contraparte síncrona. O resultado exploratório de
recuperação não modifica o resultado original.
