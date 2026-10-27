# Campanha reduzida e fechamento científico

**Histórico R1: piloto interrompido por referência não elegível a 48/s.** Não retomar esta sessão nem congelá-la. O usuário escolheu manter a taxa e investigar. Consulte [PILOTO-REJEITADO.md](PILOTO-REJEITADO.md) e a [R2 ativa](../2026-10-27-reduzida65-r2/ACOMPANHAMENTO.md), com estado local separado.

Autorização do usuário em 26/10/2026: atualizar protocolo e metodologia para **65 execuções**, validar o piloto antes, executar e finalizar capítulos 5/6 somente com resultados reais. Acompanhamento automático neste chat foi expressamente autorizado. Este arquivo é um roteiro operacional; o estado efetivo é o JSON local, não um texto de status presumido.

## Arquivos e comandos

Pasta de execução no WSL: `/mnt/c/Users/ilan.wendling/OneDrive/sistemasDeInformacao/TCC/TCC-2026/implementacao-java`.

- Política predeclarada: `policy.json` nesta pasta. Mantém as 13 condições, taxa comum 48/s, 5 blocos, aquecimento 60 s, intervalo 12 s, medição 180 s, drenagem 90 s, falha 40 s iniciada aproximadamente aos 60 s; VUs/limites/imagens inalterados.
- Piloto: `pilot-plan.json`, nove UUIDs próprios, nunca contados como definitivos.
- Campanha: `plan.csv`, 65 UUIDs novos, mesmo dataset por par; ordem embaralhada por semente e primeira variante contrabalançada globalmente. Com cinco blocos, cada condição pareada tem primeira variante em proporção 3/2 ou 2/3, não uma igualdade impossível de 2,5/2,5.
- Estado: `.runtime/reduzida65-2026-10-26/state.json`.
- Logs: `.runtime/reduzida65-2026-10-26/pilot-controller.log`, `campaign-controller.log` e um console por UUID.
- Dados brutos: `.runtime/entrega04/<UUID>-<variante>/`.
- V1 preservada: `experimento/protocolos/2026-10-26-v1-130/`; relatório/calibração e plano de 130 originais também são preservados, nunca contados como executados.

Dentro de `implementacao-java`:

```bash
python3 experimento/reduced_campaign.py status
# Preparação única, sem carga (recusa sessão/plano existente):
python3 experimento/reduced_campaign.py prepare
# Após revisar e commitar o código/metodologia/política:
python3 experimento/reduced_campaign.py launch-pilot
# Somente depois de pilot_complete, auditoria de todos os dados e checkout limpo:
python3 experimento/reduced_campaign.py freeze
# Depois de revisar o congelamento, atualizar os verificadores/docs, commitar e subir:
python3 experimento/reduced_campaign.py launch-campaign
```

Não execute `prepare` novamente nem reinicie uma etapa falha cegamente. `status` é somente leitura. `launch-*` retorna o PID e mantém o processo Linux independente do terminal; o computador/WSL/Docker precisam permanecer ligados. Não suspenda o computador. Não encerre o processo apenas porque não imprime enquanto um ensaio está rodando: confira o console do UUID corrente e o manifesto.

## Sequência e critérios

1. Preservar V1 e publicar política/planos antes de novos dados. Não editar `run.sh`, `load.js`, Java instrumentador ou imagens calibradas.
2. O controlador exige checkout limpo, fingerprints iguais aos calibrados e nenhum projeto `tcc-entrega04` concorrente. Para apenas os contêineres que estavam ativos do projeto interativo `tcc-java-2026`; não para projetos alheios. Registra os concorrentes nos manifests e retoma o interativo ao fim/erro tratável.
3. Piloto funcional: modelo comum síncrono/assíncrono, 50 registros determinísticos e testes de idempotência/conflito; comparação independente em Java excluindo apenas `persisted_at`.
4. Piloto de duração: steady 48/s em ambas, burst 48→96→48 em ambas, PG-stop 12/s em ambas e consumer-stop 12/s apenas assíncrona. Mantém 180 s medidos, 60 s de aquecimento, drenagem 90 s e falha 40 s. Essas sete coletas verificam as mudanças de duração; não estimam variância de cinco repetições nem capacidade máxima.
5. Exigir instrumentação íntegra, identidades/manifests corretos, hashes e margens originais de gerador/observador. Steady deve satisfazer os critérios de referência já predeclarados. Falhas precisam mostrar recuperação sustentada dentro da carga ativa; consumidor parado precisa conciliar seus aceitos no banco. No PG, DLQ terminal pode ocorrer e deve ser reportada como não persistência, não escondida. Erros/drops em rajada são resultados, não motivo para trocar a carga por outra mais conveniente.
6. Falha do piloto: estado `attention_required`; preservar tudo, diagnosticar, explicar qualquer revisão e gerar nova identificação se necessário. Não alongar retrospectivamente a janela para transformar uma falha de recuperação em sucesso. Não afrouxar critérios para iniciar a campanha.
7. Piloto aprovado: `freeze` audita novamente os nove conjuntos, publica resumos/catalogação sem caminhos pessoais e congela V2 ativa. Revisar o catálogo e os checksums, atualizar `verify-frozen.mjs`/`campaign.sh` e READMEs que ainda assumem 130/300/10. Fazer commit/push antes das execuções definitivas. O guard Java existente lê os parâmetros do JSON e não precisa ser reconstruído.
8. Executar somente os 65 UUIDs do plano. Parar para investigação se a coleta ou a folga dos instrumentos falhar. Não descartar um ensaio só por contradizer a hipótese; timeout, erro HTTP, DLQ e recuperação não observada são resultados possíveis. Não sobrescrever pastas existentes, não contar piloto/demonstração como definitivos e não repetir até obter significância ou uma arquitetura vencedora.

