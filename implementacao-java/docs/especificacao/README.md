> Links: [[01-introducao]] · [[02-analise-negocio]] · [[03-der]] · [[04-requisitos-funcionais]] · [[06-prototipos]] · [[07-dicionario-de-dados]] · [[08-diagramas-classe]] · [[09-diagramas-sequencia]] · [[10-requisitos-nao-funcionais]] · [[relatorio-conformidade]]

# Especificação técnica da implementação Java

Esta documentação versionável descreve **o código Java existente** e seus limites experimentais. Identificadores `RFxxx`, `RNxxx` e `UCxxx` são estáveis; `E1` etc. designam exceções dentro de cada caso de uso. Diagramas Mermaid refletem a arquitetura implementada. O código, a migração SQL e os testes prevalecem quando houver divergência; divergências devem ser corrigidas aqui.

1. [Introdução e escopo](01-introducao.md)
2. [Análise do problema e envolvidos](02-analise-negocio.md)
3. [DER](03-der.md)
4. [Requisitos funcionais](04-requisitos-funcionais.md)
5. Casos de uso: [UC001](05-casos-de-uso/uc001-registrar-sincrono.md), [UC002](05-casos-de-uso/uc002-aceitar-assincrono.md), [UC003](05-casos-de-uso/uc003-consumir-evento.md), [UC004](05-casos-de-uso/uc004-consultar-e-monitorar.md)
6. [Protótipos de interface](06-prototipos.md)
7. [Dicionário de dados](07-dicionario-de-dados.md)
8. [Diagrama de classes](08-diagramas-classe.md)
9. [Diagramas de sequência](09-diagramas-sequencia.md)
10. [Requisitos não funcionais](10-requisitos-nao-funcionais.md)

O [relatório de conformidade](relatorio-conformidade.md) registra o que foi implementado, validado e o que permanece pendente; o [plano de refatoração](plano-refatoracao.md) prioriza mudanças futuras sem apresentá-las como realizadas. A operação está descrita em [README da implementação](../../README.md) e a [paridade com Python](../paridade.md).

## Divergências deliberadas do modelo documental

Este é um **protótipo acadêmico sem interface gráfica, empresa comercial, usuários autenticados, cadastros CRUD ou relatórios de negócio**. As seções correspondentes documentam essa ausência, em vez de inventar funcionalidades. O ator “aplicação cliente” é outro sistema ou script de carga; o operador prepara o ambiente experimental. A migração Flyway destina-se exclusivamente ao banco novo da versão Java.
