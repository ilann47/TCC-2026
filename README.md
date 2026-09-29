# TCC 2026 — REST síncrono versus comunicação orientada a eventos

Este repositório reúne o texto editável do TCC, diagramas, entregas acadêmicas e duas implementações do protótipo experimental de processamento de registros de auditoria. A pesquisa compara a variante REST síncrona com a variante assíncrona orientada a eventos; **não** compara o desempenho de Java e Python.

| Pasta | Conteúdo |
|---|---|
| [projeto-latex](projeto-latex/README.md) | Fonte atual do TCC (`modelo.tex`), bibliografia, diagramas e implementação Python original. |
| [implementacao-java](implementacao-java/README.md) | Implementação Java paralela, em módulos Maven, com APIs síncrona e assíncrona, consumidor, testes e Docker Compose. |
| [entregas](entregas/README.md) | PDF e apresentação das entregas acadêmicas selecionadas, identificadas por etapa. |

Os arquivos originais fora deste checkout não foram alterados. O material em `projeto-latex` foi copiado da versão da Entrega 03 de 29/09/2026. Os PDFs de artigos científicos de terceiros não estão redistribuídos aqui; seus dados bibliográficos e citações estão nos arquivos `.bib` e no texto. Também não foram enviados caches, ambientes locais, credenciais, arquivos temporários ou versões intermediárias duplicadas.

O [projeto Java](implementacao-java/README.md) e o [projeto Python](projeto-latex/implementacao/README.md) são alternativas de implementação do mesmo experimento, não duas etapas de um único processamento. Nenhum resultado experimental definitivo é afirmado neste repositório. Use dados sintéticos; eventos e mensagens na DLQ podem conter informações sensíveis.
