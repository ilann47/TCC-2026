# Versão das fontes e proveniência

O fechamento científico que gerou o documento, os dados e os capítulos 5/6 está no commit [771d7a621c31aaccda7359b8207979c4bc84f19d](https://github.com/ilann47/TCC-2026/tree/771d7a621c31aaccda7359b8207979c4bc84f19d). O empacotamento e a nova apresentação foram publicados em [71df262](https://github.com/ilann47/TCC-2026/tree/71df262ca6af10a13a0c698459add60622bba32e). A revisão editorial posterior esclarece apenas o resumo português e alinha o abstract no fonte, sem alterar medições, classificações, análises ou capítulos.

- Texto: `projeto-latex-java/modelo.tex` e arquivos do projeto no commit científico, com revisão editorial posterior em `Configuracoes/dados_documento.tex` registrada em [revisao-resumo.json](evidencias/revisao-resumo.json).
- Resultados: `implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/` no mesmo commit.
- Coleta: 37 tentativas sob `f5d77b500ac9e1afe26d1d52068054e59a17f74d` e 28 sob `cb3e9b30e9d86ce4b288a6d8f0f917c4b342d409`, com instrumentos, imagens, plano e parâmetros medidos preservados.
- Revisão formal intermediária: `effa20b9a1c9c597e1154d526e503715ad09876d`.
- Apresentação: nova revisão do PPTX histórico da preparação, com dados definitivos derivados dos JSON públicos e ressalvas nos slides/notas. A versão de preparação não foi alterada.

O PDF atual nesta entrega é byte a byte o mesmo de `output/pdf/TCC-2026-final.pdf`. Seu SHA-256 é `56431f7482c5f90eec7a4501dabc70da1a965fceed49e660913b8495e4aed1e5`. O PDF anterior permanece recuperável nos commits citados, com SHA-256 `46b54cf04f64f33a4ac5f3fe65ff58b8f6555a2899d0046ba3398fceedf05182`; esse é o artefato descrito na validação científica histórica preservada.

O PPTX atual tem SHA-256 `71be8450168428ef77c447068c0b22e21bd51eeaec329194b0a96aefcbe77f33`. A revisão pontual esclareceu a parcial nos slides 6/8 e notas 1/6/8, preservando o visual dos demais slides e os resultados. A [proveniência dessa revisão](evidencias/revisao-apresentacao.json) registra também as fontes. O PPTX anterior permanece recuperável no commit `526b19e`, com SHA-256 `43e8b0ea342d3f550c16465d0020f4a68380e5c296e68abb5e95fc0a1d64e247`. O histórico visual de referência tem SHA-256 `e62e863808e8e3d44e79eea2314299a69b716b2ca1b86a0146fd709ca155834b`. O runtime utilizado foi `@oai/artifact-tool` 2.8.99, com fonte Arial, dimensões 1280 x 720 px, tabelas e texto nativos.

O catálogo e a validação científica em `evidencias/` são cópias dos arquivos publicados no fechamento, não uma nova auditoria dos brutos nem reclassificação de tentativas. O relatório desta entrega distingue os controles científicos originais das novas verificações de empacotamento/apresentação.
