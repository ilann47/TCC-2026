# TCC 2026 — REST síncrono versus comunicação orientada a eventos

Este repositório reúne o texto editável do TCC, diagramas, entregas acadêmicas e o protótipo experimental de processamento de registros de auditoria. A **Entrega 03 atual usa Java** nas duas variantes. A pesquisa compara comunicação REST síncrona com comunicação assíncrona orientada a eventos; **não** compara o desempenho de Java e Python.

| Pasta | Conteúdo |
|---|---|
| [projeto-latex-java](projeto-latex-java/README.md) | Fonte atual do TCC (`modelo.tex`), bibliografia e diagramas alinhados ao código Java. |
| [implementacao-java](implementacao-java/README.md) | Implementação da entrega atual: módulos Maven, APIs síncrona e assíncrona, consumidor, testes e Docker Compose. |
| [projeto-latex](projeto-latex/README.md) | Versão anterior baseada em Python, preservada como histórico; não é a fonte da Entrega 03 Java. |
| [entregas](entregas/README.md) | PDF e apresentação das entregas acadêmicas selecionadas, identificadas por etapa. |

Os PDFs de artigos científicos de terceiros não são redistribuídos aqui; seus dados bibliográficos e citações estão nos arquivos `.bib` e no texto. Também não foram enviados caches, ambientes locais, credenciais ou arquivos temporários. Os diagramas da Entrega 03 Java distinguem o banco e as funções efetivamente implementados das extensões planejadas.

O [projeto Python anterior](projeto-latex/implementacao/README.md) permanece apenas como histórico. Seus resultados e capturas não são atribuídos à versão Java. Nenhum resultado experimental definitivo é afirmado neste repositório. Use dados sintéticos; eventos e mensagens na DLQ podem conter informações sensíveis.
