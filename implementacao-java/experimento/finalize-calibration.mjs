import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {createReadStream} from 'node:fs';
import {createGunzip} from 'node:zlib';
import {createInterface} from 'node:readline';
const app=path.resolve(process.argv[2]),batch=process.argv[3],finalize=process.argv.includes('--finalize');
if(!/^[0-9a-f-]{36}$/.test(batch))throw new Error('batch UUID required');
const session=path.join(app,'.runtime/calibration-2026-10-26',batch);
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=async p=>JSON.parse(await fs.readFile(p,'utf8'));
const properties=t=>Object.fromEntries(t.split(/\r?\n/).filter(l=>l.includes('=')).map(l=>{let i=l.indexOf('=');return[l.slice(0,i),l.slice(i+1)];}));
const records=[];
for(const line of (await fs.readFile(path.join(session,'runs.csv'),'utf8')).trim().split(/\r?\n/).slice(1)) {
  const [stage,block,variant,rate,id,folder,exit]=line.split(',');
  const dir=path.join(app,'.runtime/entrega04',`${id}-${variant}`);
  const summary=await read(path.join(dir,'summary.json'));
  const manifestText=await fs.readFile(path.join(dir,'manifest.txt'),'utf8');
  const meta=properties(manifestText);
  const inventory=manifestText.split(/\r?\n/).filter(l=>l.startsWith('background_container=')).map(l=>l.slice('background_container='.length)).sort();
  delete meta.background_container;
  meta.running_container_inventory_count=inventory.length;
  meta.running_container_inventory_sha256=hash(Buffer.from(inventory.join('\n')+'\n'));
  let assessment=null;try{assessment=await read(path.join(dir,'calibration-assessment.json'));}catch{}
  const highCardinalityWarning=/higher than the suggested limit|high.cardinality/i.test(await fs.readFile(path.join(dir,'k6-console.txt'),'utf8'));
  records.push({stage,block:Number(block),variant,rate:Number(rate),id,dir,exit:Number(exit),summary,meta,assessment,highCardinalityWarning});
}
const confirmations=records.filter(r=>r.stage==='confirmation');
const explorations=records.filter(r=>r.stage==='exploration');
const controls=records.filter(r=>r.stage==='telemetry-control');
const recovery=records.filter(r=>r.stage==='recovery-validation');
const reasons=[];
const sessionMeta=properties(await fs.readFile(path.join(session,'manifest.txt'),'utf8'));
if(!sessionMeta.finished_utc)reasons.push('calibration session has not finished');
if(new Set(records.map(r=>r.id)).size!==records.length)reasons.push('duplicate run UUID in catalog');
if(confirmations.length!==2)reasons.push('two five-minute confirmations not yet collected');
if(controls.length!==8)reasons.push('eight telemetry-control runs not yet collected');
if(recovery.length!==2)reasons.push('two recovery validations not yet collected');
if(records.some(r=>r.exit!==0||!r.summary.instrument_valid))reasons.push('collection failed or invalid');
if(records.some(r=>r.meta.working_tree!=='clean'))reasons.push('calibration must use a clean checkout');
if(records.some(r=>r.meta.run_id!==r.id||r.summary.run_id!==r.id||r.meta.variant!==r.variant||r.summary.variant!==r.variant||Number(r.meta.rate)!==r.rate||Number(r.summary.rate)!==r.rate))reasons.push('catalog/manifest/summary identity mismatch');
for(const r of confirmations)if(!r.assessment?.reference_eligible||r.meta.warmup_seconds!=='60'||r.meta.measure_seconds!=='300')reasons.push(`confirmation not eligible: ${r.id}`);
if(confirmations.length===2&&new Set(confirmations.map(r=>r.variant)).size!==2)reasons.push('confirmation must include each variant once');
for(const r of recovery)if(!r.summary.instrumentation?.stable_recovery?.observed)reasons.push(`stable recovery not observed: ${r.id}`);
if(recovery.length===2&&new Set(recovery.map(r=>r.summary.profile)).size!==2)reasons.push('recovery validation must cover both failure profiles');
const overhead=[];
for(const variant of ['sync','async'])for(const block of [1,2]) {
  const pair=controls.filter(r=>r.variant===variant&&r.block===block);
  const full=pair.find(r=>r.meta.telemetry==='full'),control=pair.find(r=>r.meta.telemetry==='control');
  if(pair.length!==2||!full||!control)reasons.push(`incomplete telemetry control pair: ${variant} block ${block}`);
  if(!full||!control)continue;
  for(const r of pair)if(r.meta.warmup_seconds!=='60'||r.meta.measure_seconds!=='60'||r.rate!==full.rate)reasons.push(`telemetry control parameters mismatch: ${r.id}`);
  const metric=async r=>(await read(path.join(r.dir,'k6-summary.json'))).metrics['http_req_duration{phase:measure}'].values;
  const f=await metric(full),c=await metric(control);
  const delta=f['p(95)']-c['p(95)'];
  overhead.push({variant,block,full_run:full.id,control_run:control.id,full_p95_ms:f['p(95)'],control_p95_ms:c['p(95)'],delta_ms:delta,
    threshold_ms:Math.max(2,c['p(95)']*.25),above_screening_threshold:delta>Math.max(2,c['p(95)']*.25)});
}
for(const variant of ['sync','async'])if(overhead.filter(o=>o.variant===variant&&o.above_screening_threshold).length===2)reasons.push(`persistent telemetry effect requires investigation: ${variant}`);
const reference=confirmations[0]?.rate;
if(confirmations.length===2 && (confirmations[1].rate!==reference || reference%4!==0))reasons.push('confirmation reference mismatch');
if(reference&&controls.some(r=>r.rate!==reference))reasons.push('controls and confirmation must use the same reference');
const sourceHashes=new Set(records.map(r=>r.meta.instrument_source_sha256));
const imageHashes=new Set(records.map(r=>r.meta.analyzer_image_id));
const appHashes=new Set(records.map(r=>r.meta.application_images_sha256));
if(records.length&&(sourceHashes.size!==1||imageHashes.size!==1||appHashes.size!==1))reasons.push('instrument/image changes within calibration session');
if(records.some(r=>!/^sha256:[0-9a-f]{64}$/.test(r.meta.analyzer_image_id)||!['instrument_source_sha256','application_images_sha256'].every(k=>/^[0-9a-f]{64}$/.test(r.meta[k]))))reasons.push('missing or malformed source/image fingerprints');
const result={batch_id:batch,status:reasons.length?'not_ready':'ready_for_definitive_runs',reference_rate:reference??null,
  records:records.map(r=>({stage:r.stage,block:r.block,variant:r.variant,rate:r.rate,id:r.id,valid:r.summary.instrument_valid,eligible:r.assessment?.reference_eligible,reasons:r.assessment?.reasons})),overhead,reasons};
