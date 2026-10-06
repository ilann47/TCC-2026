// Packages derived summaries and a raw-evidence inventory, not raw payloads or credentials.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
const repo=path.resolve(process.argv[2]);
const output=path.resolve(process.argv[3]);
if(!output.startsWith(repo+path.sep))throw new Error('Output must be inside the repository');
const raw=path.join(repo,'implementacao-java/.runtime/entrega04');
const analyses=path.join(repo,'implementacao-java/.runtime/entrega04-reanalysis-v5');
const dirs=(await fs.readdir(raw,{withFileTypes:true})).filter(d=>d.isDirectory());
const knownFailures={
  '3d835b52-5990-457e-89e6-8aff51bf4c29':'Executor terminated before reading the console due to a file-creation race; no valid completed collection.',
  '07e1ba22-38cf-4f99-817b-b28d886d3c55':'Script was edited while Bash was executing it; evidence incomplete, not a definitive repetition.',
};
const digest=async p=>crypto.createHash('sha256').update(await fs.readFile(p)).digest('hex');
await fs.mkdir(path.join(output,'resumos'),{recursive:true});
const catalog=[];
for(const d of dirs.sort((a,b)=>a.name.localeCompare(b.name))){
  const folder=path.join(raw,d.name),id=d.name.slice(0,36);
  const item={run_id:id,raw_path:path.relative(repo,folder).replaceAll('\\','/'),classification:'incomplete_collection',issues:[],checksums:[]};
  try{
    const meta=Object.fromEntries((await fs.readFile(path.join(folder,'manifest.txt'),'utf8')).split(/\r?\n/).filter(l=>l.includes('=')).map(l=>{let i=l.indexOf('=');return[l.slice(0,i),l.slice(i+1)];}));
    item.metadata=meta;
    const summaryFile=path.join(analyses,d.name,'summary.json');
    const s=JSON.parse(await fs.readFile(summaryFile,'utf8'));
    item.summary=s; item.analysis_path=path.relative(repo,summaryFile).replaceAll('\\','/');
    item.classification=s.instrument_valid?'valid_functional_instrument_check_not_definitive':'invalid_instrument_collection';
    await fs.copyFile(summaryFile,path.join(output,'resumos',`${d.name}.json`));
    const sums=await fs.readFile(path.join(folder,'SHA256SUMS'),'utf8');
    for(const l of sums.split(/\r?\n/).filter(Boolean)){
      const m=l.match(/^([0-9a-f]{64})\s+\*?(.+)$/);if(!m)throw new Error('Malformed checksum line');
      const file=path.resolve(folder,m[2]);
      if(!file.startsWith(folder+path.sep))throw new Error('Checksum path escapes evidence');
      const actual=await digest(file);item.checksums.push({file:m[2],sha256:m[1],matches:actual===m[1]});
    }
    if(item.checksums.some(c=>!c.matches))item.issues.push('raw_checksum_mismatch');
    item.summary_sha256=await digest(summaryFile);
  }catch(e){item.issues.push(knownFailures[id]||String(e.message));}
  catalog.push(item);
}
let model=null;try{model=JSON.parse(await fs.readFile(path.join(raw,'model-comparison.json'),'utf8'));}catch{}
const report={status:'preparation_not_final_submission',generated_utc:new Date().toISOString(),
  definitive_repetitions:0,hardware:{cpu:'AMD Ryzen 7 5825U',physical_cores:8,logical_processors:16,windows_memory_gib:31.36},
  model_equivalence:model,analysis_version:'v5; independent Java reanalysis; original raw files and their original analyses preserved',
  analysis_runtime:'Windows Java 25.0.2; application and original analyzer containers use Java 21',
  analyzer_jar_sha256:await digest(path.join(analyses,'analyzer.jar')),
  pending:['Portal description and deadline','Common reference calibration','Validated generator/resource overhead and stable recovery criterion','Frozen protocol and 10 repetitions per variant/condition','Between-run statistical analysis','Final chapter 6 based only on chapter 5 results'],runs:catalog};
await fs.writeFile(path.join(output,'catalogo.json'),JSON.stringify(report,null,2)+'\n');
const files=await fs.readdir(path.join(output,'resumos'));
let sums=await digest(path.join(output,'catalogo.json'))+'  catalogo.json\n';
for(const f of files.sort())sums+=await digest(path.join(output,'resumos',f))+`  resumos/${f}\n`;
await fs.writeFile(path.join(output,'SHA256SUMS'),sums);
console.log(JSON.stringify({runs:catalog.length,valid:catalog.filter(r=>r.classification.startsWith('valid_')).length,
  invalid:catalog.filter(r=>r.classification==='invalid_instrument_collection').length,incomplete:catalog.filter(r=>r.classification==='incomplete_collection').length,
  checksum_mismatches:catalog.filter(r=>r.issues.includes('raw_checksum_mismatch')).length,model}));
