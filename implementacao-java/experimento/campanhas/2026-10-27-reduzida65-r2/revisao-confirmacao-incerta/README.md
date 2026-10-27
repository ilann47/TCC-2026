# Parecer formal: persistência com confirmação incerta

Data: 27/10/2026. Situação: **revisão concluída; emenda analítica proposta, ainda não adotada**.

## Escopo e conclusão

O usuário autorizou neste chat a revisão formal do tratamento de confirmação incerta, preservando o resultado e avaliando o impacto nas coletas anteriores. Esta revisão é offline e não constitui autorização técnica do controlador para retomar a campanha. Não houve alteração dos critérios congelados, dos instrumentos, das imagens, do plano ou do diário de execução.

O bloqueio é correto sob a regra publicada em `f5d77b500ac9e1afe26d1d52068054e59a17f74d`: uma linha no banco sem `commit_completed` gera `incomplete_commit_db_evidence`. Ao mesmo tempo, a evidência distingue dois fatos: **o registro está persistido na exportação final**, mas **seu instante de conclusão não foi observado pelo marco pós-commit**. O HTTP 503 permanece erro HTTP; não se transforma em aceite 201.

Recomenda-se uma emenda analítica explícita que preserve essa observação e separe a elegibilidade de cada métrica, sem declarar a coleta integralmente válida sob a regra original. Adoção dessa emenda e retomada das 28 execuções não iniciadas dependem de decisão humana sobre este parecer e de implementação/verificação/publicação do novo caminho no controlador. Não se deve editar o diário para pular a recusa atual.

## Auditoria reproduzível

Ferramenta: [`review_commit_uncertainty.py`](../../../review_commit_uncertainty.py). Relatório: [`audit.json`](audit.json).

No diretório `implementacao-java`, em WSL/Python 3.11 ou superior:

```bash
python3 -m unittest discover -s experimento/tests -p test_commit_uncertainty_review.py -v
python3 experimento/review_commit_uncertainty.py \
  --output .runtime/reduzida65-2026-10-27-r2/formal-review-outro-nome.json
```

O auditor exige uma sessão parada em `attention_required`, verifica o prefixo do plano e recusa sobrescrever saídas. Sua saída é somente um parecer: `campaign_admission_authorized=false` em todos os registros significa que **o auditor não concede nova admissão**, não revoga as 36 admissões anteriores. O relatório público preserva o snapshot auditado; o comando só é reproduzível enquanto esse estado e os brutos locais existirem. O JSON não contém caminhos absolutos pessoais ou credenciais.

Foram verificados:

- 46 conjuntos: nove pilotos e 37 tentativas definitivas; pilotos não contam como repetições definitivas.
- 1.051 arquivos distintos listados nos `SHA256SUMS`, tanto antes quanto depois da leitura: 2.102 verificações de conteúdo, sem divergência. Isso atesta os arquivos catalogados, não a existência de uma informação que nunca foi registrada.
- UUID/dataset/condição/VUs, natureza da coleta, checkout limpo registrado, fingerprints de instrumentação/imagens, parâmetros e margens de CPU/memória de gerador/observador.
- Pontos k6 originais versus `events.csv`, códigos HTTP/UUIDs, linhas exportadas, conteúdo sintético e seu hash canônico, presença de marcos e contagens do resumo.
- Catálogo público dos nove pilotos, política/plano/controlador congelados e ausência de pastas dos 28 UUIDs posteriores.
- Estado e inventários estáveis durante a revisão; os arquivos brutos foram relidos para conferência final. Nenhum resumo, booleano de validade ou timestamp foi reescrito.

| Grupo | Quantidade | Veredito original mantido | Ocorrências banco sem marco |
|---|---:|---|---:|
| Pilotos R2 | 9 | válido | 0 |
| Definitivos anteriores | 36 | válido | 0 |
| 37ª tentativa | 1 | inválido; saída do analisador 2 | 1 |
| UUIDs ainda não iniciados | 28 | sem resultado | não aplicável |

Não foram recalculadas todas as distribuições de recursos e recuperação nesta ferramenta: ela verifica sua preservação por checksum e as margens instrumentais, além de cruzar os dados de eventos. Esta revisão não substitui a agregação final da campanha.

Identificadores do snapshot:

- Protocolo congelado SHA-256: `3bcaa0251e239f84d0b0f8b26bb1f5f74a118adf3bc16a657c05cf0538ee1c77`.
- Política R2 SHA-256: `95d30475e16bcff2ebcd92f1257aa12e0e4d1aa7f64c9f72eaa6511a3f409499`.
- Plano SHA-256: `4091d5891657c6d0d80614d4133fd776e80d93d1b342148978c6fad7022a8148`.
- Ferramenta desta auditoria SHA-256: `6d368fe7c7c07bc61cf525b7718175e91d6f598cbaf62a441b664ba059210816`.
- Relatório `audit.json` SHA-256: `86aed0e8f2bb5c7a94b637194c1d1e7516b7b11e94f953c01f3da5540fe4c975`.