console.log(JSON.stringify(result,null,2));
if(!finalize)process.exit(0);
if(reasons.length)throw new Error('Do not freeze: '+reasons.join('; '));
const droppedByScenario={};
for(const r of explorations) {
  const counts={};const input=createInterface({input:createReadStream(path.join(r.dir,'k6.jsonl.gz')).pipe(createGunzip()),crlfDelay:Infinity});
  for await(const line of input)if(/"metric"\s*:\s*"dropped_iterations"/.test(line)) {
    const p=JSON.parse(line);if(p.type==='Point'){const name=p.data.tags?.scenario||'unattributed';counts[name]=(counts[name]||0)+p.data.value;}
  }
  droppedByScenario[r.id]=counts;
}
const out=path.join(app,'experimento/calibracao',`2026-10-26-${batch.slice(0,8)}`);
if(await fs.stat(out).then(()=>true,()=>false))throw new Error('Refusing existing report directory');
const frozenFile=path.join(app,'experimento/FROZEN-PROTOCOL.json');
if(await fs.stat(frozenFile).then(()=>true,()=>false))throw new Error('Refusing existing frozen protocol');
await fs.mkdir(path.join(out,'runs'),{recursive:true});
const checkResults=[];
for(const r of records) {
  const raw=await fs.readFile(path.join(r.dir,'SHA256SUMS'),'utf8');
  let verified=0;
  for(const line of raw.trim().split(/\r?\n/)) {
    const m=line.match(/^([0-9a-f]{64})\s+\*?(.+)$/);if(!m)throw new Error('invalid checksum line');
    const p=path.resolve(r.dir,m[2]);if(!p.startsWith(r.dir+path.sep))throw new Error('checksum path escape');
    if(hash(await fs.readFile(p))!==m[1])throw new Error('raw evidence changed: '+r.id+'/'+m[2]);verified++;
  }
  checkResults.push({id:r.id,files_verified:verified});
  await fs.copyFile(path.join(r.dir,'summary.json'),path.join(out,'runs',`${r.id}-${r.variant}.json`));
}
const policyBytes=await fs.readFile(path.join(session,'policy.json'));
if(hash(policyBytes)!==hash(await fs.readFile(path.join(app,'experimento/calibration-policy.json'))))throw new Error('policy changed after start');
await fs.copyFile(path.join(session,'policy.json'),path.join(out,'policy.json'));
const environment=await read(path.join(session,'environment.json')).catch(()=>({note:'Additional CPU inventory not captured; use raw manifests for Docker limits and versions.'}));
await fs.writeFile(path.join(out,'environment.json'),JSON.stringify(environment,null,2)+'\n');
const provenance=[];
for(const r of records)provenance.push({run_id:r.id,stage:r.stage,block:r.block,variant:r.variant,rate:r.rate,exit_code:r.exit,
  raw_path:path.relative(app,r.dir).replaceAll('\\','/'),manifest:r.meta,k6_high_cardinality_warning:r.highCardinalityWarning,assessment:r.assessment,assessment_sha256:r.assessment?hash(await fs.readFile(path.join(r.dir,'calibration-assessment.json'))):null,summary_sha256:hash(await fs.readFile(path.join(r.dir,'summary.json')))});
