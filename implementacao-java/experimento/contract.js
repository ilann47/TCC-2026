import http from 'k6/http';
import { check } from 'k6';
export const options = { vus: 1, iterations: 1, thresholds: { checks: ['rate==1'] } };
export default function () {
  const p = __ENV.DATASET_ID.replace(/-/g,'').slice(0,20);
  const event = { event_id: `${p.slice(0,8)}-${p.slice(8,12)}-${p.slice(12,16)}-${p.slice(16,20)}-000000000000`,
    event_type:'created',entity_type:'experiment',entity_id:'E0',actor_id:'k6-experiment',
    source:`experiment-${__ENV.DATASET_ID}`,occurred_at:'2026-10-06T00:00:00.000Z',payload:{value:0} };
  const params={headers:{'Content-Type':'application/json','X-Run-ID':__ENV.RUN_ID},timeout:'10s'};
  const replay=http.post(__ENV.TARGET_URL,JSON.stringify(event),params);
  check(replay, { 'replay HTTP': r=>r.status===(__ENV.VARIANT==='sync'?201:202),
    'same UUID':r=>r.json('event_id')===event.event_id,
    'sync duplicate or async accepted':r=>r.json('status')===(__ENV.VARIANT==='sync'?'duplicate':'accepted') });
  const conflict=http.post(__ENV.TARGET_URL,JSON.stringify({...event,payload:{value:9}}),params);
  check(conflict, { 'conflict rejected synchronously or accepted for async DLQ': r=>r.status===(__ENV.VARIANT==='sync'?409:202) });
  console.log(`CONTRACT=${JSON.stringify({event_id:event.event_id,replay_status:replay.status,conflict_status:conflict.status})}`);
}
