# TCC 2026 — REST síncrono versus comunicação orientada a eventos

Este repositório reúne o texto editável do TCC, diagramas, entregas acadêmicas e o protótipo experimental de processamento de registros de auditoria. As duas variantes são implementadas em Java: uma usa comunicação REST síncrona e a outra usa comunicação assíncrona orientada a eventos.

| Pasta | Conteúdo |
|---|---|
| [projeto-latex-java](projeto-latex-java/README.md) | Fonte atual do TCC (`modelo.tex`), bibliografia e diagramas alinhados ao código Java. |
| [implementacao-java](implementacao-java/README.md) | Implementação da entrega atual: módulos Maven, APIs síncrona e assíncrona, consumidor, testes e Docker Compose. |
| [referencias](referencias/README.md) | Catálogo bibliográfico compartilhado pelas entregas: 12 artigos na cópia local, três PDFs redistribuíveis no GitHub e licenças individuais. |
| [entregas](entregas/README.md) | PDF e apresentação das entregas acadêmicas selecionadas, identificadas por etapa. |

Somente três PDFs de artigos científicos de terceiros, com [licenças de redistribuição verificadas](referencias/DIREITOS_AUTORAIS.md), são publicados aqui. Os outros nove permanecem na cópia local, com links no catálogo; os dados bibliográficos e citações também estão nos arquivos `.bib` e no texto. Não foram enviados caches, ambientes locais, credenciais ou arquivos temporários. Os diagramas da Entrega 03 Java distinguem o banco e as funções efetivamente implementados das extensões planejadas.

As versões anteriores dos arquivos enviados ficam em [entregas](entregas/README.md); seus resultados e capturas não são atribuídos à implementação Java atual. Nenhum resultado experimental definitivo é afirmado neste repositório. Use dados sintéticos; eventos e mensagens na DLQ podem conter informações sensíveis.

O [piloto de instrumentação](implementacao-java/experimento/README.md) usa k6 e um analisador Java para conferir resposta HTTP, conclusão da persistência e conteúdo gravado. As evidências de cada execução são locais, em `implementacao-java/.runtime/pilot/`. Este piloto não substitui os cenários definitivos nem antecipa resultados do TCC.

A [preparação da Entrega 04](entregas/2026-10-06-entrega-04-java-preparacao/) acrescenta validação do modelo comum, idempotência, falhas e recuperação em ambiente isolado, com capítulo 5 parcial e apresentação. O protocolo de [experimentação](implementacao-java/experimento/PROTOCOLO-ENTREGA04.md) explicita o que ainda falta: calibração, congelamento, repetições e conclusão baseada na campanha completa. O pacote não é anunciado como entrega final pronta para o portal.
