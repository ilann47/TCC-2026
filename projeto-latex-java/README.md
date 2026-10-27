# TCC — fonte LaTeX atual em Java

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

Para regenerar os PNG dos diagramas, use PlantUML nos arquivos `.puml`. O [PDF da Entrega 03](../entregas/entrega-03-java/TCC_Entrega03_Java.pdf) é histórico, não um PDF atualizado da campanha. Não compile nem renderize enquanto o controlador estiver medindo: a revisão visual da próxima versão será feita após os experimentos.

O texto diferencia funcionalidades implementadas, verificações funcionais, instrumentos experimentais implementados e campanha comparativa ainda pendente. O capítulo 5 foi iniciado com a comparação documentada dos geradores, o piloto e a validação do modelo comum. Hipóteses comparativas permanecem inconclusivas; o capítulo 6 não foi habilitado sem a campanha definitiva. Não apresenta ensaios curtos como se fossem os resultados das repetições exigidas.

Em 27/10/2026, as [nove validações R2](../implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/README.md) foram aprovadas mantendo 48 eventos/s, e o protocolo reduzido foi congelado para 65 execuções. Método e capítulo parcial registram essa aprovação separadamente da análise definitiva. O andamento efetivo é o diário do controlador, não um estado presumido por este README.
