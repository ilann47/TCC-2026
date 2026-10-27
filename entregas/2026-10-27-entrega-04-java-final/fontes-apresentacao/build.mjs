// Updates a copy of the historical deck. Never edits historical files or campaign evidence.
// Requires the artifact runtime and skill paths supplied by load_workspace_dependencies.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {partialExplanation} from './explicacao-parcial.mjs';
const repo=path.resolve(process.argv[2]??'.');
const modules=process.env.RUNTIME_NODE_MODULES;
const skill=process.env.PRESENTATIONS_SKILL_DIR;
const python=process.env.RUNTIME_PYTHON;
if(!modules||!skill||!python) throw new Error('Set RUNTIME_NODE_MODULES, PRESENTATIONS_SKILL_DIR and RUNTIME_PYTHON from the configured bundled runtime.');
const {PresentationFile,FileBlob}=await import(pathToFileURL(path.join(modules,'@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {resolvePresentationFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const font=resolvePresentationFont({fontFamily:'Arial'});
const destDir=path.join(repo,'entregas/2026-10-27-entrega-04-java-final');
const tmp=path.join(repo,'implementacao-java/.runtime/entrega04-final-presentation');
const dest=process.argv[3]?path.resolve(process.argv[3]):path.join(destDir,'Apresentacao-Entrega04-final.pptx');
const source=path.join(repo,'entregas/2026-10-06-entrega-04-java-preparacao/Apresentacao-Entrega04-preparacao-v3.pptx');
const dataDir=path.join(repo,'implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1');
const sourceHash=crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex');
const groups=JSON.parse(await fs.readFile(path.join(dataDir,'group-summary.json'),'utf8'));
const catalog=JSON.parse(await fs.readFile(path.join(dataDir,'catalog.json'),'utf8'));
if(catalog.planned_runs!==65||catalog.complete_original_evidence!==64||catalog.partial_commit_timing!==1)throw new Error('Unexpected campaign classification');
const group=(profile,rate,variant)=>groups.find(g=>g.profile===profile&&g.rate===rate&&g.variant===variant);
const fmt=(v,d=2)=>v.toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d});
const integer=v=>fmt(v,0);
const S48=group('steady',48,'sync'), A48=group('steady',48,'async');
const S12=group('steady',12,'sync'), A12=group('steady',12,'async');
const SPG=group('postgres-stop',12,'sync'), APG=group('postgres-stop',12,'async'), AC=group('consumer-stop',12,'async');
const pres=await PresentationFile.importPptx(await FileBlob.load(source));
const inspection=await pres.inspect({select:'$.slides[*]',include:['id','index','layout','title','elements.id','elements.kind','elements.text','elements.position','elements.style']});
if(pres.slides.items.length!==10)throw new Error('Reference must contain ten slides');
const records=inspection.records;
const entry=i=>records.find(r=>r.index===i);
const slide=i=>pres.resolve(entry(i).id);
function shape(i,predicate){const e=entry(i).elements.find(predicate);if(!e)throw new Error('Reference element missing on slide '+(i+1));return pres.resolve(e.id);}
function title(i,value){shape(i,e=>e.kind==='textbox'&&e.position.top===52).text=value;}
function note(i,value){slide(i).speakerNotes.textFrame.setText(value);}
function text(i,value,x,y,w,h,size=28,bold=false,color='#172B4D'){
 const s=slide(i).shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 s.text=value;s.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none'};return s;
}
function body(i,values){
 const owned=entry(i).elements.filter(e=>e.kind==='textbox'&&e.position.top>=180&&e.position.top<650);
 owned.forEach(e=>pres.delete(e.id));
 values.forEach((value,n)=>text(i,value,72,195+n*103,1120,88,29));
}
function footer(i,value,size=24){
 const existing=entry(i).elements.find(e=>e.kind==='textbox'&&e.position.top>=550&&e.position.top<650);
 if(existing){const s=pres.resolve(existing.id);s.text=value;s.position={left:72,top:585,width:1136,height:65};s.text.style={typeface:font,fontSize:size,bold:false,color:'#172B4D',autoFit:'none'};}
 else text(i,value,72,585,1136,65,size);
}
function table(i,values,widths,top=180,height=390,size=25){
 const old=entry(i).elements.find(e=>e.kind==='table');
 let t;
 if(old){
   t=pres.resolve(old.id);
   const oldRows=old.text.split('\n').length,oldColumns=old.text.split('\n')[0].split('\t').length;
   if(values.length>oldRows)t.insertRows({index:oldRows,count:values.length-oldRows});
   else if(values.length<oldRows)t.deleteRows({index:values.length,count:oldRows-values.length});
   if(values[0].length>oldColumns)t.insertColumns({index:oldColumns,count:values[0].length-oldColumns});
   else if(values[0].length<oldColumns)t.deleteColumns({index:values[0].length,count:oldColumns-values[0].length});
   t.position={left:72,top,width:1136,height};
   widths.forEach((width,c)=>{t.columns.get(c).width=width;});
   values.forEach((row,r)=>row.forEach((value,c)=>t.cells.set(r,c,value)));
 }else t=slide(i).tables.add({rows:values.length,columns:values[0].length,left:72,top,width:1136,height,columnWidths:widths,values});
 t.borders.assign({style:'solid',fill:'#CBD5E1',width:1});
 for(let r=0;r<values.length;r++)t.rows[r].height=height/values.length;
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
   const cell=t.getCell(r,c);cell.fill=r===0?'#172B4D':'#FFFFFF';
   cell.text.style={typeface:font,fontSize:size,color:r===0?'#FFFFFF':'#172B4D',bold:r===0,autoFit:'none'};
 }
 return t;
}
const sourceNote='Fonte: campanha R2/A1 de 27/10/2026, implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/RESULTADOS.md e resultados-a1/. Documento consolidado no commit 771d7a621c31aaccda7359b8207979c4bc84f19d. ';
const notes=[];
function speak(i,value){notes[i]=value;note(i,value);}

