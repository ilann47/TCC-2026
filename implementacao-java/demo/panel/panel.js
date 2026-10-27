'use strict';
const $ = id => document.getElementById(id);
const states = {queued:'Preparando',running:'Em execução',stopping:'Interrompendo',passed:'Aprovado',failed:'Falhou',interrupted:'Interrompido'};
let token = '', selected = null, active = null, busy = false, checkBusy = false, lastHistory = '', connectionError = false;
const number = value => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('pt-BR', {maximumFractionDigits:0}) : '—';
const date = value => new Date(value).toLocaleString('pt-BR', {day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit'});
const label = variant => variant === 'sync' ? 'Síncrona' : 'Assíncrona';

async function api(path, body) {
  const options = body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify(body)};
  const response = await fetch(path, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'A operação não foi concluída.');
  return value;
}
function showError(message) { $('error').textContent = message; $('error').hidden = !message; }
function controls() {
  for (const id of ['run-sync','run-async','rate','seconds','check']) $(id).disabled = Boolean(active || busy || checkBusy);
}
function estimate() {
  $('estimate').textContent = `≈ ${number(Number($('rate').value) * Number($('seconds').value))} eventos programados`;
}
function chart(series) {
  const svg = $('chart'); svg.replaceChildren();
  const ns = 'http://www.w3.org/2000/svg';
  function element(tag, attributes) { const node = document.createElementNS(ns, tag); for (const [key,value] of Object.entries(attributes)) node.setAttribute(key,String(value)); svg.append(node); return node; }
  const maximum = Math.max(1,...series.map(point => point.avg_ms));
  for (let i=0;i<4;i++) {
    const y=15+i*35; element('line',{x1:42,x2:710,y1:y,y2:y,stroke:'#edf1f7'});
    const text = element('text',{x:0,y:y+4}); text.textContent = number(maximum*(1-i/3));
  }
  $('chart-empty').hidden = series.length > 0;
  if (!series.length) return;
  const coordinates = series.map((point,index) => [42+index/Math.max(1,series.length-1)*668,120-point.avg_ms/maximum*105]);
  element('polyline',{points:coordinates.map(point=>point.join(',')).join(' '),fill:'none',stroke:'#224fd4','stroke-width':2.5,'stroke-linejoin':'round'});
  for (const [x,y] of coordinates) element('circle',{cx:x,cy:y,r:2.5,fill:'#224fd4'});
  for (const index of [...new Set([0,series.length-1])]) {
    const text=element('text',{x:coordinates[index][0],y:145,'text-anchor':index?'end':'start'});
    text.textContent=new Date(series[index].time).toLocaleTimeString('pt-BR',{hour12:false});
  }
}
function detail(job) {
  const config = job.parameters, metrics = job.metrics || {};
  $('status').textContent = states[job.status] || job.status; $('status').className = 'status '+job.status;
  $('run-label').textContent = `k6 · ${config.rate} eventos/s · ${config.seconds} s`;
  $('run-title').textContent = `${label(config.variant)} · ${job.id.slice(0,8)}`;
  $('message').textContent = job.message;
  $('stop').hidden = active !== job.id || job.status === 'stopping';
  $('sent').textContent = number(metrics.sent); $('errors').textContent=number(metrics.errors); $('drops').textContent=number(metrics.dropped_iterations);
  $('p95').textContent = typeof metrics.http_p95_ms === 'number' ? metrics.http_p95_ms.toLocaleString('pt-BR',{maximumFractionDigits:1})+' ms' : '—';
  $('metric-note').textContent = metrics.provisional ? 'provisório · amostras observadas' : 'resumo final do teste';
  const ended = !['queued','running','stopping'].includes(job.status);
  const elapsed = Math.max(0,(Date.now()-new Date(job.started_at).getTime())/1000);
  // There is setup time before load: this is intentionally not a load-completion percentage.
  $('progress').style.width = ended ? '100%' : `${Math.min(95,elapsed/(config.seconds+30)*100)}%`;
  $('progress-label').textContent = ended ? `Encerrado em ${date(job.finished_at)} · executor ${job.exit_code ?? 'sem código'} · k6 ${job.k6_exit ?? 'sem código'}` : `${Math.floor(elapsed)} s desde o pedido · inclui verificação do ambiente e encerramento; a janela de carga é ${config.seconds} s.`;
  $('evidence').textContent = job.evidence ? `Evidências: ${job.evidence}` : 'Console preservado; a pasta k6 aparece após a verificação inicial.';
  $('console').textContent = job.console || 'Aguardando saída do executor…';
  chart(metrics.series || []);
}
function history(jobs) {
  const signature = JSON.stringify(jobs.map(job=>[job.id,job.status,selected]));
  if (signature === lastHistory) return; lastHistory=signature;
  $('history-count').textContent = `${jobs.length} teste${jobs.length===1?'':'s'}`;
  $('history-empty').hidden = jobs.length > 0;
  const rows=jobs.map(job=>{
    const row=document.createElement('tr'); row.className=selected===job.id?'selected':'';
    const values=[date(job.started_at),label(job.parameters.variant),`${job.parameters.rate}/s × ${job.parameters.seconds} s`,states[job.status]];
    for (const value of values) { const cell=document.createElement('td'); cell.textContent=value; row.append(cell); }
    const cell=document.createElement('td'),button=document.createElement('button'); button.type='button'; button.className='text-button'; button.textContent='Ver teste →'; button.setAttribute('aria-label',`Ver teste ${label(job.parameters.variant)} de ${date(job.started_at)}`);
    button.addEventListener('click',async()=>{selected=job.id;lastHistory='';await refresh();});cell.append(button);row.append(cell);return row;
  });
  $('history-body').replaceChildren(...rows);
}
async function refresh() {
  try {
    const state=await api('/api/state'); token=state.csrf_token; active=state.active_id;
    if (!selected) selected=active || state.jobs[0]?.id || null;
    if (state.check && !checkBusy) $('check-result').textContent=`Verificação de ${date(state.check.at)}: `+(state.check.ok?'✓ ':'Atenção: ')+state.check.message;
    history(state.jobs); controls();
    if (selected) detail(await api('/api/jobs/'+selected));
    if (connectionError) {showError('');connectionError=false;}
  } catch(error) { connectionError=true;showError('Painel sem conexão: '+error.message+' Mantenha o terminal do painel aberto.'); }
}
async function run(variant) {
  if (!$('test-form').reportValidity()) return;
  busy=true;controls();showError('');
  try {
    const job=await api('/api/run',{variant,rate:Number($('rate').value),seconds:Number($('seconds').value)});
    selected=job.id; active=job.id;lastHistory=''; await refresh();
  } catch(error) { showError(error.message); }
  finally {busy=false;controls();}
}
$('run-sync').addEventListener('click',()=>run('sync'));
$('run-async').addEventListener('click',()=>run('async'));
$('test-form').addEventListener('submit',event=>event.preventDefault());
for (const id of ['rate','seconds']) $(id).addEventListener('input',estimate);
$('stop').addEventListener('click',async()=>{if (!active || active!==selected) return;try{await api('/api/jobs/'+active+'/stop',{});await refresh();}catch(error){showError(error.message);}});
$('check').addEventListener('click',async()=>{checkBusy=true;controls();$('check-result').textContent='Verificando serviços, imagens e saúde das APIs…';try{const result=await api('/api/check',{});$('check-result').textContent=(result.ok?'✓ ':'Atenção: ')+result.message;}catch(error){showError(error.message);}finally{checkBusy=false;controls();}});
async function loop(){await refresh();setTimeout(loop,1200);} chart([]);loop();
