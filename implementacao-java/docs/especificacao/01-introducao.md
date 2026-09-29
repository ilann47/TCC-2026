> Links: [[README]] · [[02-analise-negocio]] · [[04-requisitos-funcionais]]

# 1. Introdução

## 1.1 Finalidade

O sistema é um protótipo experimental para observar como duas formas de comunicação influenciam o processamento de um registro de auditoria. A variante síncrona usa REST e confirma após uma transação no PostgreSQL. A variante assíncrona usa REST como porta de entrada, publica no Kafka e confirma ao cliente após o ACK do broker; outro processo consome e persiste posteriormente. As duas variantes compartilham o contrato, o hash e a regra de idempotência. O objetivo científico é analisar os comportamentos arquiteturais, e não oferecer um produto de auditoria comercial ou concluir que uma variante é universalmente superior.

## 1.2 Escopo

Dentro do escopo: receber evento, validar campos, calcular JSON/hash canônico, inserir uma vez por `event_id`, identificar duplicata/conflito, consultar registro, publicar com ACK, consumir com tentativa limitada, enviar falha à DLQ, confirmar offset e emitir marcos de observabilidade. O ambiente reproduzível inclui PostgreSQL 16, Kafka 3.9.1 e três processos Java em Docker Compose isolado.

Fora do escopo: login, autorização por usuário, interface web, edição/exclusão de registro, busca paginada, relatórios, retenção automatizada da DLQ, reprocessamento da DLQ, criptografia de campo, autenticação Kafka/PostgreSQL de produção, outbox, transação distribuída, “exactly once” de ponta a ponta, análise conclusiva de desempenho e migração do banco existente da implementação Python. Esses limites são importantes para não confundir um experimento controlado com uma plataforma pronta para produção.

## 1.3 A empresa ou produto responsável

Não há empresa contratante. O protótipo é um artefato acadêmico do TCC de Ilan Wendling Thoele, sob orientação da Professora Alessandra Bussador. Os nomes `order` e `created` nos exemplos representam dados sintéticos; o sistema não é um módulo de pedidos. A documentação segue a forma de especificação profissional, mas registra essa divergência em vez de atribuir requisitos a uma empresa inexistente.
