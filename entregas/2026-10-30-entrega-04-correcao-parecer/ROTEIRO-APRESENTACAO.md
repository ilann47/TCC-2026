# Roteiro da apresentação corrigida

Os dez primeiros slides têm roteiro sugerido de cinco minutos. Os sete slides seguintes são apoio para perguntas. Os tempos são estimativas de ensaio, não duração medida. A leitura das fontes não integra a fala. A revisão pessoal integral permanece pendente.

## Slide 1 (15 s)

Comparei duas implementações Java para registrar auditoria. A pergunta é quais compromissos de desempenho e recuperação aparecem quando se confirma a gravação imediatamente ou se aceita o trabalho para gravar depois. A campanha inclui 64 coletas completas e uma parcial preservada.

Fontes: TCC revisto em 30/10/2026, Capítulos 3, 5 e 6. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 2 (25 s)

As duas variantes compartilham contrato, validação, hash e PostgreSQL. A síncrona confirma depois da transação. A assíncrona confirma publicação no Kafka e um consumidor grava depois. O piloto comparou cinquenta registros equivalentes por variante, sem substituir a campanha.

Fontes: TCC revisto em 30/10/2026, Capítulos 3, 5 e 6. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 3 (30 s)

Cada coleta é uma execução, não um evento. Fizemos cinco repetições por condição, com o mesmo conteúdo nos pares. O k6 gerou a carga e o analisador Java conciliou resposta, banco e marcos de transação. As 65 coletas incluem cargas constantes, rajada e paradas controladas. A análise é descritiva por coleta e par.

Fontes: TCC revisto em 30/10/2026, Capítulos 3, 5 e 6. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 4 (30 s)

A 48 eventos por segundo, o p95 HTTP médio foi 2,60 milissegundos na assíncrona e 4,34 na síncrona. Até concluir a gravação, foram 5,83 e 3,92 milissegundos. O aceite mais rápido coexistiu com conclusão mais lenta. As duas atingiram a taxa oferecida nesse recorte, sem demonstrar capacidade máxima ou equivalência.

Fontes: TCC revisto em 30/10/2026, Capítulo 5, Tabela 7 e group-summary.json, steady 48/s. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 5 (25 s)

A 12 eventos por segundo, o caminho assíncrono consumiu aproximadamente duas vezes a CPU e quatro vezes a memória. Incluímos API e banco na síncrona, e também consumidor e Kafka na assíncrona. A topologia faz parte da comparação. CPU e memória não medem dinheiro ou esforço de manutenção.

Fontes: TCC revisto em 30/10/2026, Capítulo 5, Tabela 11 e group-summary.json, steady 12/s. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 6 (35 s)

Com o banco parado, a síncrona teve 2.452 respostas 503. Um desses eventos terminou no banco apesar do erro. Na assíncrona, todos os envios foram aceitos, mas 14 terminaram na fila de falhas. Eles ficaram retidos para inspeção, sem gravação automática posterior. A resposta de aceite e o destino final precisam ser acompanhados separadamente.

Fontes: TCC revisto em 30/10/2026, Capítulo 5, Tabela 10 e group-summary.json, postgres-stop. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 7 (25 s)

Com o consumidor parado, todos os 10.801 aceites medidos terminaram gravados, sem fila de falhas. O tempo de conclusão chegou à escala de dezenas de segundos. A retenção permitiu aceitar durante a parada, mas essa observação local não prova tolerância à perda do broker ou da máquina.

Fontes: TCC revisto em 30/10/2026, Capítulo 5 e dados por coleta de consumer-stop. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 8 (40 s)

A parada do banco fazia parte do teste. A falta do horário de uma gravação não era planejada. Preservamos a coleta e o veredito original de evidência incompleta. Uma revisão analítica manteve indicadores auditados e retirou o par afetado da comparação primária de conclusão, que ficou com quatro pares. Não repetimos a coleta nem estimamos o tempo ausente.

Fontes: TCC revisto em 30/10/2026, Capítulo 3, revisão analítica, capítulo 5 e Apêndice A. Original instrument_valid=false preservado. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 9 (40 s)

O critério original de recuperação exige trinta segundos sustentados sob carga e conta destinos na fila de falhas como aceites sem gravação. Ele permanece atingido em um de cinco casos assíncronos com banco parado. Na leitura exploratória posterior, separar falha terminal de pendência ativa permitiu observar retorno operacional nos cinco casos. Isso não alterou o critério original nem gravou os 14 eventos terminais.

Fontes: TCC revisto em 30/10/2026, Capítulo 5, recuperação original e subseção 5.7.5. recuperacao-exploratoria.json, 30/10/2026. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 10 (35 s)

