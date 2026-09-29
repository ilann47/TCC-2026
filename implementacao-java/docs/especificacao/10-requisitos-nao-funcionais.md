> Links: [[README]] · [[04-requisitos-funcionais]] · [[relatorio-conformidade]]

# 10. Requisitos não funcionais

Estes critérios descrevem propriedades implementadas ou limites observáveis; não são metas de desempenho inventadas. A validação definitiva depende da execução do protocolo experimental.

## 10.1 Segurança

| ID | Critério | Implementação/limite |
|---|---|---|
| RNF001 | Segredos não versionados | Senha de banco via ambiente; `.runtime/` e `.env` ignorados pelo Git |
| RNF002 | Portas externas restritas | Compose publica serviços apenas em `127.0.0.1` |
| RNF003 | Logs sem payload e credenciais | `MilestoneLog` aceita somente campos de metadados enumerados |
| RNF004 | Tráfego experimental, não de produção | Kafka sem TLS/ACL e APIs sem autenticação; não expor em rede pública |

## 10.2 Desempenho

| ID | Critério | Implementação/limite |
|---|---|---|
| RNF005 | ACK Kafka individual limitado | `DELIVERY_TIMEOUT_MS`, padrão 10 s |
| RNF006 | Tentativas de banco limitadas | Padrão 3 tentativas, esperas de 500 ms e 1 s, teto configurável de 5 s |
| RNF007 | Métricas interpretáveis | HTTP síncrono, ACK assíncrono e commit final são marcos distintos; não há throughput/latência alvo pré-afirmado |

## 10.3 Disponibilidade e resiliência

| ID | Critério | Implementação/limite |
|---|---|---|
| RNF008 | Saúde por dependência | `/health` consulta PostgreSQL na síncrona e metadados Kafka na assíncrona |
| RNF009 | Reentrega segura | `event_id` PK + hash; offset manual após persistência ou ACK da DLQ |
| RNF010 | Falha prolongada visível | Após exaustão, mensagem vai à DLQ; não há garantia de processamento automático posterior |

Não há SLA; um único broker/instância PostgreSQL é ponto único de falha. O cenário C4 prevê interrupção controlada do PostgreSQL em ambas as variantes e deve distinguir disponibilidade de aceitação e conclusão do processamento.

## 10.4 Usabilidade

RNF011: APIs usam JSON e códigos HTTP documentados, com exemplo executável no README. O protótipo não tem tela, login ou assistência interativa; operadores devem usar Compose, logs e cliente HTTP.

## 10.5 Escalabilidade

RNF012: Compose fixa uma partição e uma réplica Kafka e limite de CPU/memória por serviço. Isso favorece controle experimental, mas limita paralelismo e não demonstra escalabilidade horizontal. Mudanças no número de partições ou réplicas exigiriam novo protocolo e nova interpretação dos resultados.

## 10.6 Backup e recuperação

RNF013: volumes nomeados sobrevivem a `docker compose down`; `down -v` os remove. Não há backup automatizado, restauração validada ou retenção formal. Portanto, somente dados sintéticos e reproduzíveis devem ser usados. Evidências de experimentos devem ser armazenadas fora dos volumes e sem payload sensível.

## 10.7 Auditoria e observabilidade

RNF014: a própria linha `audit_records` é imutável pela API. Marcos JSON incluem instante UTC, relógio de parede, relógio monotônico local, variante e `run_id` opcional, sem dados sensíveis do payload. `persisted_at` é timestamp de inserção, não medição de commit; a evidência temporal de commit é o marco `commit_completed`.

## 10.8 LGPD e privacidade

RNF015: cargas do experimento devem ser sintéticas. `actor_id`, `entity_id` e `payload` podem identificar pessoas ou atividades em usos reais; a DLQ carrega valor original em Base64. Não há consentimento, retenção, anonimização ou atendimento a direitos do titular implementados. Por isso o protótipo não deve receber dados pessoais reais sem desenho adicional de governança e segurança.