const discardedSessions=[];
for(const d of await fs.readdir(path.dirname(session),{withFileTypes:true}))if(d.isDirectory()&&d.name!==batch){
  const p=path.join(path.dirname(session),d.name,'runs.csv');
  try {const lines=(await fs.readFile(p,'utf8')).trim().split(/\r?\n/).slice(1);const failed=lines.filter(l=>l.split(',')[6]!=='0');if(failed.length)discardedSessions.push({batch_id:d.name,failed_runs:failed.map(l=>({run_id:l.split(',')[4],exit_code:Number(l.split(',')[6])})),reason:'preliminary observer reconnect/sampling-gap validation failed; session preserved, not counted in reference confirmation'});}catch{}
}
await fs.writeFile(path.join(out,'catalog.json'),JSON.stringify({...result,environment,generated_utc:new Date().toISOString(),code_commit:execFileSync('git',['rev-parse','HEAD'],{cwd:app,encoding:'utf8'}).trim(),discarded_sessions:discardedSessions,dropped_iterations_by_scenario:droppedByScenario,raw_checksums_verified:checkResults,runs:provenance},null,2)+'\n');
const faultVus=Math.max(128,12*(reference/4)+32);
const frozen={schema_version:1,status:result.status,client_date:'2026-10-26',reference_rate:reference,
  scope:'common stable local reference, not maximum capacity, calibration runs are not definitive repetitions',
  interactive_tcc_project_must_be_stopped:true,
  warmup_seconds:60,warmup_measurement_gap_seconds:12,measure_seconds:300,drain_seconds:90,repetitions_per_variant_condition:10,
  normal_vus:128,fault_vus:faultVus,fault_seconds:40,fault_offset_seconds:100,fault_rate:reference/4,
  generator_cpu_limit:2,generator_memory_mib:2048,observer_cpu_limit:.25,observer_memory_mib:256,
  generator_cpu_p95_percent_max:70,generator_memory_percent_max:75,observer_cpu_p95_percent_max:80,observer_memory_percent_max:85,
  observer_interval_ms:1000,resource_sampling:'Docker stats batches approximately every 3 seconds; batch start/end preserved',
  instrument_source_sha256:[...sourceHashes][0],analyzer_image_id:[...imageHashes][0],application_images_sha256:[...appHashes][0],
  policy_sha256:hash(policyBytes),base_compose_sha256:hash(await fs.readFile(path.join(app,'docker-compose.yml'))),observer_compose_sha256:hash(await fs.readFile(path.join(app,'experimento/compose.yml'))),calibration_batch_id:batch,confirmation_run_ids:confirmations.map(r=>r.id),
  recovery:'3 consecutive complete 10s active-input windows after restore, >=90% target unique commits, zero HTTP errors, bounded pending/lag and fresh healthy observation; detection includes the 30s confirmation interval',
  dlq_interpretation:'DLQ is terminal non-persistence, not missing evidence or automatic replay; operational recovery is not full persistence recovery',
  seed:20261026,report:path.relative(app,out).replaceAll('\\','/'),plan:'plan.csv'};
