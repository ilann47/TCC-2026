# Entrega 04 em Java: fechamento de 27/10/2026

Nova entrega datada após a campanha definitiva R2/A1, sem substituir a [preparação de 06/10](../2026-10-06-entrega-04-java-preparacao/README.md) ou entregas anteriores. O nome mantém a identificação da etapa já usada no repositório. A revisão/aprovação da orientadora e a submissão ao portal são etapas externas a este pacote.

## Arquivos para revisão e apresentação

| Arquivo | Conteúdo |
|---|---|
| [TCC-Entrega04-final.pdf](TCC-Entrega04-final.pdf) | Documento de 80 páginas, capítulos 5/6 completos, conclusão de três páginas e declaração de IA. Cópia byte a byte do fechamento científico, sem nova medição ou reescrita dos dados. |
| [Apresentacao-Entrega04-final.pptx](Apresentacao-Entrega04-final.pptx) | Dez slides editáveis atualizados com resultados definitivos, seis tabelas nativas e notas de fala. Mantém o formato visual da preparação, com dados, hipóteses e limitações atuais. |
| [ROTEIRO-APRESENTACAO.md](ROTEIRO-APRESENTACAO.md) | Texto das notas e sugestão de divisão de dez minutos para ensaio. Duração sugerida, não cronometrada. |
| [RELATORIO-VERIFICACAO.md](RELATORIO-VERIFICACAO.md) | Conferências dos arquivos, conteúdo e apresentação, com limites de validação. |
| [VERSAO-FONTES.md](VERSAO-FONTES.md) | Identificação do documento científico, commits de coleta e fontes abertas. |
| [evidencias](evidencias/README.md) | Cópias do catálogo e da validação científica, com links aos resultados completos e sensibilidades. |
| [SHA256SUMS](SHA256SUMS) | Índice dos arquivos desta entrega. Detecta alterações, não constitui assinatura digital. |

## Resultado que a entrega apresenta

A campanha terminou em 27/10/2026 às 17h01 de Brasília com exatamente 65 UUIDs planejados: **64 coletas completas e uma parcial A1**, em treze condições e cinco tentativas por condição. Não são 65 integralmente válidas para toda métrica. A latência de conclusão primária com banco parado utiliza quatro pares completos, sem preencher o instante de commit ausente.

O texto e os slides separam HTTP de conclusão, aceites de persistência, DLQ de desaparecimento e recuperação do serviço de recuperação integral do backlog. Preservam os resultados desfavoráveis: 14 eventos assíncronos em DLQ no banco parado e somente um dos cinco casos atendendo o indicador composto de recuperação sustentada nessa condição. O indicador inclui aceites em DLQ na contagem sem commit, limitação discutida explicitamente.

As hipóteses recebem avaliação descritiva, por execução/par, sem alegar significância ou uma arquitetura superior em geral. Um computador compartilhado, broker único, cinco tentativas e a emenda pós-hoc limitam as conclusões. A apresentação não reutiliza os números de validações curtas como se fossem resultados definitivos.

## Fontes e reprodução

- [Texto LaTeX](../../projeto-latex-java/modelo.tex), [guia do projeto](../../projeto-latex-java/README.md) e [código Java](../../implementacao-java/README.md).
- [Resultados auditados](../../implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/RESULTADOS.md), [dados por execução/par](../../implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/) e [referências compartilhadas](../../referencias/README.md).
- [Fonte de geração da apresentação](fontes-apresentacao/build.mjs). Para editar o material diretamente, abra o PPTX. Para reproduzir a geração, use o runtime de artefatos configurado, com `RUNTIME_NODE_MODULES`, `RUNTIME_PYTHON` e `PRESENTATIONS_SKILL_DIR`, e execute `node fontes-apresentacao/build.mjs <raiz-do-repositorio> <novo-caminho-de-saida.pptx>`. O validador recusa sobrescrever uma saída já existente.

As fontes do texto e do software continuam abertas nas pastas principais; não se duplicam em ZIP, nem se incluem volumes Docker, credenciais, caches ou os brutos integrais. Os dados públicos completos têm localização única no relatório R2/A1. A cópia em `output/pdf/` permanece como artefato do fechamento; esta pasta datada é o ponto de entrada da entrega.

Para verificar o pacote, execute da raiz do repositório: `python entregas/2026-10-27-entrega-04-java-final/fontes-apresentacao/verificar_entrega.py`. A conferência é somente leitura e não inicia carga.

## Pendências externas

Revisão e eventuais solicitações da Professora Alessandra Bussador, confirmação dos requisitos/prazo institucionais e submissão oficial. O abstract continua fora do PDF conforme solicitação anterior, embora o fonte esteja atualizado. Banca, data de aprovação e ficha catalográfica dependem de dados institucionais confirmados. O pacote não comprova aprovação ou envio ao portal.