A síncrona favoreceu confirmação imediata de gravação e menor uso de recursos. A assíncrona favoreceu aceite rápido e retenção na parada do consumidor, com conclusão posterior e componentes adicionais. As expectativas tiveram apoio descritivo nesse recorte. Custos financeiros, manutenção e superioridade geral permanecem inconclusivos. As contribuições e os requisitos estão nos slides de apoio.

Fontes: TCC revisto em 30/10/2026, Capítulos 3, 5 e 6. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 11 (apoio)

O núcleo e os instrumentos já existem. UC05 executa cenários por k6 e executor. UC06 consolida os indicadores por analisador e relatórios. A documentação deixou de chamá-los de planejados. Preservamos os limites: uma coleta tem cobertura temporal incompleta, o formulário próprio não foi construído e não demonstramos segurança de produção, portabilidade externa ou escala horizontal.

Fontes: TCC revisto em 30/10/2026, Capítulo 4, requisitos e UC05/UC06. Capítulo 5, Tabela 6. Matriz integral de 27 requisitos. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 12 (apoio)

Reproduzimos o resultado original de um em cinco e então subtraímos da pendência somente eventos com confirmação de DLQ observada até o fim de cada janela. Não usamos a DLQ final como se ela já existisse antes. Os demais critérios ficaram iguais. Observamos a sequência operacional nos cinco casos, entre 37,78 e 38,77 segundos após a retomada. Esta é uma sensibilidade posterior, não reclassificação ou confirmação predeclarada.

Fontes: TCC revisto em 30/10/2026, Capítulo 5, Tabela 13. RECUPERACAO-EXPLORATORIA.md e recuperacao-exploratoria.json. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 13 (apoio)

Entreguei um protótipo e instrumentos que podem apoiar novas verificações. A contribuição metodológica é separar o que a API aceita, o que o banco grava e o que termina em falha retida. Os controles permitem rastrear as tabelas até a evidência e mantêm resultados desfavoráveis. Eles não eliminam o tamanho amostral reduzido ou a necessidade de replicação.

Fontes: TCC revisto em 30/10/2026, Capítulo 5, Pontos fortes. Capítulo 6, Avaliação do sistema e Contribuições. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 14 (apoio)

A discussão relaciona os achados aos mecanismos estudados, sem comparar milissegundos de aplicações diferentes. Custos dependem de topologia e ambiente. Comunicação e efeito persistido têm garantias distintas. Observabilidade ajuda a detectar o que faltou, mas não recupera um instante não registrado.

Fontes: TCC revisto em 30/10/2026, Capítulo 5, subseção Discussão com a literatura, e referências correspondentes. Cabane/Farias DOI 10.1016/j.future.2023.10.021; Kazanavičius/Mažeika DOI 10.31577/cai_2023_1_1; Blinowski DOI 10.1109/ACCESS.2022.3152803; Laigner DOI 10.14778/3484224.3484232; Niedermaier DOI 10.1007/978-3-030-33702-5_3; Helland CIDR 2007. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 15 (apoio)

Este gráfico mostra os mesmos números da tabela do slide quatro. Cada barra é a média de cinco percentis calculados por coleta. A síncrona confirma o efeito antes de responder. A assíncrona devolve o aceite antes da gravação, o que explica as direções diferentes.

Fontes: TCC revisto em 30/10/2026, group-summary.json, steady 48/s; Capítulo 5, Tabela 7. Gráfico arredondado a duas casas, dados científicos preservados. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 16 (apoio)

Os gráficos repetem a tabela do slide cinco em escalas distintas. O primeiro mede percentual de uma CPU lógica e o segundo memória em MiB. A comparação é dos caminhos completos, não de um protocolo abstrato. A direção não mede dinheiro, manutenção ou eficiência de componentes parados.

Fontes: TCC revisto em 30/10/2026, group-summary.json, steady 12/s; Capítulo 5, Tabela 11. CPU com duas casas e memória com uma casa no gráfico. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.

## Slide 17 (apoio)

As ferramentas apoiaram mais do que gramática: também código, comandos da campanha, agregação e redação. As medidas vieram da execução dos instrumentos. O autor informou em 30 de outubro que ainda fará sua revisão pessoal integral antes da entrega. Não devo afirmar que ela ou a aprovação da orientadora já ocorreram.

Fontes: TCC revisto em 30/10/2026, Declaração de uso de IA e Capítulo 6 do PDF corrigido. ATENDIMENTO-PARECER.md, item M4 e confirmação direta do autor. Dados originais em implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/. Sem nova medição.