let seed=frozen.seed;const rand=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
let plan='block,profile,variant,rate,run_id,dataset_id,vus\n';
for(let block=1;block<=10;block++) {
  const conditions=[{id:0,p:'steady',r:reference/4},{id:1,p:'steady',r:reference/2},{id:2,p:'steady',r:reference*3/4},{id:3,p:'steady',r:reference},{id:4,p:'burst',r:reference},{id:5,p:'postgres-stop',r:reference/4},{id:6,p:'consumer-stop',r:reference/4}];
  for(let i=conditions.length-1;i>0;i--){const j=Math.floor(rand()*(i+1));[conditions[i],conditions[j]]=[conditions[j],conditions[i]];}
  for(const c of conditions) {
    const dataset=crypto.randomUUID(),variants=c.p==='consumer-stop'?['async']:(block+c.id)%2?['sync','async']:['async','sync'];
    for(const variant of variants)plan+=`${block},${c.p},${variant},${c.r},${crypto.randomUUID()},${dataset},${c.p.includes('stop')?faultVus:128}\n`;
  }
}
frozen.plan_sha256=hash(Buffer.from(plan));
await fs.writeFile(path.join(out,'plan.csv'),plan);
const fmt=x=>Number(x).toFixed(2).replace('.',',');
const lines=['# Calibração e instrumentação — 26/10/2026','',`Estado: **pronto para iniciar a campanha**, sem nenhuma repetição definitiva executada nesta sessão. Referência comum: **${reference} eventos/s**.`,
  '', `Sessão: ${batch}. Início UTC: ${sessionMeta.started_utc}; término UTC: ${sessionMeta.finished_utc}. Código medido: ${sessionMeta.commit}. As ${records.length} execuções desta sessão são calibração/validação, não repetições dos cenários finais.`,
  '', `Ambiente: ${environment.cpu_model||'modelo de CPU não capturado'}, ${environment.logical_cpus_visible_to_wsl||'quantidade não capturada'} CPUs lógicas visíveis no WSL. O inventário complementar está em [environment.json](environment.json); versões e limites efetivos também constam dos manifestos. Frequência dinâmica, temperatura e processos do Windows não foram controlados.`,
  '', '## Como foi escolhida a referência','',
  'A política foi registrada antes da exploração. Foram avaliadas taxas crescentes e escolhida uma candidata comum elegível nas duas variantes; o arredondamento para múltiplo de quatro permite níveis C2 exatos. A candidata foi confirmada em cada variante com 60 s de aquecimento e 300 s de medição. Isso não estima a capacidade máxima do sistema.',
  '', '| Etapa | Variante | Taxa/s | Eventos medidos | Salvos ao final | Elegível como referência |', '|---|---|---:|---:|---:|---|'];
for(const r of records.filter(r=>['exploration','confirmation'].includes(r.stage)))lines.push(`| ${r.stage} | ${r.variant} | ${r.rate} | ${r.summary.offered} | ${r.summary.stored_at_observation_end} | ${r.assessment?.reference_eligible?'sim':'não: '+r.assessment?.reasons.join(', ')} |`);
for(const r of explorations)if(r.summary.dropped_iterations_all_phases)lines.push('',`Na execução ${r.id}, as iterações não iniciadas pelo gerador se distribuíram por cenário: ${JSON.stringify(droppedByScenario[r.id])}. Elas não representam registros enviados e perdidos; todos os destinos devem ser conferidos separadamente. A rejeição como referência é conservadora e não estima sozinha a capacidade da API.`);
lines.push('', '## Controle de interferência dos instrumentos','',
  'Dois blocos pareados por variante, com a ordem controle/completo invertida. O controle preserva o logging do aplicativo e usa apenas resumo HTTP e verificação independente do banco; remove JSON por evento, observador e amostragem de recursos. O p95 abaixo usa o mesmo estimador nativo do k6 nos dois modos, não compara algoritmos diferentes de percentil.',
  '', '| Variante | Bloco | p95 controle (ms) | p95 completo (ms) | Diferença (ms) |', '|---|---:|---:|---:|---:|');
