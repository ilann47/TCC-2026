// Edit the published deck in a new delivery. Never modify historical evidence.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';

const [repoArg,outputArg]=process.argv.slice(2);
if(!repoArg||!outputArg)throw new Error('Usage: atualizar_apresentacao.mjs <repo> <new-pptx-path>');
const repo=path.resolve(repoArg),output=path.resolve(outputArg);
const modules=process.env.RUNTIME_NODE_MODULES,skill=process.env.PRESENTATIONS_SKILL_DIR,python=process.env.RUNTIME_PYTHON;
if(!modules||!skill||!python)throw new Error('Set configured bundled runtime paths.');
const {PresentationFile,FileBlob}=await import(pathToFileURL(path.join(modules,'@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const delivery=path.join(repo,'entregas/2026-10-30-entrega-04-correcao-parecer');
const source=path.join(repo,'entregas/2026-10-27-entrega-04-java-final/Apresentacao-Entrega04-final.pptx');
const sha=async p=>crypto.createHash('sha256').update(await fs.readFile(p)).digest('hex');
const sourceHash=await sha(source);
if(sourceHash!=='71be8450168428ef77c447068c0b22e21bd51eeaec329194b0a96aefcbe77f33')throw new Error('Unexpected historical source');
if(await sha(path.join(delivery,'TCC-Entrega04-correcoes.pdf'))!=='ba2ff74ba5e2f85b1662b85c26723b539b99f027a9d0da6d3b16efbe64273463')throw new Error('Expected reviewed TCC revision');
const data=path.join(repo,'implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1');
const groups=JSON.parse(await fs.readFile(path.join(data,'group-summary.json'),'utf8'));
const catalog=JSON.parse(await fs.readFile(path.join(data,'catalog.json'),'utf8'));
const exploration=JSON.parse(await fs.readFile(path.join(delivery,'recuperacao-exploratoria.json'),'utf8'));
if(catalog.planned_runs!==65||catalog.complete_original_evidence!==64||catalog.partial_commit_timing!==1)throw new Error('Campaign classification changed');
if(exploration.original_observed!==1||exploration.exploratory_observed!==5)throw new Error('Unexpected sensitivity');
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const before=(await p.inspect({select:'$.slides[*]',include:['id','index','title','layout','elements.id','elements.kind','elements.text','elements.position','elements.style','notes.text']})).records;
if(before.length!==10)throw new Error('Expected ten-slide reference');
const originals=before.map(r=>p.resolve(r.id));
const font='Arial',navy='#172B4D',blue='#2454BF',green='#12877C';
while(p.slides.items.length<17){const slide=p.slides.add();slide.background.fill='#FFFFFF';}
const slides=p.slides.items,notes=[];
const sourceRoot='implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1/';
const cited=(extra='')=>'TCC revisto em 30/10/2026, '+extra+' Dados originais em '+sourceRoot+'. Sem nova medição.';
function own(i,test){const hits=before[i].elements.filter(test);if(hits.length!==1)throw new Error('Ambiguous element on slide '+(i+1));return p.resolve(hits[0].id);}
function text(i,value,x,y,w,h,size=28,bold=false,color=navy){
 const s=slides[i].shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 s.text=value;s.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none'};return s;
}
function title(i,value){if(i<10)own(i,e=>e.kind==='textbox'&&e.position.top===52).text=value;else{text(i,value,70,52,1140,110,38,true);text(i,'Apoio '+(i-9),1090,655,130,30,18,false,'#64748B');}}
function footer(i,value,top=585,size=23){text(i,value,72,top,1136,68,size,false,'#475569');}
function speak(i,value,sourceText=cited('Capítulos 3, 5 e 6.')){notes[i]={speech:value,sources:sourceText};slides[i].speakerNotes.textFrame.setText(value+'\n\nFontes: '+sourceText);}
function table(i,values,widths,{top=175,height=385,size=23}={}){
 const t=slides[i].tables.add({rows:values.length,columns:values[0].length,left:72,top,width:1136,height,columnWidths:widths,values});
 t.borders.assign({style:'solid',fill:'#CBD5E1',width:1});
 for(let r=0;r<values.length;r++){t.rows[r].height=height/values.length;for(let c=0;c<values[0].length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?navy:'#FFFFFF';cell.text.style={typeface:font,fontSize:size,color:r===0?'#FFFFFF':navy,bold:r===0,autoFit:'none'};
 }}return t;
}
function chart(i,categories,series,{left=80,width=1120,unit='ms',max=8,format='0.00'}={}){
 const digits=format==='0.0'?1:2;
 const ch=slides[i].charts.add('bar',{position:{left,top:185,width,height:355},categories,
  series:series.map(s=>({...s,values:s.values.map(v=>Number(v.toFixed(digits))),valuesFormatCode:format})),
  hasLegend:true,barOptions:{direction:'column',grouping:'clustered',gapWidth:70},
  legend:{position:'bottom',overlay:false,textStyle:{fontSize:21,fill:navy}},
  xAxis:{textStyle:{fontSize:21,fill:navy},line:{fill:'#CBD5E1',width:1}},
  yAxis:{min:0,max,title:unit,numberFormatCode:format,textStyle:{fontSize:20,fill:'#475569'},majorGridlines:{fill:'#E2E8F0',width:1}},
  dataLabels:{showValue:true,position:'outEnd',numberFormatCode:format,textStyle:{fontSize:22,fill:navy,bold:true}},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});
 applyPresentationChartFont(ch,{fontFamily:font});return ch;
}
const group=(profile,rate,variant)=>groups.find(g=>g.profile===profile&&g.rate===rate&&g.variant===variant);
const fmt=(v,d=2)=>v.toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d});
const pair=(rate,keys)=>['sync','async'].map((v,i)=>({name:i?'Assíncrona':'Síncrona',fill:i?green:blue,values:keys.map(k=>group('steady',rate,v).metrics[k].mean)}));

// Preserve all original native tables and layout positions in the ten core slides.
own(0,e=>e.kind==='textbox'&&e.position.top===430).text='Ilan Wendling Thoele\nOrientadora: Profa. Dra. Alessandra Bussador';
own(0,e=>e.kind==='textbox'&&e.position.top===590).text='Resultados de 27/10/2026 e revisão do parecer em 30/10/2026';
speak(0,'Comparei duas implementações Java para registrar auditoria. A pergunta é quais compromissos de desempenho e recuperação aparecem quando se confirma a gravação imediatamente ou se aceita o trabalho para gravar depois. A campanha inclui 64 coletas completas e uma parcial preservada.');
speak(1,'As duas variantes compartilham contrato, validação, hash e PostgreSQL. A síncrona confirma depois da transação. A assíncrona confirma publicação no Kafka e um consumidor grava depois. O piloto comparou cinquenta registros equivalentes por variante, sem substituir a campanha.');
own(2,e=>e.kind==='textbox'&&e.text.startsWith('65 UUIDs')).text='65 coletas em 13 condições, com cinco repetições por condição.';
speak(2,'Cada coleta é uma execução, não um evento. Fizemos cinco repetições por condição, com o mesmo conteúdo nos pares. O k6 gerou a carga e o analisador Java conciliou resposta, banco e marcos de transação. As 65 coletas incluem cargas constantes, rajada e paradas controladas. A análise é descritiva por coleta e par.');
const table4=own(3,e=>e.kind==='table');table4.cells.set(2,0,'p95 até concluir a gravação (ms)');
own(3,e=>e.kind==='textbox'&&e.position.top===585).text='Médias de cinco coletas. Cada p95 é calculado dentro de uma coleta.';
speak(3,'A 48 eventos por segundo, o p95 HTTP médio foi 2,60 milissegundos na assíncrona e 4,34 na síncrona. Até concluir a gravação, foram 5,83 e 3,92 milissegundos. O aceite mais rápido coexistiu com conclusão mais lenta. As duas atingiram a taxa oferecida nesse recorte, sem demonstrar capacidade máxima ou equivalência.',cited('Capítulo 5, Tabela 7 e group-summary.json, steady 48/s.'));
own(4,e=>e.kind==='table').cells.set(4,0,'Coletas por variante');
speak(4,'A 12 eventos por segundo, o caminho assíncrono consumiu aproximadamente duas vezes a CPU e quatro vezes a memória. Incluímos API e banco na síncrona, e também consumidor e Kafka na assíncrona. A topologia faz parte da comparação. CPU e memória não medem dinheiro ou esforço de manutenção.',cited('Capítulo 5, Tabela 11 e group-summary.json, steady 12/s.'));
own(5,e=>e.kind==='table').cells.set(0,0,'Totais das cinco coletas');
speak(5,'Com o banco parado, a síncrona teve 2.452 respostas 503. Um desses eventos terminou no banco apesar do erro. Na assíncrona, todos os envios foram aceitos, mas 14 terminaram na fila de falhas. Eles ficaram retidos para inspeção, sem gravação automática posterior. A resposta de aceite e o destino final precisam ser acompanhados separadamente.',cited('Capítulo 5, Tabela 10 e group-summary.json, postgres-stop.'));
const t7=own(6,e=>e.kind==='table');t7.cells.set(0,0,'Indicador nas cinco coletas');t7.cells.set(4,1,'5 de 5 coletas');
speak(6,'Com o consumidor parado, todos os 10.801 aceites medidos terminaram gravados, sem fila de falhas. O tempo de conclusão chegou à escala de dezenas de segundos. A retenção permitiu aceitar durante a parada, mas essa observação local não prova tolerância à perda do broker ou da máquina.',cited('Capítulo 5 e dados por coleta de consumer-stop.'));
const t8=own(7,e=>e.kind==='table');t8.cells.set(1,1,'Horário de uma gravação ausente');t8.cells.set(2,1,'Exclusão do par com evidência parcial');
own(7,e=>e.kind==='textbox'&&e.text.startsWith('A parada do banco')).text='A parada do banco era planejada. A ausência do tempo de conclusão foi imprevista.\nA revisão veio após 37 coletas, antes das 28 restantes. Sem estimar o instante ausente.';
speak(7,'A parada do banco fazia parte do teste. A falta do horário de uma gravação não era planejada. Preservamos a coleta e o veredito original de evidência incompleta. Uma revisão analítica manteve indicadores auditados e retirou o par afetado da comparação primária de conclusão, que ficou com quatro pares. Não repetimos a coleta nem estimamos o tempo ausente.',cited('Capítulo 3, revisão analítica, capítulo 5 e Apêndice A. Original instrument_valid=false preservado.'));
title(8,'Recuperação sustentada e leitura exploratória');
own(8,e=>e.kind==='textbox'&&e.text.startsWith('Critério:')).text='O critério original permanece em 1 de 5 no banco assíncrono.\nA leitura exploratória separou a DLQ da fila ativa e observou 5 de 5.\nOs 14 eventos terminais continuam sem gravação. Detalhes no apoio 2.';
speak(8,'O critério original de recuperação exige trinta segundos sustentados sob carga e conta destinos na fila de falhas como aceites sem gravação. Ele permanece atingido em um de cinco casos assíncronos com banco parado. Na leitura exploratória posterior, separar falha terminal de pendência ativa permitiu observar retorno operacional nos cinco casos. Isso não alterou o critério original nem gravou os 14 eventos terminais.',cited('Capítulo 5, recuperação original e subseção 5.7.5. recuperacao-exploratoria.json, 30/10/2026.'));
own(9,e=>e.kind==='textbox'&&e.position.top===615).text='Apoio descritivo local. Um computador, um broker e cinco repetições limitam a generalização.';
speak(9,'A síncrona favoreceu confirmação imediata de gravação e menor uso de recursos. A assíncrona favoreceu aceite rápido e retenção na parada do consumidor, com conclusão posterior e componentes adicionais. As expectativas tiveram apoio descritivo nesse recorte. Custos financeiros, manutenção e superioridade geral permanecem inconclusivos. As contribuições e os requisitos estão nos slides de apoio.');

title(10,'Requisitos esperados e resultados obtidos');
table(10,[['Requisitos','Esperado','Obtido','Situação'],
 ['RF01 a RF10, RF16 e RF17','Registrar e tratar confirmações e falhas','Núcleo executado. Testes têm limites','Atendidos no escopo'],
 ['RF11 e RNF08','Evidência temporal completa','64 completas e uma parcial. Quatro pares na conclusão afetada','Cobertura parcial'],
 ['RF12 a RF14','Executar carga, medir e comparar','Executor e relatórios implementados','Atendidos'],
 ['RF15','Envio interativo e formulário próprio','Swagger entregue. Formulário próprio não construído','Parcial'],
 ['RNF03, RNF04 e RNF09','Segurança, portabilidade e escala','Ambiente local. Sem ensaio externo ou horizontal','Limites de demonstração']
],[212,280,414,230],{height:405,size:21});
footer(10,'Síntese da matriz de 17 requisitos funcionais e 10 não funcionais do TCC.\nImplementação não significa prova exaustiva de todos os modos de falha.',595,22);
speak(10,'O núcleo e os instrumentos já existem. UC05 executa cenários por k6 e executor. UC06 consolida os indicadores por analisador e relatórios. A documentação deixou de chamá-los de planejados. Preservamos os limites: uma coleta tem cobertura temporal incompleta, o formulário próprio não foi construído e não demonstramos segurança de produção, portabilidade externa ou escala horizontal.',cited('Capítulo 4, requisitos e UC05/UC06. Capítulo 5, Tabela 6. Matriz integral de 27 requisitos.'));

title(11,'Recuperação operacional após separar a fila de falhas');
const cases=exploration.runs;
table(11,[['Indicador','1','2','3','4','5'],
 ['Eventos terminais na DLQ',...cases.map(r=>String(r.dlq_terminal))],
 ['Critério original observado',...cases.map(r=>r.original.observed?'Sim':'Não')],
 ['Leitura exploratória observada',...cases.map(r=>r.exploratory.observed?'Sim':'Não')],
 ['Confirmação exploratória (s)',...cases.map(r=>fmt(r.exploratory.timing.confirmed_after_restore_s))]
],[436,140,140,140,140,140],{height:345,size:24});
footer(11,'Análise exploratória pós-hoc, sem nova carga. Só a pendência muda.\nAs três janelas, vazão, erros, saúde, lag e entrada ativa permanecem exigidos.\nOs 14 eventos na DLQ continuam sem persistência.',550,22);
speak(11,'Reproduzimos o resultado original de um em cinco e então subtraímos da pendência somente eventos com confirmação de DLQ observada até o fim de cada janela. Não usamos a DLQ final como se ela já existisse antes. Os demais critérios ficaram iguais. Observamos a sequência operacional nos cinco casos, entre 37,78 e 38,77 segundos após a retomada. Esta é uma sensibilidade posterior, não reclassificação ou confirmação predeclarada.',cited('Capítulo 5, Tabela 13. RECUPERACAO-EXPLORATORIA.md e recuperacao-exploratoria.json.'));

title(12,'Contribuições e pontos fortes');
['Técnica: protótipo Java e instrumentos reutilizáveis de carga e conciliação.',
 'Metodológica: medidas separadas de aceite, conclusão e destino terminal.',
 'Prática: critérios de escolha ligados à confirmação, ao atraso e às falhas.',
 'Controles: protocolo prévio, conteúdo pareado e resultados desfavoráveis preservados.'
].forEach((value,n)=>text(12,value,72,185+n*95,1136,82,28));
footer(12,'A revisão analítica e a leitura exploratória estão identificadas como posteriores aos dados.');
speak(12,'Entreguei um protótipo e instrumentos que podem apoiar novas verificações. A contribuição metodológica é separar o que a API aceita, o que o banco grava e o que termina em falha retida. Os controles permitem rastrear as tabelas até a evidência e mantêm resultados desfavoráveis. Eles não eliminam o tamanho amostral reduzido ou a necessidade de replicação.',cited('Capítulo 5, Pontos fortes. Capítulo 6, Avaliação do sistema e Contribuições.'));

title(13,'Discussão com a literatura');
table(13,[['Estudo','Questão relacionada','Relação com este TCC'],
 ['Cabane e Farias (2024)','Recursos de topologias distintas','Memória adicional e definição do trabalho contado'],
 ['Kazanavičius e Mažeika (2023)','Escolha da comunicação','Requisitos e significado da confirmação'],
 ['Blinowski e colaboradores (2022)','Ambiente e dimensionamento','Distribuição não assegura ganho proporcional'],
 ['Helland (2007) e Laigner e colaboradores (2021)','Coordenação sem transação global','Idempotência e DLQ não garantem gravação'],
 ['Niedermaier e colaboradores (2019)','Observabilidade distribuída','Correlação detecta limites, mas não recupera tempo ausente']
],[338,342,456],{height:405,size:21});
footer(13,'Comparação de direções, mecanismos e limites. Valores absolutos de estudos distintos\nnão formam uma mesma amostra e não são comparados diretamente.',595,22);
speak(13,'A discussão relaciona os achados aos mecanismos estudados, sem comparar milissegundos de aplicações diferentes. Custos dependem de topologia e ambiente. Comunicação e efeito persistido têm garantias distintas. Observabilidade ajuda a detectar o que faltou, mas não recupera um instante não registrado.',cited('Capítulo 5, subseção Discussão com a literatura, e referências correspondentes. Cabane/Farias DOI 10.1016/j.future.2023.10.021; Kazanavičius/Mažeika DOI 10.31577/cai_2023_1_1; Blinowski DOI 10.1109/ACCESS.2022.3152803; Laigner DOI 10.14778/3484224.3484232; Niedermaier DOI 10.1007/978-3-030-33702-5_3; Helland CIDR 2007.'));

title(14,'Resposta HTTP e conclusão a 48 eventos por segundo');
chart(14,['p95 HTTP válido','p95 até concluir a gravação'],pair(48,['http_success_p95_ms','commit_p95_ms']),{unit:'ms',max:7.5});
footer(14,'Médias de cinco p95 por variante. As barras não representam eventos agrupados.\nA evidência descritiva não estabelece superioridade estatística ou capacidade máxima.');
speak(14,'Este gráfico mostra os mesmos números da tabela do slide quatro. Cada barra é a média de cinco percentis calculados por coleta. A síncrona confirma o efeito antes de responder. A assíncrona devolve o aceite antes da gravação, o que explica as direções diferentes.',cited('group-summary.json, steady 48/s; Capítulo 5, Tabela 7. Gráfico arredondado a duas casas, dados científicos preservados.'));

title(15,'CPU e memória do caminho completo a 12 eventos/s');
chart(15,['CPU média'],pair(12,['business_cpu_mean_percent']),{left:80,width:530,unit:'% de uma CPU lógica',max:21});
chart(15,['Memória média'],pair(12,['business_memory_mean_mib']),{left:670,width:530,unit:'MiB',max:1400,format:'0.0'});
footer(15,'Cinco médias por coleta. A soma inclui os componentes adicionais da assíncrona.\nGerador e observador ficam separados. CPU e memória não medem custo financeiro.');
speak(15,'Os gráficos repetem a tabela do slide cinco em escalas distintas. O primeiro mede percentual de uma CPU lógica e o segundo memória em MiB. A comparação é dos caminhos completos, não de um protocolo abstrato. A direção não mede dinheiro, manutenção ou eficiência de componentes parados.',cited('group-summary.json, steady 12/s; Capítulo 5, Tabela 11. CPU com duas casas e memória com uma casa no gráfico.'));

title(16,'Uso de IA, limites e revisão do autor');
['Claude e Codex apoiaram código, execução, análise e redação.',
 'Os instrumentos produziram medições reais. Dados e vereditos foram preservados.',
 'A revisão pessoal integral do autor ainda está pendente antes da entrega.',
 'Ambiente compartilhado, cinco repetições e broker único limitam a generalização.'
].forEach((value,n)=>text(16,value,72,185+n*95,1136,82,28));
footer(16,'A declaração registra o apoio efetivo e a responsabilidade do autor.\nEsta versão não declara aprovação institucional ou revisão pessoal já concluída.');
speak(16,'As ferramentas apoiaram mais do que gramática: também código, comandos da campanha, agregação e redação. As medidas vieram da execução dos instrumentos. O autor informou em 30 de outubro que ainda fará sua revisão pessoal integral antes da entrega. Não devo afirmar que ela ou a aprovação da orientadora já ocorreram.',cited('Declaração de uso de IA e Capítulo 6 do PDF corrigido. ATENDIMENTO-PARECER.md, item M4 e confirmação direta do autor.'));

const key=crypto.createHash('sha256').update(output).digest('hex').slice(0,12);
const build=path.join(repo,'implementacao-java/.runtime/apresentacao-parecer-2026-10-30','build-'+key);
await fs.mkdir(build,{recursive:true});await fs.mkdir(path.dirname(output),{recursive:true});
const candidate=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
const tables=[4,5,6,7,8,9,11,12,14],charts=[15,16];
const final=await finalizePresentation({workspaceDir:repo,candidatePath:candidate,finalPath:output,pythonExecutable:python,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tables.flatMap(n=>['--require-native-table-slide',String(n)])],
 explicitTotalSlideCount:17,requiredNativeTableOwnerSlides:tables,requiredNativeChartOwnerSlides:charts,
 materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'reference',families:['Arial'],referencePath:source,referenceSha256:sourceHash},verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation.json')});
const after=await PresentationFile.importPptx(await FileBlob.load(output));
const inspection=await after.inspect({select:'$.slides[*]',include:['id','index','title','layout','elements.id','elements.kind','elements.text','elements.position','elements.style','notes.text']});
await fs.writeFile(path.join(build,'inspection.ndjson'),inspection.ndjson);
for(let i=0;i<after.slides.items.length;i++){
 const png=await after.export({slide:after.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const timing=[15,25,30,30,25,35,25,40,40,35];
const guide='# Roteiro da apresentação corrigida\n\nOs dez primeiros slides têm roteiro sugerido de cinco minutos. Os sete slides seguintes são apoio para perguntas. Os tempos são estimativas de ensaio, não duração medida. A leitura das fontes não integra a fala. A revisão pessoal integral permanece pendente.\n\n'+notes.map((n,i)=>'## Slide '+(i+1)+(i<10?' ('+timing[i]+' s)':' (apoio)')+'\n\n'+n.speech+'\n\nFontes: '+n.sources+'\n').join('\n');
await fs.writeFile(path.join(build,'ROTEIRO-APRESENTACAO.md'),guide);
await fs.writeFile(path.join(build,'build-summary.json'),JSON.stringify({slides:17,core:10,support:7,suggestedSeconds:timing.reduce((a,b)=>a+b,0),tableOwners:tables,chartOwners:charts,sourceHash,sha256:final.finalSha256},null,2));
console.log(JSON.stringify({build,sha256:final.finalSha256,slides:17,layout:final.presentationLayout.exitCode,integrity:final.packageIntegrity.status,import:final.firstPartyImport.passed}));