shape(0,e=>e.kind==='textbox'&&e.position.top===590).text='Resultados da campanha R2/A1 em 27/10/2026';
speak(0,partialExplanation.openingNotes+sourceNote);

title(1,'Pergunta e modelo comum de auditoria');
shape(1,e=>e.kind==='textbox'&&e.position.top===470).text='Mesmo contrato, validação, hash e PostgreSQL.\nPiloto funcional: 50 registros equivalentes por variante.';
speak(1,'A pergunta permanece a mesma: quais trade-offs de desempenho e resiliência aparecem nas duas implementações? As variantes recebem o mesmo contrato, validam os mesmos campos, calculam o hash e usam o mesmo repositório PostgreSQL. A validação funcional comparou cinquenta registros equivalentes em cada variante, excluindo apenas o instante de inserção. Também conferiu reenvio idempotente e conflito de conteúdo. Isso verifica a função examinada, sem provar todo caso possível ou desempenho. A diferença experimental está no caminho: na síncrona, 201 vem depois da transação. Na assíncrona, 202 confirma publicação no Kafka e o consumidor grava em outra etapa. '+sourceNote+'Piloto: pilot-catalog.json e model-comparison.json na pasta R2.');

title(2,'Campanha executada e unidade de comparação');
body(2,['65 UUIDs em 13 condições, com cinco tentativas cada.','Constantes: 12, 24, 36 e 48/s. Rajada: 48, 96 e 48/s.','Falhas: PostgreSQL nas duas variantes e consumidor na assíncrona.','60 s de aquecimento, 180 s medidos e 90 s de observação posterior.']);
speak(2,'O gerador k6 exporta as amostras por evento e o analisador Java cruza os marcos e o banco. A escolha do k6 veio da integração com o protocolo, não de um benchmark que o declarasse superior ao JMeter. Antes da campanha, calibramos 48 eventos por segundo e aprovamos nove validações R2. Preservamos a R1 rejeitada, sem baixar a taxa. A campanha usa cinco blocos, trinta pares com o mesmo dataset e cinco casos adicionais de consumidor parado. As falhas solicitaram quarenta segundos, mas os manifestos mostram os tempos efetivos. Analisamos as execuções e diferenças pareadas. Milhares de eventos dentro de uma execução não viram milhares de repetições independentes. '+sourceNote);

title(3,'HTTP e conclusão a 48 eventos por segundo');
table(3,[['Indicador','Síncrona','Assíncrona'],['p95 HTTP válido (ms)',fmt(S48.metrics.http_success_p95_ms.mean),fmt(A48.metrics.http_success_p95_ms.mean)],['p95 envio até commit (ms)',fmt(S48.metrics.commit_p95_ms.mean),fmt(A48.metrics.commit_p95_ms.mean)],['Vazão concluída (eventos/s)',fmt(S48.metrics.throughput_lower.mean),fmt(A48.metrics.throughput_lower.mean)],['Erro HTTP medido (%)',fmt(S48.metrics.http_error_percent.mean),fmt(A48.metrics.http_error_percent.mean)]],[540,298,298]);
footer(3,'Médias entre cinco execuções. Latências: média dos p95 de cada execução.');
speak(3,'A 48 eventos por segundo, a assíncrona apresentou média dos p95 HTTP de 2,60 milissegundos, contra 4,34 na síncrona. Mas a conclusão da gravação teve a ordem inversa: 5,83 contra 3,92 milissegundos. O primeiro número mede o aceite ou retorno HTTP. O segundo começa no envio e termina no marco após o retorno da transação, conciliado com o banco. A diferença de significado explica por que uma resposta mais rápida não demonstra trabalho terminado antes. Os cinco pares mostraram essa direção nas condições sem falha. Ambas concluíram 48 eventos por segundo nesta carga, sem erro HTTP medido. Não estimamos capacidade máxima nem equivalência estatística. '+sourceNote+'group-summary.json: steady, rate=48.');

