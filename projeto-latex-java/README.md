# TCC — fonte LaTeX atual em Java

Revisão atual: [justificativa do painel em 24/11/2026](../entregas/2026-11-24-entrega-04-justificativa-painel/), com [PDF atualizado](../output/pdf/TCC-2026-justificativa-painel-2026-11-24.pdf), de 93 páginas. A seção 4.5.1 explicita que o painel foi implementado após a campanha como camada separada das aplicações Java, sem participar das medições ou dos recursos comparados. Distingue a consulta de resultados das demonstrações locais controladas pelo Python. Mantém as quatro telas de 23/11, as tecnologias na seção 4.6.1, a cronologia da Figura 17 e a declaração de IA com revisão pessoal confirmada em 24/11. Não houve novas medições, reclassificação ou mudança de resultados e conclusões. Os [primeiros ajustes de 24/11](../entregas/2026-11-24-entrega-04-ajustes-banca/), as [correções do parecer em 30/10](../entregas/2026-10-30-entrega-04-correcao-parecer/) e as demais entregas históricas permanecem preservados; os dados institucionais não foram inventados.

Este diretório é a fonte editável atual do TCC em Java, em evolução após a [Entrega 03](../entregas/entrega-03-java/README.md). O código executável está em [implementacao-java](../implementacao-java/README.md). As versões anteriores dos arquivos enviados ficam em [entregas](../entregas/README.md); seus números e capturas não foram reutilizados como evidência da campanha atual.

O arquivo principal é `modelo.tex`. Os capítulos ficam em `Capitulos/`, os metadados e a bibliografia em `Configuracoes/`, e os diagramas editáveis em `Diagramas/plantuml/` (`.puml` com PNG correspondente).

## Compilação

Com MiKTeX/TeX Live e BibTeX disponíveis, execute nesta pasta:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error modelo.tex
bibtex modelo
pdflatex -interaction=nonstopmode -halt-on-error modelo.tex
pdflatex -interaction=nonstopmode -halt-on-error modelo.tex
```

Para regenerar os PNG dos diagramas, use PlantUML nos arquivos `.puml`. O [PDF da Entrega 03](../entregas/entrega-03-java/TCC_Entrega03_Java.pdf) é histórico. O [PDF de 27/10](../entregas/2026-10-27-entrega-04-java-final/TCC-Entrega04-final.pdf) é o fechamento histórico da campanha; o [PDF de 30/10](../entregas/2026-10-30-entrega-04-correcao-parecer/TCC-Entrega04-correcoes.pdf) preserva a revisão do parecer. A edição atual acrescenta as capturas de `Imagens/painel/` e foi compilada em pasta isolada, sem executar nova medição. As três figuras de resultados usam páginas horizontais para facilitar a leitura.

O capítulo 5 segue ferramentas/piloto, modelo comum (a), síncrona (b), assíncrona (c), cenários e qualificação (d), métricas (e), trade-offs/hipóteses (f) e limitações. O capítulo 6 responde à pergunta, avalia objetivos e limita recomendações sem introduzir resultados novos. Resumo/abstract, método e declaração de IA foram atualizados. Orientadora: Professora Alessandra Bussador. Dados institucionais de banca/ficha continuam sem invenção e não implicam aprovação ou submissão.

Em 27/10/2026, após nove validações, a campanha concluiu 65 tentativas: 64 completas e uma parcial preservada, não 65 integralmente válidas. [Dados por execução/par e sensibilidades](../implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/RESULTADOS.md). As seis tabelas geradas podem ser reproduzidas por `render_final_tables.py`; n de conclusão com banco parado é quatro pares completos. A revisão A1 é pós-hoc nas primeiras 37 tentativas e declarada antes das 28 restantes.
