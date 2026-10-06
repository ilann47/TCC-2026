# TCC — fonte LaTeX da Entrega 03 Java

Este diretório é a fonte editável da [Entrega 03 em Java](../entregas/entrega-03-java/README.md). O código executável está em [implementacao-java](../implementacao-java/README.md). As versões anteriores dos arquivos enviados ficam em [entregas](../entregas/README.md); seus números e capturas não foram reutilizados como evidência do Java.

O arquivo principal é `modelo.tex`. Os capítulos ficam em `Capitulos/`, os metadados e a bibliografia em `Configuracoes/`, e os diagramas editáveis em `Diagramas/plantuml/` (`.puml` com PNG correspondente).

## Compilação

Com MiKTeX/TeX Live e BibTeX disponíveis, execute nesta pasta:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error modelo.tex
bibtex modelo
pdflatex -interaction=nonstopmode -halt-on-error modelo.tex
pdflatex -interaction=nonstopmode -halt-on-error modelo.tex
```

Para regenerar os PNG dos diagramas, use PlantUML nos arquivos `.puml`. O PDF já compilado para envio está em [TCC_Entrega03_Java.pdf](../entregas/entrega-03-java/TCC_Entrega03_Java.pdf).

O texto diferencia funcionalidades implementadas, verificações funcionais, instrumentos experimentais implementados e campanha comparativa ainda pendente. O capítulo 5 foi iniciado com a comparação documentada dos geradores, o piloto e a validação do modelo comum. Hipóteses comparativas permanecem inconclusivas; o capítulo 6 não foi habilitado sem a campanha definitiva. Não apresenta ensaios curtos como se fossem os resultados das repetições exigidas.