for(const o of overhead)lines.push(`| ${o.variant} | ${o.block} | ${fmt(o.control_p95_ms)} | ${fmt(o.full_p95_ms)} | ${fmt(o.delta_ms)} |`);
lines.push('', 'O critério de triagem exige investigação se a diferença exceder max(2 ms, 25% do p95 de controle) em ambos os blocos de uma variante. O resultado não demonstra overhead zero nem constitui teste estatístico de equivalência. As comparações definitivas medirão o protótipo instrumentado, com configuração igual entre repetições. O observador consulta SQL nas duas variantes e Kafka Admin apenas na assíncrona; os controles expõem parte desse efeito, mas não eliminam todo possível viés de instrumentação.',
  '', '## Recursos na confirmação de cinco minutos','', '| Variante | CPU p95 gerador (% da quota) | Memória máxima gerador (% limite) | CPU p95 observador (% quota) | Memória máxima observador (% limite) |', '|---|---:|---:|---:|---:|');
for(const r of confirmations){const i=r.summary.instrumentation;lines.push(`| ${r.variant} | ${fmt(i.generator.cpu_p95_percent_of_limit)} | ${fmt(i.generator.memory_max_percent_of_limit)} | ${fmt(i.observer.cpu_p95_percent_of_limit)} | ${fmt(i.observer.memory_max_percent_of_limit)} |`);}
if(records.some(r=>r.highCardinalityWarning))lines.push('', 'O k6 emitiu alerta de alta cardinalidade pelas tags de correlação por evento. O alerta e seu vínculo com os UUIDs constam dos consoles brutos e do catálogo; não foram ocultados. A folga da tabela é a observada com essa instrumentação. Não extrapolar para cargas/durações maiores: a campanha deve parar para investigação se gerador ou observador ultrapassarem as margens congeladas. Referência técnica: [tags do k6](https://grafana.com/docs/k6/latest/using-k6/tags-and-groups/).');
lines.push('', 'O gerador dispõe de 2 CPUs e 2 GiB; o observador, 0,25 CPU e 256 MiB. A CPU Docker é normalizada pela quota atribuída. A memória do CLI exclui cache conforme a documentação Docker; não é consumo global da máquina. O ambiente observado deve ser preservado nas repetições.',
  '', 'O isolamento dos dados é lógico: a tabela experimental é reinicializada e cada execução recebe tópicos e grupo novos. O broker e os volumes permanecem, com tópicos anteriores preservados. Isso não equivale a limpar caches, reinicializar a máquina ou eliminar todos os efeitos do histórico; a ordem contrabalançada e o aquecimento mitigam, mas não anulam essa limitação. Nesta versão do CLI, o contêiner parado apareceu com CPU 0 e memória 0B/0B; essas amostras brutas são preservadas. As médias dos cenários de falha misturam períodos ativos e indisponíveis: não representam eficiência, consumo condicionado ao processo ativo, energia ou custo global. A janela de parada deve acompanhar qualquer comparação de recursos.',
  '', 'Os limites foram escolhidos antes da exploração como margens de engenharia, não como constantes universais: 30% de reserva na quota de CPU do gerador, 25% na memória, pelo menos 95% de conclusões dentro da janela e 90% em cada janela de dez segundos. O limite de fila escala com 0,25 s de chegadas, com piso de cinco registros. A cauda não pode crescer mais que 0,01 evento/s. A comparação de controles é uma triagem de interferência, não teste de significância ou prova de equivalência.',
  '', 'Aceites sem commit e requisições HTTP em voo são medidas diferentes: na síncrona, o sucesso HTTP ocorre depois do commit, de modo que o primeiro indicador tende a zero mesmo quando há clientes aguardando. O lag Kafka é específico da assíncrona. Nenhum deles deve ser apresentado como uma fila física diretamente equivalente entre as arquiteturas.',
  '', '## Recuperação validada','', 'Ensaios de validação a 10 eventos/s, com 10 s de aquecimento, 90 s de medição e interrupção de 10 s. Não são as repetições definitivas de falha a 12/s por 40 s.');