Os tempos configurados somam **6 h 10 min 30 s** para 65 execuções, sem preparação/exportação/análise, nem o piloto adicional. O prazo real será maior. A redução perde resolução temporal e precisão entre repetições em relação à V1; não afirmar equivalência de poder estatístico. São cinco repetições por condição por escolha de orçamento autorizada, não um tamanho amostral universalmente suficiente.

## Após os dados

- Conferir exatamente 65 coletas válidas, cinco por condição/variante e datasets pareados. Publicar catálogo e cópias dos resumos com hashes, mantendo brutos locais e tentativas inválidas identificadas.
- Agregar por **execução** e por **par**, não transformar milhares de eventos correlacionados em milhares de repetições. Mostrar valores por repetição, média/mediana, desvio-padrão, mínimo/máximo e diferenças pareadas. Não alegar significância estatística ou usar intervalos injustificados com n=5. Resultados inconsistentes/inconclusivos permanecem assim.
- Capítulo 5 na ordem da orientadora: ferramentas/piloto; modelo comum (a); síncrona (b); assíncrona (c); execução dos cenários (d); tabelas comparativas (e); trade-offs/hipóteses (f); limitações. Incorporar calibração de 26/10 separadamente dos definitivos e da preparação histórica.
- Sempre separar HTTP de envio→commit. Informar número de commits observados e destinos dos não gravados. Vazão somente dentro da janela; drenagem não infla o throughput. DLQ é não persistência terminal, não desaparecimento nem reprocessamento automático. Recursos de sistema e instrumentos separados; contêiner parado não significa eficiência.
- Hipóteses do texto: menor complexidade/custo síncrono em carga reduzida; menor latência de aceitação e retenção na indisponibilidade do consumidor na assíncrona; contrapartida de recursos e distância aceite/conclusão. Operacionalizar somente o que foi medido. Quantidade de componentes não comprova esforço de manutenção/custo financeiro; deixar esses aspectos descritivos/inconclusivos, sem inventar medidas.
- Capítulo 6: **2 a 4 páginas**, pergunta e resposta direta, situação de a-f, destino de cada hipótese, recomendações limitadas ao medido, limitações e trabalhos futuros; nenhum resultado novo. Habilitar sua inclusão em `modelo.tex` somente após redação sustentada pelos dados.
- Corrigir trechos desatualizados do método/resultados/resumo/status que dizem que a instrumentação ainda não existe ou que são dez repetições/300 s. Não modificar entregas históricas.
- Compilar com MiKTeX no Windows (`pdflatex`, `bibtex`, duas novas passagens), verificar logs e usar Poppler/renderização para QA do PDF. Seguir a skill PDF na sessão que editar o documento. Fontes continuam em `projeto-latex-java`; destino final e nova entrega histórica devem ser claramente identificados. Não publicar brutos indiscriminadamente ou segredos.
- Testar, commitar e subir à main, confirmar remoto e entregar links dos arquivos reais. Não anunciar “TCC finalizado” antes disso. Ao concluir toda a tarefa, desativar a automação `tcc-campanha-reduzida-e-cap-tulos-finais`.

## Como acompanhar sem duplicar trabalho

O monitor deve ficar silencioso enquanto a execução estiver normal. Avisar apenas em conclusão, falha, decisão necessária ou mudança acionável. Se o controlador morrer, conferir estado/logs/UUIDs antes de qualquer retomada. O controlador recusa diretórios já existentes não confirmados no diário; uma substituição exige auditoria e novo UUID, nunca limpeza da evidência anterior.

Este roteiro não concede permissão para ações fora da autorização do usuário, como parar outros projetos, reconstruir imagens durante medição ou inventar/selecionar resultados. Mudanças de parâmetros depois de dados definitivos exigem identificação e justificativa de revisão, preservando os resultados afetados.
