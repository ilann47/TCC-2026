# Recuperação operacional e destino terminal

Leitura exploratória pós-hoc realizada em 30/10/2026 a pedido do parecer. Não é nova coleta, emenda do protocolo ou novo veredito da campanha.

Foram lidas as cinco coletas assíncronas de interrupção do PostgreSQL. O script reproduziu o critério original, inclusive tempos nos casos observados: uma sequência qualificante em cinco coletas. Em seguida, alterou **somente a pendência**, subtraindo eventos medidos que já possuíam o marco `dlq_acknowledged` até o fim da janela. Não se usou o estado final da DLQ como se tivesse ocorrido antes; sua confirmação temporal foi exigida.

Permaneceram: três janelas completas de dez segundos, ao menos 90% da taxa oferecida concluída por segundo, ausência de erros HTTP, limite de pendência `max(2, ceil(taxa × 0,1))`, observação saudável e recente de banco e lag, e somente entrada ativa. Os instantes foram tratados em nanossegundos inteiros, como os registros, sem preencher ausência por zero.

| Repetição | DLQ terminal | Critério original | Leitura exploratória | Confirmação exploratória após retomada |
|---|---:|---|---|---:|
| 1 | 3 | Não observado | Observada | 38,77 s |
| 2 | 3 | Não observado | Observada | 37,78 s |
| 3 | 3 | Não observado | Observada | 38,52 s |
| 4 | 3 | Não observado | Observada | 38,26 s |
| 5 | 2 | Observado | Observada | 38,71 s |

Os 115 arquivos dos cinco inventários foram verificados antes e depois da leitura, sem divergências. [Dados por janela e hashes dos inventários](recuperacao-exploratoria.json). [Script](fontes/analisar_recuperacao.py) e [seis testes de fronteira](fontes/test_recuperacao.py).

As duas leituras respondem a perguntas diferentes. A primeira inclui a obrigação de concluir o aceite no banco; a segunda observa retorno operacional com destinos terminais separados da fila ativa. **Os 14 eventos em DLQ continuam não persistidos.** Não há replay automático, nova classificação de validade ou demonstração de recuperação de desastre. Em nova campanha, os dois indicadores devem ser definidos antes de observar os dados.
