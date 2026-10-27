'use strict';
const $=id=>document.getElementById(id);
const states={queued:'Preparando',running:'Em execução',stopping:'Interrompendo',passed:'Aprovado',failed:'Falhou',interrupted:'Interrompido'};
let token='',selected=null,selectedPair=null,active=null,activePair=null,busy=false,checking=false,remoteChecking=false,connectionError=false;
let lastHistorySignature='',refreshGeneration=0;
const numeric=value=>typeof value==='number'&&Number.isFinite(value);
const fmt=(value,digits=0,unit='')=>numeric(value)?value.toLocaleString('pt-BR',{maximumFractionDigits:digits})+unit:'—';
const date=value=>new Date(value).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'});
const label=variant=>variant==='sync'?'Síncrona':'Assíncrona';
const ms=value=>fmt(value,2,' ms'),bytes=value=>numeric(value)?fmt(value/1024,1,' KiB'):'—';
const pick=(object,path)=>path.split('.').reduce((value,key)=>value?.[key],object);
async function api(path,body){
  const options=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify(body)};
  const response=await fetch(path,options),value=await response.json();
  if(!response.ok)throw new Error(value.error||'A operação não foi concluída.');return value;
}
function error(message){$('error').textContent=message;$('error').hidden=!message;}
function controls(){for(const id of ['run-both','run-sync','run-async','rate','seconds','check'])$(id).disabled=Boolean(active||activePair||busy||checking||remoteChecking);}
function estimate(){$('estimate').textContent='≈ '+fmt(Number($('rate').value)*Number($('seconds').value))+' eventos por variante';}
function dataList(id,values){$(id).replaceChildren(...values.map(([name,value])=>{const row=document.createElement('div'),term=document.createElement('dt'),description=document.createElement('dd');term.textContent=name;description.textContent=value;row.append(term,description);return row;}));}
function drawChart(id,groups,relative=false){
  const svg=$(id);svg.replaceChildren();const ns='http://www.w3.org/2000/svg';
  function element(tag,attrs,text){const node=document.createElementNS(ns,tag);for(const [key,value]of Object.entries(attrs))node.setAttribute(key,String(value));if(text!==undefined)node.textContent=text;svg.append(node);return node;}
  const values=groups.flatMap(group=>group.points.map(point=>point.avg_ms));
  const maximum=Math.max(1,...values),span=Math.max(1,...groups.flatMap(group=>group.points.map(point=>(new Date(point.time)-new Date(group.points[0].time))/1000)));
  for(let i=0;i<4;i++){const y=15+i*35;element('line',{x1:48,x2:710,y1:y,y2:y,stroke:'#edf1f7'});element('text',{x:0,y:y+4},fmt(maximum*(1-i/3),1));}
  if(!values.length){element('text',{x:360,y:77,'text-anchor':'middle'},'Aguardando amostras HTTP…');return;}
  for(const group of groups){
    if(!group.points.length)continue;const start=new Date(group.points[0].time).getTime();
    const coordinates=group.points.map(point=>[48+(new Date(point.time).getTime()-start)/1000/span*662,120-point.avg_ms/maximum*105]);
    element('polyline',{points:coordinates.map(point=>point.join(',')).join(' '),fill:'none',stroke:group.color,'stroke-width':2.5,'stroke-linejoin':'round'});
    for(const [x,y]of coordinates)element('circle',{cx:x,cy:y,r:2,fill:group.color});
  }
  const first=groups.find(group=>group.points.length).points;
  element('text',{x:48,y:146},relative?'0 s':new Date(first[0].time).toLocaleTimeString('pt-BR',{hour12:false}));
  element('text',{x:710,y:146,'text-anchor':'end'},relative?fmt(span,0,' s'):new Date(first.at(-1).time).toLocaleTimeString('pt-BR',{hour12:false}));
}
function detail(job){
  const config=job.parameters,m=job.metrics||{},lat=m.latency_ms||{},g=m.generator||{};
  $('status').textContent=states[job.status]||job.status;$('status').className='status '+job.status;
  $('run-label').textContent='k6 · '+config.rate+' eventos/s · '+config.seconds+' s'+(job.comparison_id?' · parte de sequência':'');
  $('run-title').textContent=label(config.variant)+' · '+job.id.slice(0,8);$('message').textContent=job.message;
  $('stop').hidden=!(active===job.id||(selectedPair&&selectedPair===activePair))||job.status==='stopping';
  $('stop').textContent=activePair?'Interromper sequência':'Interromper teste atual';
  $('sent').textContent=fmt(m.sent);$('errors').textContent=fmt(m.errors);$('drops').textContent=fmt(m.dropped_iterations);$('p95').textContent=ms(m.http_p95_ms);
  $('metric-note').textContent=m.provisional?'provisório · amostras':'resumo final do teste';
  $('send-rate').textContent=fmt(m.send_rate_window,2,'/s');$('lat-avg').textContent=ms(lat.avg);$('lat-med').textContent=ms(lat.med);$('lat-p99').textContent=ms(lat['p(99)']);
  const ended=!['queued','running','stopping'].includes(job.status),elapsed=Math.max(0,(Date.now()-new Date(job.started_at).getTime())/1000);
  $('progress').style.width=ended?'100%':Math.min(95,elapsed/(config.seconds+30)*100)+'%';
  $('progress-label').textContent=ended?'Encerrado em '+date(job.finished_at)+' · executor '+(job.exit_code??'sem código')+' · k6 '+(job.k6_exit??'sem código'):Math.floor(elapsed)+' s desde o pedido · inclui verificação do ambiente; carga programada de '+config.seconds+' s.';
  $('evidence').textContent=job.evidence?'Evidências: '+job.evidence:'Console preservado; pasta k6 disponível após a verificação inicial.';$('console').textContent=job.console||'Aguardando saída do executor…';
  drawChart('chart',[{points:m.series||[],color:config.variant==='sync'?'#224fd4':'#12877c'}]);$('chart-empty').hidden=true;
  const statuses=Object.entries(m.statuses||{}).sort();$('http-statuses').replaceChildren(...statuses.map(([code,count])=>{const node=document.createElement('span');node.className='chip';node.textContent=(code==='0'?'Sem resposta':code)+' · '+fmt(count);return node;}));
  if(!statuses.length)$('http-statuses').textContent='Sem amostras disponíveis';
  $('coverage').textContent=fmt(m.http_observed)+' requisições HTTP observadas · arquivo '+(m.raw_complete?'completo':'parcial/indisponível')+'. Resumo final e contagem de amostras têm fontes distintas.';
  dataList('generator-data',[
    ['Checks aprovados / falhos',fmt(m.checks_passed)+' / '+fmt(m.checks_failed)],['Respostas inválidas',fmt(m.invalid_pct,2,'%')],['Falha HTTP k6',fmt(m.http_failure_pct,2,'%')],
    ['VUs reservados / pico amostrado',fmt(g.vus_available)+' / '+fmt(g.vus_sampled_peak??m.vus_peak)],['Tráfego total, com prontidão',bytes(g.bytes_sent)+' / '+bytes(g.bytes_received)],['HTTP total do k6, com prontidão',fmt(g.http_total)]
  ]);
  dataList('timing-data',[
    ['HTTP mínimo / máximo',ms(lat.min)+' / '+ms(lat.max)],['HTTP média / mediana',ms(lat.avg)+' / '+ms(lat.med)],['HTTP p95 / p99',ms(lat['p(95)'])+' / '+ms(lat['p(99)'])],
    ...[['blocked','Bloqueio médio'],['connecting','Conexão média'],['sending','Envio médio'],['waiting','Espera pela resposta média'],['receiving','Recepção média']].map(([key,name])=>[name,ms(m.stages_ms?.[key])])
  ]);
}
const comparisonRows=[
  ['Carga e integridade'],['Taxa programada','parameters.rate','rate'],['Janela por variante','parameters.seconds','seconds'],['Eventos enviados','metrics.sent','count'],['HTTP observados no arquivo','metrics.http_observed','count'],['Envios ÷ janela programada','metrics.send_rate_window','rate'],['Respostas inválidas (HTTP/contrato)','metrics.errors','count'],['Respostas inválidas (%)','metrics.invalid_pct','pct'],['Iterações não iniciadas','metrics.dropped_iterations','count'],['Checks falhos','metrics.checks_failed','count'],
  ['Resposta HTTP dos eventos · não é conclusão assíncrona'],['Mínimo HTTP','metrics.latency_ms.min','ms'],['Média HTTP','metrics.latency_ms.avg','ms'],['Mediana HTTP','metrics.latency_ms.med','ms'],['p95 HTTP','metrics.latency_ms.p(95)','ms'],['p99 HTTP','metrics.latency_ms.p(99)','ms'],['Máximo HTTP','metrics.latency_ms.max','ms'],
  ['Gerador k6 · inclui prontidão'],['VUs reservados','metrics.generator.vus_available','count'],['Pico de VUs amostrado','metrics.generator.vus_sampled_peak','count'],['Bytes enviados pelo k6','metrics.generator.bytes_sent','bytes'],['Bytes recebidos pelo k6','metrics.generator.bytes_received','bytes']
];
function metric(value,type){return type==='ms'?ms(value):type==='rate'?fmt(value,2,'/s'):type==='seconds'?fmt(value,0,' s'):type==='pct'?fmt(value,2,'%'):type==='bytes'?bytes(value):fmt(value);}
function comparison(pair){
  $('comparison').hidden=false;$('pair-status').textContent=states[pair.status];$('pair-status').className='status '+pair.status;
  $('pair-label').textContent='Sequência '+pair.id.slice(0,8)+' · '+date(pair.started_at)+' · '+pair.parameters.rate+'/s por '+pair.parameters.seconds+' s em cada variante';$('pair-message').textContent=pair.message;
  const sync=pair.results.sync,async=pair.results.async;
  for(const [variant,job]of Object.entries(pair.results))$(variant+'-step').textContent=(variant==='sync'?'1':'2')+' · '+label(variant)+': '+(job?states[job.status]:'não iniciado');
  const rows=comparisonRows.map(([name,path,type])=>{
    const row=document.createElement('tr');if(!path){row.className='group';const cell=document.createElement('td');cell.colSpan=4;cell.textContent=name;row.append(cell);return row;}
    const s=pick(sync,path),a=pick(async,path),difference=numeric(s)&&numeric(a)?a-s:null;
    for(const value of [name,metric(s,type),metric(a,type),numeric(difference)?(difference>0?'+':'')+metric(difference,type):'—']){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}return row;
  });
  const statusRow=document.createElement('tr');for(const value of ['Resultado',sync?states[sync.status]:'Não iniciado',async?states[async.status]:'Não iniciado','—']){const cell=document.createElement('td');cell.textContent=value;statusRow.append(cell);}rows.unshift(statusRow);$('comparison-body').replaceChildren(...rows);
  drawChart('comparison-chart',[{points:sync?.metrics.series||[],color:'#224fd4'},{points:async?.metrics.series||[],color:'#12877c'}],true);
}
function resources(jobs,paired){
  const names=['sync-api','async-api','consumer','postgres','kafka'],head=document.createElement('tr');
  for(const name of ['Serviço',...(paired?['Síncrona · média / máximo','Assíncrona · média / máximo']:['CPU média / máximo','Memória média / máximo'])]){const cell=document.createElement('th');cell.textContent=name;head.append(cell);}$('resource-head').replaceChildren(head);
  const cellText=(job,service)=>{const row=job?.resources.rows.find(row=>row.service===service);return row?'CPU '+fmt(row.cpu_avg_pct,2,'%')+' / '+fmt(row.cpu_peak_pct,2,'%')+' · RAM '+fmt(row.memory_avg_mib,1)+' / '+fmt(row.memory_peak_mib,1,' MiB')+' · n='+row.samples:'Sem amostras';};
  $('resource-body').replaceChildren(...names.map(name=>{const row=document.createElement('tr');let values;
    if(paired)values=[name,cellText(jobs.sync,name),cellText(jobs.async,name)];else{const item=jobs[0]?.resources.rows.find(row=>row.service===name);values=[name,item?fmt(item.cpu_avg_pct,2,'%')+' / '+fmt(item.cpu_peak_pct,2,'%'):'—',item?fmt(item.memory_avg_mib,1)+' / '+fmt(item.memory_peak_mib,1,' MiB')+' · n='+item.samples:'—'];}
    for(const value of values){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}return row;
  }));
  const list=paired?[jobs.sync,jobs.async]:jobs;$('resource-scope').textContent=paired?'Mesmos cinco serviços · duas execuções':'Amostras do teste selecionado';
  $('resource-note').textContent=list.filter(Boolean).map(job=>label(job.parameters.variant)+': '+job.resources.snapshots+' amostras'+(job.resources.message?' · '+job.resources.message:'')).join(' | ')+' · Ausência de amostra não é consumo zero. Média simples de snapshots; não é CPU acumulada/energia. Tráfego e VUs acima pertencem ao gerador, não aos serviços.';
}
function history(state){
  const signature=JSON.stringify([selected,selectedPair,state.jobs.map(job=>[job.id,job.status]),(state.comparisons||[]).map(pair=>[pair.id,pair.status])]);
  if(signature===lastHistorySignature)return;lastHistorySignature=signature;
  $('history-count').textContent=state.jobs.length+' testes';$('history-empty').hidden=state.jobs.length>0;
  $('history-body').replaceChildren(...state.jobs.map(job=>{const row=document.createElement('tr');row.className=selected===job.id?'selected':'';
    for(const value of [date(job.started_at),label(job.parameters.variant)+(job.comparison_id?' · sequência':''),job.parameters.rate+'/s × '+job.parameters.seconds+' s',states[job.status]]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}
    const cell=document.createElement('td'),button=document.createElement('button');button.type='button';button.className='text-button';button.textContent='Ver teste →';button.setAttribute('aria-label','Ver teste '+job.id.slice(0,8));button.addEventListener('click',()=>{selected=job.id;selectedPair=null;refresh();});cell.append(button);row.append(cell);return row;
  }));
  const pairs=state.comparisons||[];$('pair-count').textContent=pairs.length+(pairs.length===1?' comparação':' comparações');$('pair-empty').hidden=pairs.length>0;
  $('pair-history').replaceChildren(...pairs.map(pair=>{const row=document.createElement('tr');row.className=selectedPair===pair.id?'selected':'';
    for(const value of [date(pair.started_at),pair.parameters.rate+'/s × '+pair.parameters.seconds+' s',states[pair.status]]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}
    const cell=document.createElement('td'),button=document.createElement('button');button.type='button';button.className='text-button';button.textContent='Comparar →';button.setAttribute('aria-label','Ver comparação '+pair.id.slice(0,8));button.addEventListener('click',()=>{selectedPair=pair.id;selected=null;refresh();});cell.append(button);row.append(cell);return row;
  }));
}
async function refresh(){
  const generation=++refreshGeneration;
  try{
    const state=await api('/api/state');if(generation!==refreshGeneration)return;token=state.csrf_token;active=state.active_id;activePair=state.active_comparison_id;remoteChecking=state.checking;
    if(!selected&&!selectedPair){const latest=state.jobs[0];selectedPair=activePair||latest?.comparison_id||null;if(!selectedPair)selected=active||latest?.id||null;}
    if(state.check&&!checking)$('check-result').textContent='Verificação de '+date(state.check.at)+': '+(state.check.ok?'✓ ':'Atenção: ')+state.check.message;
    if(selectedPair){const pair=await api('/api/comparisons/'+selectedPair);if(generation!==refreshGeneration)return;comparison(pair);resources(pair.results,true);const current=Object.values(pair.results).find(job=>job?.id===active)||pair.results.async||pair.results.sync;if(current)detail(current);if(activePair===pair.id){$('stop').hidden=pair.status==='stopping';$('stop').textContent='Interromper sequência';}}
    else{$('comparison').hidden=true;if(selected){const job=await api('/api/jobs/'+selected);if(generation!==refreshGeneration)return;detail(job);resources([job],false);}}
    history(state);controls();if(connectionError){error('');connectionError=false;}
  }catch(problem){connectionError=true;error('Painel sem conexão: '+problem.message+' Mantenha o processo do painel aberto.');}
}
async function run(variant){
  if(!$('test-form').reportValidity())return;busy=true;controls();error('');
  try{const config={rate:Number($('rate').value),seconds:Number($('seconds').value)};
    if(variant==='both'){const pair=await api('/api/compare',config);selectedPair=pair.id;selected=null;activePair=pair.id;}
    else{const job=await api('/api/run',{...config,variant});selected=job.id;selectedPair=null;active=job.id;}await refresh();
  }catch(problem){error(problem.message);}finally{busy=false;controls();}
}
$('run-both').addEventListener('click',()=>run('both'));$('run-sync').addEventListener('click',()=>run('sync'));$('run-async').addEventListener('click',()=>run('async'));
$('test-form').addEventListener('submit',event=>event.preventDefault());for(const id of ['rate','seconds'])$(id).addEventListener('input',estimate);
$('stop').addEventListener('click',async()=>{try{if(activePair)await api('/api/comparisons/'+activePair+'/stop',{});else if(active)await api('/api/jobs/'+active+'/stop',{});await refresh();}catch(problem){error(problem.message);}});
$('check').addEventListener('click',async()=>{checking=true;controls();$('check-result').textContent='Verificando serviços e imagem k6…';try{const result=await api('/api/check',{});$('check-result').textContent=(result.ok?'✓ ':'Atenção: ')+result.message;}catch(problem){error(problem.message);}finally{checking=false;controls();}});
async function loop(){await refresh();setTimeout(loop,1500);}drawChart('chart',[]);loop();
