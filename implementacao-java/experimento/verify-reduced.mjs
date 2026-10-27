// Read-only published-evidence verifier. Runtime folders may exist after the campaign starts.
import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const json=p=>JSON.parse(fs.readFileSync(p,'utf8'));
export function verifyAmendment(frozen) {
  const amendment=frozen.analytical_amendment;
  if(!amendment)return false;
  assert.equal(amendment.revision,'2026-10-27-a1-qualified-commit');
  assert.deepEqual(Object.keys(amendment.files).sort(),['adoption_audit','analysis','baseline_audit','original_controller','original_protocol','policy','review']);
  for(const item of Object.values(amendment.files)){
    assert.ok(!item.path.includes('..')&&!item.path.startsWith('/')&&!item.path.includes('\\'));
    assert.equal(sha(fs.readFileSync(item.path)),item.sha256,item.path);
  }
  const original=json(amendment.files.original_protocol.path);
  const current={...frozen};delete current.analytical_amendment;current.controller_sha256=original.controller_sha256;
  assert.deepEqual(current,original,'measurement protocol must remain identical');
  assert.equal(amendment.files.original_controller.sha256,original.controller_sha256);
  const policy=json(amendment.files.policy.path),audit=json(amendment.files.adoption_audit.path);
  assert.equal(policy.human_authorized,true);assert.equal(policy.no_imputation,true);assert.equal(policy.no_replacement_or_repeat,true);
  assert.equal(policy.revision,amendment.revision);assert.equal(policy.plan_sha256,frozen.plan_sha256);
  assert.equal(policy.reference_rate,48);assert.equal(policy.allowed_variant,'sync');assert.equal(policy.allowed_profile,'postgres-stop');
  assert.equal(policy.baseline_audit_sha256,amendment.files.baseline_audit.sha256);
  assert.deepEqual(audit.counts,{pilot:9,complete:36,partial:1,unstarted:28});
  assert.equal(audit.original_summary_changes,0);assert.equal(audit.raw_verdicts_rewritten,0);assert.equal(audit.new_measurements,0);
  assert.deepEqual(audit.implementation_hashes,{analysis:amendment.files.analysis.sha256,review:amendment.files.review.sha256,controller:frozen.controller_sha256,policy:amendment.files.policy.sha256});
  const partial=audit.assessments.filter(a=>a.classification==='partial_commit_timing');
  assert.equal(audit.assessments.length,37);assert.equal(partial.length,1);
  assert.equal(partial[0].run_id,policy.initial_partial_run_id);assert.equal(partial[0].original_instrument_valid,false);
  assert.equal(partial[0].eligibility.commit_latency_primary,false);assert.equal(partial[0].timing.imputed_timestamps,0);
  return true;
}
export function verifyReduced(frozen) {
  assert.equal(frozen.schema_version,2);assert.ok(['pilot_pending','ready_for_definitive_runs'].includes(frozen.status));
  const ready=frozen.status==='ready_for_definitive_runs';
  assert.equal(frozen.repetitions_per_variant_condition,5);assert.equal(frozen.measure_seconds,180);
  const report=frozen.report;
  for(const [key,file] of [['plan_sha256',`${report}/plan.csv`],['base_compose_sha256','docker-compose.yml'],['observer_compose_sha256','experimento/compose.yml'],['policy_sha256','experimento/calibration-policy.json'],['reduced_policy_sha256',`${report}/policy.json`],['controller_sha256','experimento/reduced_campaign.py'],['previous_protocol_sha256',frozen.previous_protocol]])assert.equal(sha(fs.readFileSync(file)),frozen[key],file);
  if(ready)assert.equal(sha(fs.readFileSync(`${report}/pilot-catalog.json`)),frozen.pilot_catalog_sha256);
  const java='experimento/analyzer/src/main/java/br/com/ilan/tcc/experiment';
  const files=['experimento/run.sh','experimento/load.js',...fs.readdirSync(java).filter(n=>n.endsWith('.java')).sort().map(n=>`${java}/${n}`)];
  assert.equal(sha(Buffer.from(files.map(p=>`${sha(fs.readFileSync(p))}  ${p}\n`).join(''))),frozen.instrument_source_sha256);
  const rows=fs.readFileSync(`${report}/plan.csv`,'utf8').trim().split(/\r?\n/).slice(1).map(l=>{const [block,profile,variant,rate,run,dataset,vus]=l.split(',');return{block:Number(block),profile,variant,rate:Number(rate),run,dataset,vus:Number(vus)};});
  assert.equal(rows.length,65);assert.equal(new Set(rows.map(r=>r.run)).size,65);
  const counts=new Map(),pairs=new Map(),first=new Map();let present=0;
  const allowed=new Set(['steady/12/sync','steady/12/async','steady/24/sync','steady/24/async','steady/36/sync','steady/36/async','steady/48/sync','steady/48/async','burst/48/sync','burst/48/async','postgres-stop/12/sync','postgres-stop/12/async','consumer-stop/12/async']);
  for(const r of rows){
    for(const id of [r.run,r.dataset])assert.match(id,/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/);
    const key=`${r.profile}/${r.rate}/${r.variant}`;assert.ok(allowed.has(key));counts.set(key,(counts.get(key)||0)+1);
    const p=`${r.block}/${r.profile}/${r.rate}`;if(!pairs.has(p))pairs.set(p,[]);pairs.get(p).push(r);
    assert.equal(r.vus,r.profile.includes('stop')?frozen.fault_vus:frozen.normal_vus);
    if(fs.existsSync(`.runtime/entrega04/${r.run}-${r.variant}`))present++;
  }
  assert.equal(counts.size,13);for(const n of counts.values())assert.equal(n,5);
  for(let b=1;b<=5;b++)assert.equal(rows.filter(r=>r.block===b).length,13);
  for(const pair of pairs.values()){
    if(pair[0].profile==='consumer-stop'){assert.equal(pair.length,1);assert.equal(pair[0].variant,'async');continue;}
    assert.equal(pair.length,2);assert.notEqual(pair[0].variant,pair[1].variant);assert.equal(pair[0].dataset,pair[1].dataset);
    const key=`${pair[0].profile}/${pair[0].rate}`;if(!first.has(key))first.set(key,{sync:0,async:0});first.get(key)[pair[0].variant]++;
  }
  for(const value of first.values())assert.deepEqual(Object.values(value).sort(),[2,3]);
  assert.equal([...first.values()].reduce((s,v)=>s+v.sync,0),15);
  if(process.argv.includes('--require-unused'))assert.equal(present,0,'planned run folder already exists');
  const pilot=ready?json(`${report}/pilot-catalog.json`):{ready:false,records:[]};
  if(ready){assert.equal(pilot.ready,true);assert.equal(pilot.records.length,9);}
  const pilotIds=new Set();
  for(const run of pilot.records){
    assert.ok(!pilotIds.has(run.run_id));pilotIds.add(run.run_id);
    const file=`${report}/pilot-runs/${run.run_id}-${run.variant}.json`;assert.equal(sha(fs.readFileSync(file)),run.summary_sha256);
    const s=json(file);assert.equal(s.instrument_valid,true);assert.notEqual(s.kind,'definitive');
  }
  for(const r of rows)assert.ok(!pilotIds.has(r.run));
  if(ready){assert.deepEqual(json(`${report}/model-comparison.json`),pilot.model);assert.equal(pilot.model.same_ids_fields_payload_hash,true);}
  const calibration=json(`${frozen.calibration_report}/catalog.json`);
  assert.equal(calibration.runs.length,20);
  for(const run of calibration.runs)assert.equal(sha(fs.readFileSync(`${frozen.calibration_report}/runs/${run.run_id}-${run.variant}.json`)),run.summary_sha256);
  const amended=verifyAmendment(frozen);
  console.log(JSON.stringify({revision:frozen.protocol_revision,status:frozen.status,original_measurement_protocol_ready:ready,definitive_execution_authorized:ready&&!amended,resumption_requires_controller_preflight:amended,analytical_amendment:amended?frozen.analytical_amendment.revision:null,reference:frozen.reference_rate,original_calibration_runs:20,reduced_validation_runs:pilot.records.length,planned_runs:65,conditions:13,repetitions:5,measure_seconds:180,paired_first_variant:'3/2 or 2/3 per condition; 15/15 overall',planned_output_folders_present:present,source_and_file_hashes:'match'},null,2));
}