title(4,'Recursos do caminho completo a 12 eventos por segundo');
table(4,[['Indicador','Síncrona','Assíncrona'],['CPU média (% de uma CPU lógica)',fmt(S12.metrics.business_cpu_mean_percent.mean),fmt(A12.metrics.business_cpu_mean_percent.mean)],['Memória média (MiB)',fmt(S12.metrics.business_memory_mean_mib.mean,1),fmt(A12.metrics.business_memory_mean_mib.mean,1)],['Componentes no caminho','2','4'],['Execuções por variante','5','5']],[540,298,298],180,390,25);
footer(4,'API e banco na síncrona. API, consumidor, banco e Kafka na assíncrona.\nGerador e observador separados. Sem medição financeira ou de manutenção.',23);
speak(4,'Em carga constante de 12 eventos por segundo, a síncrona apresentou menor uso de CPU e memória. As médias por execução ficaram em 6,79 por cento de uma CPU lógica e 231 MiB, contra 15,36 por cento e 1.020,5 MiB da assíncrona. Somamos API e PostgreSQL na síncrona. Na assíncrona, somamos API, consumidor, PostgreSQL e Kafka nos mesmos instantes amostrados. O custo dos componentes adicionais pertence ao objeto comparado. Gerador e observador ficam separados. A direção se repetiu nos pares comparáveis, mas não podemos transformar esses valores em custo financeiro ou esforço de manutenção, que não medimos. Tampouco um componente parado durante falha demonstra eficiência. '+sourceNote+'group-summary.json: steady, rate=12.');

title(5,'PostgreSQL parado: aceites e destinos finais');
table(5,[['Totais das cinco tentativas','Síncrona','Assíncrona'],['Enviados',integer(SPG.totals.offered),integer(APG.totals.offered)],['Aceitos com 201 ou 202',integer(SPG.totals.accepted),integer(APG.totals.accepted)],['Persistidos ao fim',integer(SPG.totals.stored_final),integer(APG.totals.stored_final)],['DLQ terminal',integer(SPG.totals.dlq_terminal),integer(APG.totals.dlq_terminal)],['Respostas HTTP 503',integer(SPG.totals.offered-SPG.totals.accepted),'0']],[540,298,298],175,390,25);
footer(5,partialExplanation.postgresFooter,24);
speak(5,partialExplanation.postgresNotes+sourceNote+'group-summary.json: postgres-stop, rate=12.');

title(6,'Consumidor parado: retenção e recuperação');
table(6,[['Indicador nas cinco execuções','Resultado'],['Aceitos durante a medição',integer(AC.totals.accepted)],['Persistidos ao fim',integer(AC.totals.stored_final)],['DLQ terminal',integer(AC.totals.dlq_terminal)],['Recuperação sustentada',AC.stable_recovery_observed_n+' de 5 execuções']],[580,556],180,380,26);
footer(6,'Backlog integral: 12,55 a 24,16 s após comando de retomada.\nP95 de conclusão por execução: 46,95 a 57,80 s.',24);
speak(6,'A parada do consumidor foi diferente da parada do banco. Com o consumidor parado, o Kafka continuou recebendo os eventos e o banco não era a dependência indisponível. Todos os 10.801 aceites medidos acabaram persistidos e não houve DLQ. Em cada uma das cinco execuções, verificamos aceites ocorridos entre a confirmação da parada e o comando de retomada, com registros no banco e commits observados depois da retomada. O backlog anterior foi integralmente salvo entre 12,55 e 24,16 segundos após o comando. Os p95 de conclusão ficaram entre 46,95 e 57,80 segundos. Essa retenção confirma o comportamento local, mas não demonstra tolerância à perda física do broker ou da máquina. '+sourceNote+'per-run-details.json: consumer_pause.');

title(7,partialExplanation.title);
table(7,partialExplanation.rows,[380,470,286],180,365,24);
footer(7,partialExplanation.footer,24);
speak(7,partialExplanation.notes+sourceNote+'emenda-a1/README.md e strict-sensitivity.json.');