## Evidência da 37ª tentativa

Execução `8733a7d2-89b5-4a5e-be22-0e4ed6e6b29b`, bloco 3, `postgres-stop`, síncrona, 12 eventos/s, 180 s medidos. Dataset `d68f2ee7-bbc4-4380-b8e1-8478f6978fb5`; evento afetado `d68f2ee7-bbc4-4380-b8e1-0000000002d5`.

| Evidência local preservada | Observação |
|---|---|
| `manifest.txt` | parada solicitada às 09:06:29.271570069Z; parada concluída às 09:06:30.111764003Z; restauração às 09:07:10.888700988Z |
| `app.log` | `request_received` às 09:06:29.877793617Z e `request_failed`, motivo `database_unavailable`, às 09:06:29.911335695Z |
| `events.csv` e pontos k6 | HTTP 503, duração HTTP 39,671671 ms, linha no banco, tempo envio→commit ausente |
| `database.jsonl` | UUID e conteúdo corretos, hash verificado; `persisted_at=2026-10-27T09:06:29.878966+00:00` |
| `app.log` | nenhum `commit_completed` ou `persistence_confirmed` para esse UUID |
| `summary.json` | única questão instrumental: esse UUID com `incomplete_commit_db_evidence` |

Os 23 arquivos catalogados dessa pasta permaneceram iguais. SHA-256 do resumo original: `f34209d961bdd29ebea8aa3646aaf147a946908d10bd767aa4c0b98762385df8`.

O mecanismo exato da exceção de banco não é identificável pelo motivo genérico registrado. A coincidência com a parada planejada é evidência temporal, não prova de qual etapa JDBC/rede perdeu a confirmação. Não se afirma que houve um SQLSTATE específico, rollback, perda de pacote ou defeito no PostgreSQL.

### Por que não usar `persisted_at` como commit