for(const r of recovery){const stable=r.summary.instrumentation.stable_recovery;lines.push(`- ${r.summary.profile}: ${r.summary.offered} envios, ${r.summary.accepted} aceites, ${r.summary.stored_at_observation_end} salvos, ${r.summary.dlq_terminal} na DLQ terminal. Recuperação operacional sustentada confirmada ${fmt(stable.confirmed_after_restore_ms/1000)} s após o comando de retomada. UUID: ${r.id}.`);}
lines.push('', 'O primeiro commit, a persistência do backlog anterior e a recuperação sustentada são medidas distintas. O último critério exige três janelas completas consecutivas de dez segundos com entrada ativa, >=90% da taxa alvo em commits únicos, zero erros HTTP e fila/lag limitados com observação saudável e recente. O instante de confirmação inclui esses trinta segundos. Uma mensagem na DLQ impede alegar recuperação completa da persistência, mesmo com throughput novamente estável.',
  '', '## Plano definitivo ainda não executado','',
  `C1/C2: ${reference/4}, ${reference/2}, ${reference*3/4} e ${reference} eventos/s. C3: ${reference}→${reference*2}→${reference}. C4/C5: banco parado em ambas ou consumidor parado apenas na assíncrona, à taxa comum de ${reference/4}/s, falha de 40 s iniciada por volta dos 100 s de medição. Os instantes efetivos dos comandos e da parada são registrados. Essa carga de falha foi reduzida por desenho, para não confundir o acúmulo de requisições com falta de VUs; não muda entre variantes.`,
  '', `São 130 execuções em dez blocos, sem sobreposição, com ordem de condições embaralhada por semente 20261026 e primeira variante contrabalançada. UUIDs já foram gerados no plano. Aquecimento 60 s, intervalo até 12 s para concluí-lo, medição 300 s e observação posterior 90 s. VUs: 128 nas cargas normais e ${faultVus} nas falhas; o último valor reserva mais de 12 vezes a taxa de chegada para o timeout HTTP de 10 s. Mudança de ambiente ou parâmetros exige nova calibração.`,
  '', 'Os dados brutos estão em `.runtime/entrega04/`; os caminhos e hashes constam de `catalog.json`. Os resumos são publicados, sem duplicar todo o volume bruto. Checksums foram verificados antes de congelar. Os testes da instrumentação passaram no JDK 21. Não foram reescritas entregas históricas nem preenchidos capítulos 5 e 6 com estes ensaios.',
  '', 'A sessão preliminar 24cbb534-4a69-45ee-8b12-7f0da8082182 foi interrompida por uma lacuna de 7,03 s no observador durante a reconexão com PostgreSQL parado. A política não foi afrouxada. O observador passou a usar o IP experimental capturado antes da parada e loginTimeout de 2 s; os dados preliminares e a causa foram preservados. A confirmação usa somente a nova versão consistente dos instrumentos.',
  '', 'Fontes técnicas: [Kafka Admin](https://kafka.apache.org/39/javadoc/org/apache/kafka/clients/admin/Admin.html), [Docker stats](https://docs.docker.com/reference/cli/docker/container/stats/), [k6: alocação de VUs](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/arrival-rate-vu-allocation/).','');
await fs.writeFile(path.join(out,'README.md'),lines.join('\n'));
await fs.writeFile(path.join(out,'.gitattributes'),'*.json text eol=lf\n*.csv text eol=lf\n*.md text eol=lf\n');
await fs.writeFile(frozenFile,JSON.stringify(frozen,null,2)+'\n');
console.log('Frozen protocol: '+frozenFile+'; report: '+out);