title(8,'Recuperação sustentada e limite do indicador');
body(8,[]);
table(8,[['Cenário','Critério atingido','Confirmação após retomada'],['Banco parado, síncrona',SPG.stable_recovery_observed_n+' de 5',fmt(SPG.metrics.stable_recovery_confirmed_s.mean)+' s em média'],['Consumidor parado, assíncrona',AC.stable_recovery_observed_n+' de 5',fmt(AC.metrics.stable_recovery_confirmed_s.mean)+' s em média'],['Banco parado, assíncrona',APG.stable_recovery_observed_n+' de 5',fmt(APG.metrics.stable_recovery_confirmed_s.mean)+' s no caso observado']],[500,230,406],180,330,24);
text(8,'Critério: três janelas completas de 10 s com entrada ativa.\nO cálculo conta DLQ como aceite sem commit. Três DLQ excedem o limite de dois.\nO retorno do serviço e o indicador composto exigem interpretações distintas.',72,540,1136,100,23);
speak(8,'O critério congelado exige três janelas completas de dez segundos, ainda sob entrada ativa, com taxa concluída suficiente, sem erro HTTP e com limites de aceites sem commit e observação saudável. As cinco síncronas e os cinco casos de consumidor parado atingiram esse critério. Apenas um caso assíncrono de banco parado atingiu. Isso exige cuidado: o cálculo inclui eventos já destinados à DLQ na contagem de aceites sem commit. O limite é dois, e três mensagens em DLQ já o ultrapassam. Portanto, nos primeiros quatro blocos, o indicador composto não se recupera, mesmo com retorno dos commits. Não mudamos a regra para aprová-los. O resultado não significa indisponibilidade contínua ou falha permanente do serviço. '+sourceNote+'Instrumentation.stableRecovery e tabela de recuperação do capítulo 5.');

title(9,'Conclusões e alcance das hipóteses');
body(9,['Síncrona: menor CPU/memória e confirmação de gravação no sucesso.','Assíncrona: menor latência de aceite e retenção na parada do consumidor.','Contrapartida: mais recursos e maior intervalo até a persistência.','Custo financeiro e manutenção permanecem inconclusivos.']);
text(9,'Cinco tentativas, um computador e um broker. Sem superioridade geral.',72,615,1136,35,22,false,'#475569');
speak(9,'As principais expectativas receberam apoio descritivo no recorte. A síncrona usou menos recursos em carga reduzida. A assíncrona teve menor p95 de aceite e reteve eventos na indisponibilidade do consumidor, com mais recursos e maior intervalo até a conclusão. Complexidade operacional aparece na topologia, mas custo financeiro e esforço de manutenção continuam inconclusivos, pois não foram medidos. A escolha depende do compromisso da aplicação. Confirmação imediata de gravação e aceite para conclusão posterior atendem necessidades diferentes. Cinco tentativas, um computador compartilhado, um broker, uma partição e a emenda pós-hoc limitam a generalização. Não afirmamos significância estatística nem uma arquitetura vencedora para qualquer sistema. '+sourceNote+'Capítulos 5 e 6 do PDF final.');

await fs.mkdir(tmp,{recursive:true});await fs.mkdir(path.dirname(dest),{recursive:true});
const buildKey=crypto.createHash('sha256').update(dest).digest('hex').slice(0,12);
const candidate=path.join(tmp,'candidate-'+buildKey+'.pptx');
await (await PresentationFile.exportPptx(pres)).save(candidate);
const tableOwners=[4,5,6,7,8,9];
const result=await finalizePresentation({workspaceDir:repo,candidatePath:candidate,finalPath:dest,
 pythonExecutable:python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],
 explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:tableOwners,
 fontPolicy:{basis:'reference',families:[font],referencePath:source,referenceSha256:sourceHash},verifyArtifactToolImport:true,
 receiptPath:path.join(tmp,'validation-'+buildKey+'.json')});
const rendered=await PresentationFile.importPptx(await FileBlob.load(dest));
for(let i=0;i<rendered.slides.items.length;i++){
 const p=await rendered.export({slide:rendered.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(tmp,`final-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await p.arrayBuffer()));
}
await fs.writeFile(path.join(tmp,'final-inspection.ndjson'),(await rendered.inspect({select:'$.slides[*]',include:['id','index','title','elements.id','elements.kind','elements.text','elements.position','elements.style','notes.text']})).ndjson);
const timing=[40,50,65,60,55,70,55,70,70,65];
const guide='# Roteiro de fala da apresentação final\n\nDez slides, duração estimada de 10 minutos. Os tempos são sugestões de ensaio, não duração medida.\n\n'+notes.map((n,i)=>'## Slide '+(i+1)+' ('+timing[i]+' s)\n\n'+n.trim()+'\n').join('\n');
await fs.writeFile(path.join(destDir,'ROTEIRO-APRESENTACAO.md'),guide,'utf8');
console.log(JSON.stringify({sha256:result.finalSha256,slides:rendered.slides.items.length,integrity:result.packageIntegrity.status,layout:result.presentationLayout.exitCode,import:result.firstPartyImport.passed}));
