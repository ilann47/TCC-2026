import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile, FileBlob } from '@oai/artifact-tool';
const repo=path.resolve(process.argv[2]);
process.env.RUNTIME_NODE_MODULES='C:/Users/ilan.wendling/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_PYTHON='C:/Users/ilan.wendling/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const skill='C:/Users/ilan.wendling/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const tmp=path.join(repo,'implementacao-java/.runtime/entrega04-presentation');
const dest=path.join(repo,'entregas/2026-10-06-entrega-04-java-preparacao/Apresentacao-Entrega04-preparacao-v3.pptx');
const { resolvePresentationFont,finalizePresentation }=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const font=resolvePresentationFont();
console.log('font='+font);
const pres=Presentation.create({slideSize:{width:1280,height:720}});
function text(s,value,x,y,w,h,size=28,bold=false,color='#172B4D'){
  const shape=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  shape.text=value;shape.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none'};return shape;
}
function slide(title,notes){
  const s=pres.slides.add();s.background.fill='#FFFFFF';
  text(s,title,70,52,1140,110,38,true);
  text(s,String(pres.slides.items.length),1170,655,50,30,18,false,'#64748B');
  s.speakerNotes.textFrame.setText(notes);return s;
}
function body(s,rows){rows.forEach((r,i)=>text(s,r,72,200+i*104,1120,88,30));}
function table(s,values,widths,top=200,height=380,size=23){
  const t=s.tables.add({rows:values.length,columns:values[0].length,left:72,top,width:1136,height,columnWidths:widths,values});
  t.borders.assign({style:'solid',fill:'#CBD5E1',width:1});
  for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
    const cell=t.getCell(r,c);cell.fill=r===0?'#172B4D':'#FFFFFF';
    cell.text.style={typeface:font,fontSize:size,color:r===0?'#FFFFFF':'#172B4D',bold:r===0,autoFit:'none'};
  }
  return t;
}
let s=slide('Comunicação síncrona via REST e assíncrona orientada a eventos',
  'Hoje eu vou mostrar a passagem do desenvolvimento para a etapa de experimentação. As duas versões do sistema já existem em Java, mas ter o código funcionando não é a mesma coisa que ter a comparação científica concluída. Então a apresentação separa o que foi verificado do que ainda precisa ser medido com repetições. A ideia é deixar claro como vamos conseguir responder à pergunta do trabalho, sem escolher de antemão uma arquitetura vencedora. Esta é uma versão de preparação da Entrega 04, não uma apresentação de resultados definitivos.');
text(s,'Análise experimental no processamento de registros',72,250,1120,110,34);
text(s,'Ilan Wendling Thoele\nOrientadora: Professora Alessandra Bussador',72,430,1120,100,25);
text(s,'Validação e preparação experimental • 06/10/2026',72,590,1120,46,22,false,'#475569');
s=slide('O que a pesquisa quer responder?',
  'A pergunta é sobre os trade-offs, ou seja, o que a gente ganha e o que precisa aceitar em troca. Nos dois casos o destino dos registros é o mesmo PostgreSQL. O que muda é o caminho até ele. Eu não quero comparar um sistema simples com outro cheio de regras diferentes, porque isso misturaria as causas dos resultados. Por isso o contrato, o processamento e a persistência são compartilhados. Também não vou dizer que REST ou Kafka são melhores em geral. A resposta precisa ficar limitada ao computador, às configurações e às cargas realmente testadas.');
text(s,'Quais trade-offs de desempenho e resiliência aparecem nas duas implementações?',72,205,1120,190,44,true);
text(s,'Mesmo contrato, processamento e PostgreSQL.\nO caminho de processamento é diferente.',72,470,1120,130,30);
s=slide('A resposta de sucesso significa coisas diferentes',
  'Na síncrona, a API recebe o registro, faz a validação e tenta gravar no banco antes de responder. Então o sucesso vem depois da transação. Na assíncrona, a API publica no Kafka e responde quando recebe a confirmação da publicação. O consumidor faz a gravação em outra etapa. Esse detalhe é central: se eu olhar só o tempo do HTTP, posso achar que a assíncrona resolveu tudo mais rápido, mas talvez o registro ainda esteja esperando para ser salvo. Para fazer uma comparação justa, os dois tempos precisam aparecer separados.');
