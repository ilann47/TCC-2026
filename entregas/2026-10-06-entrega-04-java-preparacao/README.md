# Entrega 04 — versão de preparação de 06/10/2026

**Não é um fechamento pronto para enviar ao portal.** O enunciado e o prazo da Entrega 04 ainda precisam ser confirmados. O pacote inicia o capítulo 5 com evidências verificadas e prepara a campanha solicitada pela Professora Alessandra Bussador. Não inclui capítulo 6 científico nem afirma que as hipóteses foram confirmadas.

## Arquivos

- `TCC-Entrega04-preparacao.pdf`: texto atual, com capítulo 5 parcial organizado pelos objetivos a–f; declaração de IA preservada, sem resumo em inglês.
- `Apresentacao-Entrega04-preparacao-v3.pptx`: 10 slides editáveis, com notas de fala em linguagem acessível. Não apresenta validações como campanha definitiva.
- `RELATORIO-VERIFICACAO.md`: procedimentos, resultados funcionais, tentativas inválidas e itens ainda necessários.
- `evidencias/catalogo.json`, `evidencias/resumos/`: catálogo das 12 tentativas, resumos de reanálise e checksums. Os dados brutos completos permanecem no ambiente local, identificados no catálogo.
- `fontes-apresentacao/build.mjs`: fonte de geração dos slides; depende do runtime de artefatos descrito no ambiente de trabalho. O PPTX pode ser editado diretamente no PowerPoint.

As fontes atuais do texto estão em `projeto-latex-java`; o código do sistema e dos instrumentos está em `implementacao-java`. A pasta compartilhada `referencias` continua na raiz. Não foram duplicados artigos, volumes Docker, caches, credenciais ou diretórios `target` no pacote.

## O que passou

- 11 testes unitários do sistema e 25 dos instrumentos, sem falhas nas verificações executadas.
- Modelo comum: 50 registros por variante, iguais em UUID, campos, payload e hash, excluindo apenas o instante de inserção.
- Idempotência e conflito: 50 linhas depois do reenvio; 409 síncrono e mensagem conflitante na DLQ assíncrona, sem modificar a linha original.
- Validação curta de rajada: todos os eventos observados conciliados com o banco em ambas as variantes.
- Falha do PostgreSQL: respostas 503 na síncrona; na assíncrona, um aceite foi encaminhado à DLQ após esgotar tentativas. Essa não persistência aparece no texto, não foi escondida.
- Consumidor parado/retomado: em uma nova validação com observação de 40 s, 91/91 eventos ficaram salvos, sem DLQ ou pendência final. A primeira observação curta, com 54 pendentes, foi preservada.
- PDF compilado e páginas alteradas revisadas visualmente; PPTX com validação estrutural, tabelas nativas, notas e renderização. Não houve teste de edição no aplicativo PowerPoint.

## O que falta para fechar

1. Confirmar o enunciado e o prazo do portal.
2. Calibrar e justificar a carga comum de referência.
3. Completar a validação do overhead do gerador, série de backlog/lag e recuperação estável; congelar o protocolo.
4. Executar as dez repetições por condição/variante, com 60 s de aquecimento e 300 s de medição, ou uma mudança metodológica previamente justificada e aprovada.
5. Analisar as repetições, completar as tabelas do capítulo 5 e classificar as hipóteses.
6. Redigir o capítulo 6 (2–4 páginas), sem resultados novos; atualizar resumo e apresentação com os achados finais.

A matriz atual tem 130 execuções. Só aquecimento e medição representam **13 horas**, sem inicialização, intervalo para concluir aquecimento, drenagem, exportações e eventuais repetições inválidas. Este pacote **não reduz** essa exigência nem fabrica números para encerrar a pesquisa.

## Segurança do ambiente

Os experimentos usaram `tcc-entrega04`, sem portas públicas, com outro banco/volumes/tópicos. O banco interativo foi preservado; seus 129 registros do piloto anterior continuavam presentes na conferência final. Ao encerrar, apenas os serviços experimentais foram parados, sem apagar volumes; a aplicação interativa foi retomada e as duas rotas de saúde responderam 200. Os registros sintéticos reinicializados entre ensaios permanecem nas exportações locais anteriores.

Os checksums identificam alterações posteriores, não assinatura de autenticidade. Contagens funcionais e ensaios curtos não são uma análise estatística de superioridade arquitetural.
