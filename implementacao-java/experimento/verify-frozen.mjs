// Read-only preflight: validates published summaries/configuration and unused planned output paths.
// The count of verified raw files is historical, recorded at freeze; raw files remain local.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const json=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const frozen=json('experimento/FROZEN-PROTOCOL.json');
if(frozen.schema_version===2){const {verifyReduced}=await import('./verify-reduced.mjs');verifyReduced(frozen);process.exit(0);}
const report=frozen.report,catalog=json(`${report}/catalog.json`);
assert.equal(frozen.status,'ready_for_definitive_runs');
for(const [key,file] of [['plan_sha256',`${report}/plan.csv`],['base_compose_sha256','docker-compose.yml'],['observer_compose_sha256','experimento/compose.yml'],['policy_sha256','experimento/calibration-policy.json']])assert.equal(sha(fs.readFileSync(file)),frozen[key],file);
const java='experimento/analyzer/src/main/java/br/com/ilan/tcc/experiment';
const files=['experimento/run.sh','experimento/load.js',...fs.readdirSync(java).filter(n=>n.endsWith('.java')).sort().map(n=>`${java}/${n}`)];
assert.equal(sha(Buffer.from(files.map(p=>`${sha(fs.readFileSync(p))}  ${p}\n`).join(''))),frozen.instrument_source_sha256);
const rows=fs.readFileSync(`${report}/plan.csv`,'utf8').trim().split('\n').slice(1).map(l=>{const [block,profile,variant,rate,run,dataset,vus]=l.split(',');return{block:Number(block),profile,variant,rate:Number(rate),run,dataset,vus:Number(vus)};});
assert.equal(rows.length,130);assert.equal(new Set(rows.map(r=>r.run)).size,130);
const counts=new Map(),pairs=new Map(),first=new Map();
for(const r of rows){
  assert.match(r.run,/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/);assert.match(r.dataset,/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/);
  assert.ok(!fs.existsSync(`.runtime/entrega04/${r.run}-${r.variant}`));
  const key=`${r.profile}/${r.rate}/${r.variant}`;counts.set(key,(counts.get(key)||0)+1);
  const p=`${r.block}/${r.profile}/${r.rate}`;if(!pairs.has(p))pairs.set(p,[]);pairs.get(p).push(r);
  assert.equal(r.vus,r.profile.includes('stop')?frozen.fault_vus:frozen.normal_vus);
}
assert.equal(counts.size,13);for(const n of counts.values())assert.equal(n,10);
for(let b=1;b<=10;b++)assert.equal(rows.filter(r=>r.block===b).length,13);
for(const pair of pairs.values()){
  if(pair[0].profile==='consumer-stop'){assert.equal(pair.length,1);assert.equal(pair[0].variant,'async');continue;}
  assert.equal(pair.length,2);assert.notEqual(pair[0].variant,pair[1].variant);assert.equal(pair[0].dataset,pair[1].dataset);
  const key=`${pair[0].profile}/${pair[0].rate}`;if(!first.has(key))first.set(key,{sync:0,async:0});first.get(key)[pair[0].variant]++;
}
for(const value of first.values())assert.deepEqual(value,{sync:5,async:5});
assert.equal(catalog.runs.length,20);assert.equal(catalog.raw_checksums_verified.length,20);
for(const run of catalog.runs){const file=`${report}/runs/${run.run_id}-${run.variant}.json`;assert.equal(sha(fs.readFileSync(file)),run.summary_sha256);const s=json(file);assert.equal(s.instrument_valid,true);assert.notEqual(s.kind,'definitive');}
console.log(JSON.stringify({reference:frozen.reference_rate,calibration_runs:catalog.runs.length,raw_files_verified_at_freeze:catalog.raw_checksums_verified.reduce((s,r)=>s+r.files_verified,0),planned_runs:rows.length,conditions:counts.size,paired_first_variant:'5 sync / 5 async in each paired condition',planned_output_folders_present:0,source_and_file_hashes:'match'},null,2));