body(s,['Síncrona: 201 após confirmar a transação no banco.','Assíncrona: 202 após o aceite da publicação no Kafka.','202 não significa que o registro já foi salvo.']);
s=slide('Por que usar k6? Não é uma disputa entre ferramentas',
  'Eu examinei a documentação das duas ferramentas. O JMeter é uma alternativa válida, inclusive possui um grupo de execução de modelo aberto. Então não seria correto falar que só o k6 consegue controlar chegadas. A escolha aqui foi pela integração: o script do k6 já gera os identificadores, separa as fases e exporta as tags que o analisador Java usa. Isso facilita revisar e repetir os testes pelo Git e pelo Docker. Eu não medi qual gerador é mais rápido. Fontes: https://jmeter.apache.org/usermanual/best-practices.html ; https://jmeter.apache.org/usermanual/component_reference.html#Open_Model_Thread_Group ; https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/ ; https://grafana.com/docs/k6/latest/results-output/real-time/json/ .');
table(s,[['Critério','JMeter','k6'],['Plano','JMX e interface gráfica','JavaScript versionado'],['Carga','CLI recomendado','CLI em Docker'],['Chegadas','Open Model Thread Group','Constant / ramping arrival'],['Saída','JTL / CSV','JSONL e tags por evento']],[240,448,448],180,390,24);
text(s,'Escolha: integração com os identificadores e o analisador Java.',72,590,1136,50,25);
s=slide('As duas variantes salvaram o mesmo conjunto',
  'Antes de olhar velocidade, a gente conferiu se as duas versões fazem o mesmo trabalho. Foram enviados cinquenta registros com conteúdo determinístico a cada uma. Isso significa que o identificador e os dados não dependem do momento do envio ou da versão executada. A comparação confirmou os mesmos campos, payloads e hashes. Só o instante de inserção ficou de fora, porque as gravações aconteceram em horários diferentes. O reenvio igual não criou uma segunda linha. Já o conteúdo divergente recebeu 409 na síncrona e foi encontrado na DLQ da assíncrona depois do aceite 202. Esse teste passou para o conjunto examinado, mas não prova todos os casos possíveis nem desempenho. Fonte: comparação das execuções e71d7147-04f8-41bc-b44c-30b6857b41cb e 6cdf03fd-1d50-45b3-b77e-1afd41691e95, catálogo de evidências.');
table(s,[['Verificação','Resultado observado'],['Conjunto comum','50 linhas em cada variante'],['Equivalência','UUIDs, campos, payloads e hashes iguais'],['Reenvio igual','50 linhas; duplicate em ambas'],['Mesmo UUID, conteúdo diferente','409 síncrono; conflito na DLQ assíncrona']],[340,796],180,390,26);
text(s,'Verificação funcional não é benchmark de desempenho.',72,590,1136,50,25);
s=slide('Banco parado: um aceite terminou na fila de falhas',
  'O piloto inicial conferiu a instrumentação, com vinte e um eventos síncronos e vinte assíncronos conciliados. Depois houve uma validação curta com o banco parado nas duas versões. Na síncrona, foram observados noventa e um envios, trinta e nove sucessos e cinquenta e dois retornos 503. Na assíncrona, os noventa envios receberam 202, mas um ficou na DLQ ao esgotar as tentativas; oitenta e nove foram salvos. A mensagem não desapareceu, só que também não virou registro no banco. Essa observação impede prometer gravação automática de tudo depois da recuperação. Não é uma estimativa geral de taxas: houve uma execução curta por variante e a carga efetiva diferiu em um evento. Fontes: relatório do piloto e execuções f53dad57-5b76-425a-8bad-44add2111a9f e a5f30182-e7de-47d1-a13a-1a6c1047e6f4 no catálogo.');
table(s,[['Validação curta','Síncrona','Assíncrona'],['Envios observados','91','90'],['HTTP de sucesso','39','90'],['Salvos / DLQ terminal','39 / 0','89 / 1']],[520,308,308],200,300,28);
text(s,'Uma validação por variante. Não confirma desempenho superior.',72,560,1136,65,28,true);
s=slide('Medir resposta e gravação separadamente',
  'O analisador mantém três intervalos diferentes. O primeiro é o tempo HTTP que o próprio k6 fornece. O segundo começa no marcador de envio e termina quando o código do cliente conferiu o retorno. E o terceiro termina no marco emitido depois que a transação voltou. Esse último não é o campo persisted_at, porque aquele campo é preenchido durante o INSERT. Também calculamos registros efetivamente confirmados dentro da janela divididos pela duração da janela. Se um registro ficou pronto depois, na drenagem, ele não aumenta artificialmente o throughput da medição anterior.');
