# Entrega 04 - esclarecimento sobre o painel

Revisão adicional de **24/11/2026**, posterior aos [três ajustes documentais da mesma data](../2026-11-24-entrega-04-ajustes-banca/). Esta pasta é uma nova entrega; os PDFs anteriores não foram substituídos.

- [PDF desta revisão](TCC-2026-justificativa-painel.pdf): **93 páginas**.
- [Cópia idêntica em `output/pdf`](../../output/pdf/TCC-2026-justificativa-painel-2026-11-24.pdf).
- [Fonte LaTeX atual](../../projeto-latex-java/modelo.tex).
- [SHA-256 do documento](SHA256SUMS).

## Ajuste solicitado

Na seção **4.5.1**, logo após a descrição do processo Python, o texto esclarece que o painel foi implementado depois da campanha, como camada de apresentação separada das aplicações de negócio Java. Ele não participou das medições e seu consumo de recursos não compõe a comparação experimental. Essa separação não é atribuída à linguagem utilizada.

A área de resultados apenas consulta os relatórios publicados, com verificação dos hashes. O serviço Python também controla demonstrações locais, separadas da campanha científica. Assim, o texto não confunde a consulta somente leitura com a execução de cargas sintéticas no ambiente demonstrativo.

O acréscimo está na **página 61 do visualizador**, contando a capa, correspondente à página impressa 60. Os ajustes anteriores da declaração de IA, das tecnologias na seção 4.6.1 e da cronologia da Figura 17 foram mantidos.

## Conferência e preservação

- Compilação isolada com BibTeX e quatro passagens LaTeX, sem referências indefinidas, destinos duplicados ou caixas excedentes sinalizadas pelo verificador.
- Comparação do texto e da renderização das 93 páginas com o PDF anterior de 24/11: **somente a página 61 mudou**. Inspeção visual ampliada dessa página e da transição para a Figura 17.
- Nenhuma página vazia ou marcador `??`. As quatro capturas originais continuam presentes, sem alteração dos fluxos JPEG, nas páginas 62, 79, 80 e 81.
- Resultados, conclusões, declaração de IA, tabelas, instrumentos, código executável e dados da campanha não foram alterados. Permanecem 65 coletas planejadas, 64 completas e uma parcial A1, sem reposição ou reclassificação.
- O PDF anterior preserva o SHA-256 `eefe7a63e3f6a89e919bdc1a25e5d0febafb398ec3c80decaa88b41e34e852c2`. As duas cópias desta revisão possuem o mesmo hash, indicado em `SHA256SUMS`.
- Não houve execução de novas cargas nem alteração de código de aplicação; a suíte unitária não foi repetida nesta revisão exclusivamente documental.

As verificações técnicas e a revisão pessoal já confirmada pelo autor não equivalem a aprovação institucional ou submissão ao portal.
