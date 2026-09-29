> Links: [[README]] · [[relatorio-conformidade]] · [[10-requisitos-nao-funcionais]]

# Plano de refatoração e evolução — não implementado

O escopo atual prioriza paridade e experimento. Esta lista não atribui capacidades futuras ao código presente.

| Prioridade | Área | Alteração proposta | Justificativa e condição |
|---|---|---|---|
| P0 | Banco/API/entidades | Ampliar testes reais de concorrência, conflito e falha de commit sem modificar `audit_records` | Verificar semântica antes do ensaio; qualquer mudança de esquema deve ser nova migração Flyway |
| P0 | Backend/mensageria | Validar timeout, ACK, DLQ e replay em Kafka real | O mock não prova comportamento sob falha de broker |
| P0 | Arquitetura/experimento | Congelar parâmetros, executar C4 nas duas variantes, validar marcos e normalizador | Necessário antes de qualquer conclusão comparativa |
| P1 | API/contrato | Ampliar fixtures de canonicalização para Unicode de controle, datas com offset e variedade numérica; harmonizar erros `422` | Reduzir divergência Java/Python se cargas forem compartilhadas |
| P1 | Banco | Definir política de migração para dados históricos somente se houver necessidade real | A versão Java deve continuar em banco próprio até validação |
| P2 | Segurança/LGPD | Autenticação, TLS, ACL Kafka, retenção e mascaramento/remoção de dados | Obrigatório apenas para uso com dados reais ou exposição em rede; fora do TCC experimental |
| P2 | Frontend | Nenhuma tela prevista | Um frontend não contribui para a pergunta REST versus EDA |
| P2 | Relatórios | Relatório científico gerado a partir de ensaios definitivos | Não substituir por gráficos de piloto |

Critério para cada evolução: primeiro demonstrar o problema com teste/evidência, alterar código e migração de modo isolado, atualizar esta especificação e executar novamente testes e protocolo pertinente. O diagrama de classe e o DER devem permanecer sincronizados com o código, não servir como projeto imaginário.
