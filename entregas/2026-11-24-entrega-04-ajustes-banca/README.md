# Entrega 04 - ajustes documentais para a banca

Revisão de **24/11/2026**, limitada aos três ajustes solicitados após a inclusão das telas do painel. A [entrega de 23/11](../2026-11-23-entrega-04-paineis/) permanece preservada. Não houve alteração no código executável, nos instrumentos, nas capturas, nos dados ou na classificação das coletas.

## Documento atualizado

- [PDF desta entrega](TCC-2026-ajustes-banca.pdf): **93 páginas**, a mesma quantidade da revisão anterior.
- [Cópia idêntica em `output/pdf`](../../output/pdf/TCC-2026-ajustes-banca-2026-11-24.pdf).
- [Fonte LaTeX atual](../../projeto-latex-java/modelo.tex).
- [Hash SHA-256](SHA256SUMS).

## Atendimento dos três ajustes

As páginas abaixo são as do visualizador, contando a capa como página 1.

| Solicitação | Aplicação | Página |
| --- | --- | --- |
| Declaração de IA: incluir o painel e atualizar a revisão pessoal | Finalidades incluem painel React/Vite, serviço Python e documentação das capturas. O autor confirmou pessoalmente em 24/11/2026 a revisão desses itens, complementando a confirmação de 06/11 sobre código, método, tabelas e conclusões. Não se declara aprovação institucional. | 4 |
| Tecnologias do painel também na seção 4.6.1 | Frase com React, shadcn/ui, Tailwind CSS, Vite e Python, distinguindo a apresentação posterior do caminho de negócio medido. | 63 |
| Figura 17: esclarecer a data da demonstração | Texto e fonte da figura indicam que a demonstração de 27/10 ocorreu depois do encerramento das coletas. A captura continua identificada como registrada em 23/11. | 61 e 62 |

A inclusão redistribuiu a Tabela 5 e parágrafos nas páginas 63 a 65; a lista de tabelas foi atualizada na página 8. As únicas páginas com texto ou renderização diferentes da edição de 23/11 são **4, 8, 61, 62, 63, 64 e 65**.

## Cronologia e limites

O [catálogo publicado da campanha](../../implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/catalog.json) registra o encerramento em 27/10/2026 às **17h01 de Brasília**. O registro local da execução assíncrona `bdc0bf05-2bb9-41c3-85f5-70c129fa1f18`, mostrado na Figura 17, registra início às **20h57min51s** e fim às **20h58min32s**, no mesmo fuso e dia. Isso sustenta o esclarecimento de que é uma demonstração posterior, não uma das coletas científicas. Os arquivos de runtime locais não são incluídos nesta entrega.

O painel de resultados consulta os relatórios; o serviço Python entrega a interface e controla demonstrações locais separadas. Não substitui as aplicações de negócio Java nem passa a integrar os recursos medidos na campanha. O texto mantém a advertência sobre acesso local confiável ao socket Docker e sobre a ausência de autenticação de produção.

Permanecem **65 coletas planejadas, 64 completas e uma parcial A1**, sem reposição, imputação ou reclassificação. As quatro capturas mantêm exatamente os arquivos de imagem anteriores, nas páginas 62, 79, 80 e 81. Resultados e conclusões permanecem iguais; o capítulo 6 ocupa quatro páginas. Esta revisão não acrescenta medições ou resultados novos.

## Verificação desta revisão

- Compilação isolada com BibTeX e quatro passagens LaTeX, sem referências indefinidas, destinos duplicados ou caixas excedentes sinalizadas pelo verificador.
- Inspeção visual das sete páginas alteradas; comparação de texto e renderização das 93 páginas com a edição anterior. As demais 86 páginas são idênticas, inclusive resultados, conclusões e as três telas de resultados.
- Nenhuma página vazia ou marcador `??`; os quatro JPEG originais foram encontrados sem alteração nos fluxos de imagem do PDF.
- Cópias finais com o mesmo SHA-256. Somente fontes documentais e arquivos desta revisão foram preparados para publicação; o código executável não foi alterado e sua suíte de testes não foi repetida.

Para conferir o arquivo no PowerShell, nesta pasta:

```powershell
Get-FileHash .\TCC-2026-ajustes-banca.pdf -Algorithm SHA256
```

Compare com `SHA256SUMS`. A confirmação de revisão do autor não equivale a aprovação da orientadora, da banca ou a submissão institucional. Os campos institucionais não confirmados continuam sem preenchimento inventado.
