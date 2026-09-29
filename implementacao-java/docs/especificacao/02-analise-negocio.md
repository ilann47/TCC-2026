> Links: [[README]] · [[01-introducao]] · [[03-der]] · [[05-casos-de-uso/uc001-registrar-sincrono]]

# 2. Análise do problema

## 2.1 Problemas atuais

Uma resposta HTTP bem-sucedida pode representar marcos diferentes: gravação concluída no banco ou apenas aceitação pelo broker. Sem distinguir os marcos, métricas de latência e disponibilidade são interpretadas incorretamente. Falhas de banco também podem produzir reenvios, duplicatas, conflitos ou mensagens não processadas. O protótipo oferece duas implementações com contrato comum para tornar essas diferenças observáveis, especialmente no cenário C4 de interrupção do PostgreSQL nas duas variantes.

## 2.2 Envolvidos

| Envolvido | Interesse | Limite de responsabilidade |
|---|---|---|
| Acadêmico/desenvolvedor | Implementar, versionar e analisar as variantes | Não apresentar piloto como resultado definitivo |
| Orientadora e banca | Verificar coerência entre questão, modelo, execução e evidência | Avaliação acadêmica, não operação dos serviços |
| Operador experimental | Configurar ambiente, cargas, falha C4 e coleta | Usar dados sintéticos, preservar parâmetros |
| Aplicação cliente/script de carga | Enviar eventos e observar respostas | Reusar `event_id` somente quando desejar duplicata |
| Administrador do ambiente | Proteger senha local e dados de Kafka/PostgreSQL | Não publicar payloads ou segredos |

## 2.3 Usuários e papéis

| Papel | Interface | Responsabilidades concretas |
|---|---|---|
| Aplicação cliente | HTTP JSON | Criar evento síncrono ou solicitar aceitação assíncrona; opcionalmente informar `X-Run-ID` |
| Operador | Docker Compose, logs, HTTP | Inicializar serviços, conferir saúde, consultar registro e executar cenário controlado |
| Consumidor automatizado | Kafka e PostgreSQL | Processar evento, aplicar tentativas, usar DLQ e confirmar offset |

Não existe cadastro de usuários nem perfil de autorização na aplicação. Esse é um limite de segurança do protótipo: as portas externas do Compose são vinculadas somente a `127.0.0.1`.
