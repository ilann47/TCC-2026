import http from 'k6/http';
import exec from 'k6/execution';
import { Counter } from 'k6/metrics';

const sent = new Counter('experiment_sent');
const responded = new Counter('experiment_response');
const run = __ENV.RUN_ID;
const dataset = __ENV.DATASET_ID;
const variant = __ENV.VARIANT;
const rate = Number(__ENV.RATE);
const seconds = Number(__ENV.MEASURE_SECONDS);
const warm = Number(__ENV.WARMUP_SECONDS);
const vus = Number(__ENV.VUS);
const scenario = __ENV.PROFILE || 'steady';
const executor = (duration, startTime) => ({
  executor: 'constant-arrival-rate', rate, timeUnit: '1s', duration,
  startTime, preAllocatedVUs: vus, maxVUs: vus, gracefulStop: '12s',
});
const measurement = scenario === 'burst'
  ? { executor: 'ramping-arrival-rate', startRate: rate, timeUnit: '1s',
      startTime: `${warm + 12}s`, preAllocatedVUs: vus, maxVUs: vus,
      stages: [
        { target: rate, duration: `${Math.floor(seconds / 3)}s` },
        { target: rate * 2, duration: '1s' },
        { target: rate * 2, duration: `${Math.floor(seconds / 3) - 1}s` },
        { target: rate, duration: '1s' },
        { target: rate, duration: `${seconds - 2 * Math.floor(seconds / 3) - 1}s` },
      ], gracefulStop: '12s' }
  : executor(`${seconds}s`, `${warm + 12}s`);
export const options = {
  tags: { run_id: run, variant },
  scenarios: scenario === 'model'
    ? { measure: { executor: 'shared-iterations', vus: 1, iterations: 50, maxDuration: '60s', gracefulStop: '12s' } }
    : { warmup: executor(`${warm}s`, '0s'), measure: measurement },
};

export function setup() {
  const uuid = /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
  if (!uuid.test(run) || !uuid.test(dataset)) throw new Error('UUID required');
  if (!['sync', 'async'].includes(variant)) throw new Error('invalid variant');
  if (!Number.isInteger(rate) || rate < 1 || rate > 2000 || vus < 1 || vus > 2000
      || warm < 1 || seconds < 6) throw new Error('invalid load parameters');
  const r = http.get(__ENV.TARGET_URL.replace('/audit', '/health'), {
    timeout: '10s', tags: { phase: 'readiness' },
  });
  if (r.status !== 200) throw new Error(`API not ready: ${r.status}`);
}

export default function () {
  const phase = exec.scenario.name;
  const i = exec.scenario.iterationInTest + (phase === 'warmup' ? 1000000000 : 0);
  const prefix = dataset.replace(/-/g, '').slice(0, 20);
  const id = `${prefix.slice(0, 8)}-${prefix.slice(8, 12)}-${prefix.slice(12, 16)}-${prefix.slice(16, 20)}-${i.toString(16).padStart(12, '0')}`;
  // Pair content is deterministic, independent of variant, wall clock and run ID.
  const occurred = new Date(Date.UTC(2026, 9, 6) + i).toISOString();
  const tags = { event_id: id, phase, iteration: String(i), occurred_at: occurred };
  if (phase === 'measure' && exec.scenario.iterationInTest === 0) {
    console.log(`MEASUREMENT_START=${exec.scenario.startTime}`);
  }
  const body = JSON.stringify({ event_id: id, event_type: 'created', entity_type: 'experiment',
    entity_id: `E${i}`, actor_id: 'k6-experiment', source: `experiment-${dataset}`,
    occurred_at: occurred, payload: { value: i % 10 } });
  sent.add(1, tags);
  const response = http.post(__ENV.TARGET_URL, body, {
    headers: { 'Content-Type': 'application/json', 'X-Run-ID': run },
    timeout: '10s', tags,
  });
  let matches = false;
  try { matches = response.json('event_id') === id; } catch (_) { /* recorded below */ }
  responded.add(1, { ...tags, http_status: String(response.status), id_matches: String(matches) });
}
