// Executes the real load.js body in a local VM; no HTTP requests are performed.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const code = fs.readFileSync(new URL('../load.js', import.meta.url), 'utf8')
  .replace(/^import .*;\r?\n/gm, '')
  .replace('export const options', 'const options')
  .replace('export default function ()', 'function invokeIteration()')
  .replaceAll('export function ', 'function ');
const phases = [
  {name:'warmup',analysis_phase:'warmup',rate:5,seconds:5,start_seconds:0,payload_offset:0},
  {name:'measurement',analysis_phase:'measurement',rate:5,seconds:10,start_seconds:5,payload_offset:25}
];
const cfg = {phases,run_id:'test-only',variant:'sync',scenario:'fixture',url:'http://never-called',
  preallocated_vus:1,max_vus:1,http_timeout_seconds:20};
let requests = [], records = [];
const exec = {scenario:{name:'warmup',iterationInTest:24,startTime:1000},test:{abort:msg=>{throw new Error(msg);}}};
const sandbox = {exec,Date,console:{log:s=>records.push(JSON.parse(s))},
  SharedArray:function (_, factory) {return factory();},
  open:path=>JSON.stringify(path.endsWith('config.json') ? cfg : Array.from({length:75},(_,i)=>({event_id:`event-${i}`}))),
  http:{post:(_url,body)=>{requests.push(JSON.parse(body));return {status:201,body:'{}',timings:{duration:1}};}}};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
vm.runInContext('invokeIteration()',sandbox);
assert.equal(requests[0].event_id,'event-24');
exec.scenario.iterationInTest=25;
vm.runInContext('invokeIteration()',sandbox);
assert.equal(requests.length,1,'warmup boundary must never consume measurement event-25');
assert.equal(records.at(-1).kind,'scheduler_excess_iteration');
exec.scenario.name='measurement';exec.scenario.iterationInTest=0;
vm.runInContext('invokeIteration()',sandbox);
assert.equal(requests[1].event_id,'event-25');
exec.scenario.iterationInTest=49;
vm.runInContext('invokeIteration()',sandbox);
assert.equal(requests[2].event_id,'event-74');
exec.scenario.iterationInTest=50;
vm.runInContext('invokeIteration()',sandbox);
assert.equal(requests.length,3,'extra iteration must not issue HTTP');
assert.equal(records.at(-1).scheduled_count,50);
console.log('5 load phase/boundary checks passed using real load.js and explicit HTTP doubles.');