Na migração `audit-storage/src/main/resources/db/migration/V1__create_audit_records.sql`, o valor padrão é `clock_timestamp()`. Essa função avalia o relógio durante a instrução, não a conclusão da transação; ver [PostgreSQL 16, funções de data/hora](https://www.postgresql.org/docs/16/functions-datetime.html#FUNCTIONS-DATETIME-CURRENT). Portanto, nem esse valor, nem o horário do HTTP 503, nem a restauração serão usados para preencher o tempo ausente.

Em `audit-storage/.../AuditRepository.java`, o marco só é emitido depois do retorno normal de `TransactionTemplate.execute`. Em `sync-api/.../SyncAuditController.java`, exceções de acesso/transação resultam em 503 com `acceptance=unknown`. A combinação observada é compatível com esse contrato; o analisador, porém, trata toda discrepância banco/marco como uma invalidação global. A revisão identifica essa limitação do modelo de evidência, sem provar a causa física da exceção nem negar a informação temporal ausente.

## Impacto quantitativo e semântico

População medida da 37ª tentativa:

| Resposta | Oferecidos | Persistidos ao final | Com tempo pós-commit observado | Não presentes na exportação final |
|---|---:|---:|---:|---:|
| HTTP 201 com UUID correto | 1.666 | 1.666 | 1.666 | 0 |
| HTTP 503 | 494 | 1 | 0 | 493 |
| Total | 2.160 | 1.667 | 1.666 | 493 |

Erro HTTP: `494/2160 = 22,87037%`, sem descontar o erro que persistiu. Cobertura temporal dos persistidos: `1666/1667 = 99,94001%`. Isso não é cobertura da totalidade dos oferecidos: houve 493 não persistidos, todos nesse grupo de erros HTTP. Não chamar esses 493 de perda de eventos aceitos. Não há aceite válido sem destino conciliado, DLQ ou pendência retida nesta coleta; isso não equivale a sucesso de todas as solicitações.

O resumo original mostra `1666/180 = 9,25556` commits observados/s na janela. Sem localizar o commit ausente no tempo, a vazão real dos eventos medidos persistidos nessa janela está conservadoramente entre `1666/180` e `1667/180`, ou **[9,25556; 9,26111] eventos/s**, considerando que a única lacuna temporal encontrada é esse registro. Esse intervalo é uma análise de sensibilidade contábil, não intervalo de confiança e não imputação de timestamp. Não substituir o valor original por 9,26111.

A distribuição envio→commit de 1.666 observações permanece a mesma, mas não descreve integralmente os 1.667 persistidos. A ausência aconteceu em uma fronteira de falha e não pode ser assumida aleatória. Não imputar média/zero nem afirmar ausência de viés por a fração ser pequena. `first_commit_after_restore_ms` deve ser chamado primeiro **marco observado**; o tempo do primeiro commit real não fica identificado para todos os eventos. A recuperação sustentada registrada continua evidência das três janelas qualificadas pelos marcos conhecidos, não reconstrução do evento sem tempo.

Os 36 definitivos anteriores e nove pilotos não apresentaram essa lacuna. Seus resultados, arquivos e vereditos permanecem inalterados. Isso permite delimitar o impacto observado, mas não exclui outras ameaças à validade do experimento local.

## Emenda recomendada, ainda não vigente

1. Preservar o analisador original e sua saída inválida. Criar uma camada de revisão versionada separada, com rastreabilidade para a regra e para o protocolo R2 original, distinguindo integridade do conteúdo/destino de cobertura temporal. Não editar a imagem Java para inventar dados.
2. Admitir revisão restrita de **linha correta + HTTP 503 + `request_failed=database_unavailable` + dados de cliente completos + ausência de ambos os marcos de confirmação**, sem retry/replay/DLQ e sem outra questão instrumental. Sucesso HTTP sem marco, marco sem linha, conteúdo incorreto, cliente incompleto, clock inválido ou falta de recursos continuam bloqueios. Casos assíncronos e outros códigos não ficam autorizados por analogia.
3. Manter a 37ª tentativa com qualificação explícita, não como integralmente válida: usar contagens finais/HTTP/recursos verificáveis; manter o tempo desconhecido nulo; distinguir vazão observada de seu limite conservador. Para comparação primária de latência de conclusão, usar somente execuções com cobertura temporal completa e mostrar separadamente a sensibilidade com a distribuição parcial desta coleta.
4. Não substituir ou repetir esta observação desfavorável. Continuar somente os 28 UUIDs nunca iniciados, com a mesma carga, parâmetros, imagens e configuração. Se todos passarem, serão **64 coletas com evidência temporal completa dos persistidos e uma coleta qualificada**, não 65 coletas integralmente válidas sob o critério original. Na condição síncrona `postgres-stop`, a análise primária completa de conclusão terá quatro repetições/pares completos, não cinco; indicadores identificados podem conservar as cinco observações com a ressalva explícita.
5. Registrar a emenda como motivada por dados já vistos: análise retrospectiva nas primeiras 37 e regra declarada antes das restantes. Aplicar a mesma regra a todo o conjunto, sem favorecer uma variante. Testar todos os bloqueios, conferir novamente o impacto, commitar/push e verificar o remoto antes de eventual retomada por caminho explícito do controlador, com lock e sem diário adulterado.
6. Atualizar protocolo/metodologia/relatórios para a elegibilidade por métrica e para a análise de sensibilidade, sem dizer que essa decisão era predeclarada antes da campanha. Preservar a análise estrita original como comparação. Não alterar os critérios de referência 48/s ou as margens para liberar o estudo.

Alternativa estrita: manter esta tentativa excluída da análise primária pelo critério original e avaliar, mediante decisão expressa e documentação, uma coleta adicional com novo UUID. Isso excederia as 65 tentativas planejadas e não apagaria a ocorrência nem justificaria repetições opcionais. Por preservar o fenômeno e evitar seleção de uma execução sem a ocorrência, recomenda-se a emenda qualificada acima, com perda de completude declarada.

## Limites e próximo passo

Os 13 testes novos da ferramenta e os cinco testes existentes do controlador passaram (18/18). Os novos testes cobrem a descrição restrita e rejeições de casos diferentes; não validam uma emenda executável, porque ela ainda não foi implementada. O verificador Node confirmou os hashes do protocolo original, nove pilotos, plano de 65 e 37 pastas presentes. Seu campo estático `definitive_execution_authorized=true` descreve a antiga liberação do protocolo; **não é liberação de retomada** nem auditoria dessa coleta recusada. O controlador permanece sem caminho para admitir a pasta recusada, e `state.json` continua em `attention_required`, com 36 concluídas. Nenhum UUID foi repetido/substituído e nenhuma nova carga foi iniciada. O projeto interativo foi observado ativo com seus cinco serviços; o experimental estava parado.

A decisão solicitada é **adotar a emenda analítica qualificada e autorizar sua implementação e posterior retomada dos 28 UUIDs**, ou manter a campanha parada para outra decisão metodológica. Finalização dos capítulos 5/6 e PDF permanece pendente; esta revisão não é conclusão do TCC.
