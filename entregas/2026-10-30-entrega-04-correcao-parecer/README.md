# Entrega 04 revisada conforme parecer de correções

Revisão de 30/10/2026 do TCC de Ilan Wendling Thoele, orientado pela Profa. Dra. Alessandra Bussador, cuja titulação foi confirmada pelo autor. O [PDF corrigido](TCC-Entrega04-correcoes.pdf) é o documento atual; a [entrega de 27/10](../2026-10-27-entrega-04-java-final/) permanece histórica, sem substituir seu PDF ou apresentação.

O [relatório de atendimento](ATENDIMENTO-PARECER.md) compara os 17 itens do parecer com o texto anterior e registra a alteração e os limites. O parecer original não é redistribuído: sua referência e seu hash identificam o documento utilizado.

A [apresentação corrigida e editável](Apresentacao-Entrega04-correcoes.pptx) acompanha este PDF. São dez slides principais com [roteiro sugerido de cinco minutos](ROTEIRO-APRESENTACAO.md) e sete slides de apoio para perguntas. O tempo precisa ser ensaiado pelo autor. Os apoios incluem requisitos esperados versus obtidos, recuperação exploratória, contribuições, literatura, gráficos de latência e recursos, uso de IA e limites. Tabelas e gráficos permanecem editáveis, com notas e fontes em todos os slides.

As medições e classificações da campanha não foram alteradas: são 65 coletas, 64 completas e uma parcial, sem reposição. A comparação primária de conclusão com banco parado conserva quatro pares completos. A nova leitura de recuperação é **exploratória e pós-hoc**, não substitui o veredito original nem transforma DLQ em persistência. Veja [método e resultado da reanálise](RECUPERACAO-EXPLORATORIA.md), [dados por janela](recuperacao-exploratoria.json) e [script](fontes/analisar_recuperacao.py).

## O que mudou

Resumo e abstract usam linguagem direta e números com contexto; a metodologia concentra escolha das ferramentas e definições. O capítulo 4 descreve instrumentos já construídos e reduz propostas não implementadas. O capítulo 5 inclui requisitos esperados versus obtidos, discussão com a literatura, pontos fortes e recuperação exploratória. A conclusão acrescenta avaliação do sistema e contribuições. Referências oficiais, unidades, acentos, listas e sumário foram revistos. Identificadores e caminhos técnicos ficam no apêndice.

## Pendências externas à edição

- O autor informou que **ainda fará a revisão pessoal integral** do código, protocolo, tabelas e conclusões antes da entrega. A declaração de IA registra esse estado, sem afirmar uma revisão já concluída. Após essa conferência, o texto da declaração deve ser atualizado de forma verdadeira.
- Data, examinadores e assinaturas da folha de aprovação dependem da instituição. A folha está preparada sem simular aprovação.
- O parecer cita um Documento Mestre não anexado a este pedido. Esta revisão atende aos itens concretos transcritos no parecer; não certifica conferência integral de um documento não fornecido.
- Esta publicação não realiza submissão ao portal ou aprovação acadêmica. O PDF foi publicado primeiro e a apresentação foi alinhada em seguida, nesta mesma entrega datada. Alterações locais independentes do painel/seminário não fazem parte desta revisão.

## Reprodução e verificação

Fontes editáveis em [projeto-latex-java](../../projeto-latex-java/README.md). Com MiKTeX e BibTeX instalados, o [script PowerShell](fontes/compilar.ps1) faz cópia limpa dos fontes para uma pasta nova, executa LaTeX, BibTeX e três passagens adicionais e rejeita referências indefinidas e caixas excedentes. O parâmetro `-disable-installer` impede instalação automática no MiKTeX utilizado nesta revisão. Para TeX Live, use as passagens equivalentes sem essa opção específica do MiKTeX.

```powershell
# Na raiz do repositório; escolha uma pasta nova, que ainda não exista.
.\entregas\2026-10-30-entrega-04-correcao-parecer\fontes\compilar.ps1 -Repo . -Build "C:\temp\tcc-revisao-parecer"
python .\entregas\2026-10-30-entrega-04-correcao-parecer\fontes\verificar.py
python .\entregas\2026-10-30-entrega-04-correcao-parecer\fontes\verificar_apresentacao.py
python -m unittest discover -s .\entregas\2026-10-30-entrega-04-correcao-parecer\fontes -p test_recuperacao.py
python .\implementacao-java\experimento\verify_final_results.py
```

O script exploratório precisa das cinco pastas brutas preservadas localmente; ele não inicia serviços, carga ou campanha e recusa sobrescrever sua saída. A verificação pública do relatório e dos hashes não exige os brutos. O índice [SHA256SUMS](SHA256SUMS) cobre este pacote; a precisão integral da campanha permanece no catálogo original.

O [fonte JavaScript da apresentação](fontes/atualizar_apresentacao.mjs) importa a versão histórica de 27/10 e grava uma saída nova, sem alterar a apresentação anterior. Requer Node, Python e `@oai/artifact-tool` no ambiente configurado, além dos validadores da skill Presentations. Informe os caminhos em `RUNTIME_NODE_MODULES`, `RUNTIME_PYTHON` e `PRESENTATIONS_SKILL_DIR`, e passe a raiz do repositório e um caminho PPTX novo como argumentos. O verificador público usa apenas a biblioteca padrão do Python e confere o PPTX, as notas, as tabelas e os dados incorporados dos gráficos. A revisão não incluiu abertura no aplicativo Microsoft PowerPoint.
