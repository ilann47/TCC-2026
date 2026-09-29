# TCC 2026 — REST síncrono versus comunicação orientada a eventos

Este repositório contém uma **implementação Java paralela** do protótipo experimental de processamento de registros de auditoria. A pesquisa compara o momento da confirmação e o comportamento diante de falhas nas variantes REST síncrona e Kafka assíncrona; **não** compara o desempenho de Java e Python.

- [Implementação Java, execução e testes](implementacao-java/README.md)
- [Especificação técnica e diagramas](implementacao-java/docs/especificacao/README.md)
- [Paridade e diferenças em relação ao protótipo Python](implementacao-java/docs/paridade.md)

A versão Python e o projeto LaTeX originais permanecem fora deste repositório, sem alteração. Nenhum resultado experimental definitivo é afirmado aqui. Use dados sintéticos; eventos e mensagens na DLQ podem conter informações sensíveis.