table(s,[['Métrica','O que termina a medição'],['Tempo HTTP','Retorno da requisição'],['Envio → resposta','Marcador do cliente após conferir o retorno'],['Envio → commit','Retorno da transação confirmado pelo servidor'],['Throughput concluído','UUIDs com commit na janela / segundos']],[370,766],190,380,25);
s=slide('A campanha planejada cobre carga e falhas',
  'A carga baixa é o menor nível da carga crescente; a mesma execução pode atender aos dois objetivos, sem contar como duas repetições. Depois vêm os demais níveis e uma rajada. Para a falha comparável, o banco é interrompido nas duas versões. Existe ainda um teste específico da assíncrona com o consumidor parado: ali o Kafka pode acumular os eventos enquanto o banco continua disponível. Isso é diferente de deixar o consumidor tentando gravar em um banco parado, pois ele pode esgotar tentativas e mandar mensagens para a DLQ. Cada condição precisa de dez repetições, com a ordem registrada.');
table(s,[['Cenário','Condição','Comparação'],['C1 / C2','25%, 50%, 75%, 100% da referência','Ambas'],['C3','Rajada acima da referência','Ambas'],['C4 / C5','Banco parado e retomado','Ambas'],['Complementar','Consumidor parado e retomado','Assíncrona']],[210,730,196],185,360,24);
text(s,'Planejado: 60 s de aquecimento + 300 s de medição, 10 repetições.',72,580,1136,70,24);
s=slide('O que torna as medições conferíveis?',
  'Cada execução ganha uma pasta própria e um manifesto com parâmetros, commit, imagens e limites. O ambiente experimental tem outro nome, outra rede e outros volumes, para não apagar os dados da aplicação que usamos pelo Swagger. Os dados brutos do k6 são preservados comprimidos, junto com os logs, as exportações do banco, do tópico e da DLQ. Os checksums ajudam a perceber alterações posteriores, mas não são uma assinatura que prova autenticidade. Também precisamos guardar as tentativas inválidas com o motivo. Resultado ruim para a hipótese não é motivo para descartar um teste.');
body(s,['Ambiente Docker isolado e dados sintéticos.','UUID por execução e conteúdo comum por par.','Manifesto, dados brutos, conciliação e checksums.','Tentativas inválidas preservadas com o motivo.']);
s=slide('O que ainda falta para a conclusão científica?',
  'O próximo ponto é confirmar a carga de referência e congelar os parâmetros antes da campanha. Depois precisamos completar as repetições, comparar os resultados por execução e só então responder às hipóteses. Não adianta ter milhares de eventos em um único ensaio e tratar isso como milhares de experimentos independentes. Também temos limitações: tudo roda em um computador, com dados sintéticos, um broker e uma partição. Então as recomendações precisam caber nesse recorte. O capítulo seis vai usar somente os resultados apresentados antes, sem trazer novos números ou escolher um vencedor porque era o esperado.');
body(s,['Calibrar a carga e congelar o protocolo.','Executar as repetições e analisar a dispersão.','Responder às hipóteses com o que foi medido.','Limites: um computador, um broker, dados sintéticos.']);
await fs.mkdir(tmp,{recursive:true});
const candidate=path.join(tmp,'candidate.pptx');
await (await PresentationFile.exportPptx(pres)).save(candidate);
const result=await finalizePresentation({workspaceDir:repo,candidatePath:candidate,finalPath:dest,
  pythonExecutable:'C:/Users/ilan.wendling/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...[4,5,6,7,8].flatMap(n=>['--require-native-table-slide',String(n)])],
  explicitTotalSlideCount:10, requiredNativeTableOwnerSlides:[4,5,6,7,8],
  fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
  receiptPath:path.join(tmp,'validation-v3.json')});
console.log(JSON.stringify({sha256:result.finalSha256,integrity:result.packageIntegrity.status,layout:result.presentationLayout.exitCode,import:result.firstPartyImport.passed}));
const rendered=await PresentationFile.importPptx(await FileBlob.load(dest));
for(let i=0;i<rendered.slides.items.length;i++){
  const p=await rendered.export({slide:rendered.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(tmp,`slide-${i+1}.png`),new Uint8Array(await p.arrayBuffer()));
}
