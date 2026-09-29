# Entrega 03 — versão Java

- [TCC em PDF](TCC_Entrega03_Java.pdf): fechamento do desenvolvimento, todos os diagramas UML, banco de dados e arquitetura.
- [Apresentação de 10 minutos](Apresentacao_Entrega03_Java_10min.pptx): dez slides com notas de fala.
- [Fonte editável do TCC](../../projeto-latex-java/README.md).
- [Código executável e instruções](../../implementacao-java/README.md).

Esta é a versão atual da entrega; [a Entrega 03 anterior](../entrega-03/) permanece como histórico. O projeto Java passou em `mvnw verify` localmente em 29/09/2026. Também iniciou com `docker compose up --build -d` no WSL: as duas APIs ficaram prontas, e gravações sintéticas pelos caminhos síncrono e assíncrono foram consultadas no banco. O [workflow de integração contínua](https://github.com/ilann47/TCC-2026/actions/runs/36627197788) verificou os fluxos principais e um smoke de interrupção do PostgreSQL. O experimento quantitativo definitivo, inclusive as repetições de carga e análise estatística, continua pendente. A resposta `202` da API assíncrona confirma o ACK do Kafka, não a persistência do evento.
