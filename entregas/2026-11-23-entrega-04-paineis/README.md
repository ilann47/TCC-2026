# Entrega 04 - painel implementado e capturas no TCC

Revisão documental de **23/11/2026**, posterior à campanha R2/A1 e às correções do parecer. Esta pasta é uma entrega nova; não substitui os PDFs, slides ou dados das entregas históricas.

## Documento para leitura

- [PDF desta entrega](TCC-2026-paineis.pdf): **93 páginas**.
- [Mesma versão em `output/pdf`](../../output/pdf/TCC-2026-paineis-2026-11-23.pdf).
- [Fonte LaTeX editável](../../projeto-latex-java/modelo.tex).
- [Capturas originais da interface](../../projeto-latex-java/Imagens/painel/).
- [Hashes do pacote](SHA256SUMS).

## Capturas acrescentadas

As páginas abaixo são as do visualizador, contando a capa como página 1. A numeração impressa nessas páginas é uma unidade menor.

| Figura | Página do PDF | Conteúdo e interpretação |
| --- | --- | --- |
| 17 | 62 | Controles da demonstração k6 e histórico anterior. É uma demonstração separada, não resultado adicional da campanha. |
| 18 | 79 | HTTP e envio até commit em gráficos pareados separados, a 48 eventos/s, com cinco pares. |
| 19 | 80 | Sete recortes de consulta: quatro cargas constantes, rajada, banco parado e consumidor parado. Correspondem às treze condições por variante. |
| 20 | 81 | Destinos finais e recuperação: 14 eventos em DLQ; resultado original 1/5 e leitura exploratória 5/5 separados. |

As três figuras de resultados estão em páginas horizontais para preservar espaço de leitura. Todas as imagens são capturas reais da aplicação, registradas nesta revisão, sem alterar valores ou gerar uma nova carga para compor as telas.

## Alinhamento documental

- O capítulo 4 descreve o painel Python/React implementado, seus filtros e a área de demonstração. A interface é posterior à campanha e não integra o caminho de recursos medido originalmente.
- O capítulo 5 contextualiza as telas como visualização dos relatórios públicos verificados, sem nova medição, reclassificação ou imputação.
- UC06, RF14 e RNF10 passam a mencionar a consulta gráfica efetivamente disponível. **RF15 permanece parcial**: configurar k6 não equivale ao formulário manual próprio dos wireframes.
- A conclusão apenas alinha a descrição da consulta ao que foi implementado; continua com quatro páginas, sem resultados novos.
- A declaração de IA mantém o texto da confirmação de revisão pessoal de 06/11/2026. Não se afirma nova revisão pessoal ou aprovação institucional das capturas.
- O painel mantém as seções de comparação e repetições abertas. O título exclusivo do apresentador foi removido, preservando a interpretação.

## Preservação dos resultados

Permanecem **65 coletas planejadas, 64 completas e uma parcial A1**, sem repetição ou substituição. São cinco tentativas por condição; o banco parado conserva quatro pares completos para a comparação primária de conclusão. HTTP 503 continua erro, mesmo na persistência final comprovada. Os 14 destinos em DLQ não são gravações no PostgreSQL. A leitura exploratória não substitui o resultado original.

As capturas não demonstram desempenho de uma nova campanha. O painel de resultados é somente leitura. A demonstração k6 envia eventos sintéticos aos serviços e pode gravá-los no banco interativo; seu histórico é separado dos arquivos científicos, ela não mede envio-commit no teste curto e não inicia a campanha definitiva.

## Conferências

- Compilação em diretório novo, com BibTeX e passagens LaTeX completas; sem referências indefinidas ou caixas excedentes sinalizadas pelo verificador de compilação.
- Revisão visual das 93 páginas e inspeção ampliada das quatro figuras, sumário e listas.
- Declaração de IA textualmente idêntica à edição anterior; nenhuma página vazia ou marcador `??` no PDF.
- 21 testes Node, 91 testes Python do painel, 39 testes Python dos instrumentos, 24 verificações de menu, cinco de comparação e seis do iniciador PowerShell aprovados: **186 testes/verificações locais**. Configuração Compose e fingerprints do protocolo também conferidos.
- Nenhum arquivo dos instrumentos, plano, diário, resumos originais ou dados da campanha foi modificado nesta entrega.

Para conferir o arquivo no PowerShell, nesta pasta:

```powershell
Get-FileHash .\TCC-2026-paineis.pdf -Algorithm SHA256
```

Compare com a entrada correspondente de `SHA256SUMS`. A conferência técnica não representa aprovação da orientadora, da banca ou submissão institucional. O autor ainda deve conferir a nova inclusão antes de enviar o documento.
