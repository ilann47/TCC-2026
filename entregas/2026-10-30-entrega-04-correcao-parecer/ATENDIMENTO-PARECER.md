# Atendimento ao parecer de correções

Documento analisado: “Parecer de correções – ilan.docx”, fornecido pelo autor. SHA-256: `1ba2ca16f2de1e8fc35ba6db62caf345878c8519d4014687fd08409f3f1c7ba5`. A numeração de páginas do parecer refere-se à versão anterior; as seções e o sumário do PDF novo são os localizadores vigentes.

## O que já estava atendido

O texto anterior distinguia resposta HTTP, conclusão da gravação e destino terminal; preservava a coleta parcial e seu veredito original; não estimava o instante de commit ausente; utilizava quatro pares completos na comparação afetada e apresentava sensibilidade estrita. Também documentava ambiente compartilhado, cinco repetições, análise descritiva e ausência de medição financeira. A limitação do critério de recuperação que inclui DLQ já estava discutida, mas ainda não havia a leitura exploratória solicitada.

## Conferência item a item

| Item | Estado antes da revisão | Alteração realizada | Situação e limite |
|---|---|---|---|
| A1 | Explicação da parcial já presente, porém com rótulos e rastreamento no corpo | Resumo direto com método e números; quadro de termos no método; commits, identificadores de coleta e caminhos no apêndice | Atendido editorialmente; dados e parcial preservados |
| A2 | Abstract e folha de aprovação desabilitados | Abstract com Keywords traduz o resumo; folha preparada no padrão do modelo UDC | Incluídos; data, examinadores e assinaturas continuam dependentes da instituição, sem aprovação fictícia |
| A3 | Capítulo 4 ainda anunciava a coleta futura | Tempos verbais e referência ao capítulo 5 atualizados | Atendido; futuro mantido apenas onde descreve comportamento condicional ou evolução real |
| A4 | UC05/06, coletores e relatórios marcados como planejados; propostas ocupavam várias páginas | UC05/06 e requisitos dos instrumentos atualizados; diagrama regenerado; banco mostra a tabela real; propostas relacionais e de interface reduzidas | Atendido; formulário próprio continua parcial e não é apresentado como entregue |
| A5 | Objetivos discutidos, sem matriz RF/RNF e seções próprias | Matriz de 17 RF e 10 RNF, pontos fortes, avaliação do sistema e contribuições | Atendido com estados qualificados, não “27 requisitos integralmente comprovados” |
| M1 | Discussão breve de dois estudos | Subseção que confronta direções, marcos e limitações com Cabane/Farias, Kazanavičius/Mažeika, Blinowski, Helland, Laigner e Niedermaier | Atendido sem comparar valores absolutos de aplicações diferentes |
| M2 | Análise descritiva e n pequeno declarados, pouca justificativa | Orçamento, ausência de cálculo de poder e resolução limitada explicados; probabilidade de 6,25% bilateral para cinco sinais concordantes usada apenas como ilustração sob hipóteses explícitas | Atendido; não foi acrescentado teste confirmatório pós-hoc |
| M3 | Limite de construto da recuperação já identificado | Reanálise offline com ACK observado de DLQ separado da pendência ativa, mantendo todas as demais condições | Atendido; original 1/5 permanece, exploratório 5/5 não significa todos persistidos |
| M4 | Declaração em tom normativo e revisão pessoal não confirmada | Uso efetivo de Claude/Codex descrito no passado, incluindo código, execução, análise e redação | **Parcial por pendência humana:** o autor respondeu que ainda revisará pessoalmente; não foi declarada revisão concluída ou aprovação da orientadora |
| M5 | Comparação JMeter/k6 no capítulo de resultados | Escolha e quadro movidos à metodologia; capítulo 5 começa pela validação dos instrumentos | Atendido |
| M6 | Documentação de geradores só em notas, demais ferramentas sem referência | Referências oficiais de k6, saída JSON, JMeter, Kafka 3.9, PostgreSQL 16 e Docker, citadas no método com acesso em 30/10/2026 | Atendido na exigência concreta; inclusão de 3–5 novos artigos era opcional e não foi preenchida com referências sem avaliação |
| B1 | Rótulo “Orientador” e título “Professora” | “Orientadora” e “Profa. Dra.”, após confirmação expressa do autor | Atendido |
| B2 | “Palavras-chaves” | Corrigido para “Palavras-chave” no modelo | Atendido |
| B3 | Sobrenomes Unicode falhavam na caixa alta do BibTeX | Acentos protegidos por comandos LaTeX; saída bibliográfica conferida | Atendido |
| B4 | Latências longas em milissegundos e vazão com cinco casas | Conclusão longa em segundos, unidade em cada célula; vazão com duas casas; precisão integral mantida nos dados e limites explícitos no texto | Atendido; nota explica arredondamento que pode coincidir nos limites ou mostrar dispersão 0,00 |
| B5 | Quadro fora das listas | Lista de Quadros incluída e títulos dos marcadores corrigidos | Atendido |
| B6 | Sumário da versão anterior | Regenerado após as novas seções e apêndice | Atendido após compilação estabilizada |

## Limites de publicação

O parecer original não foi alterado nem redistribuído. Não foram modificados o protocolo congelado, plano, diário, instrumentação de carga, imagens ou resultados originais. O gerador offline de tabelas recebeu apenas ajustes de apresentação e unidades. A reanálise exploratória possui saída e script separados, sem novo experimento ou reclassificação. A revisão não altera a entrega histórica de 27/10 nem conclui a revisão pessoal do autor.
