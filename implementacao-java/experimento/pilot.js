import http from 'k6/http';
import exec from 'k6/execution';
import { Counter } from 'k6/metrics';

// Pilot-only per-event tags permit correlation, but add high metric cardinality.
// Do not treat this instrumented run as a definitive performance result.
const sent = new Counter('pilot_sent');
const responded = new Counter('pilot_response');

const runId = __ENV.RUN_ID || '';
const variant = __ENV.VARIANT || '';
const targetUrl = __ENV.TARGET_URL || '';
const rate = Number(__ENV.RATE || '2');
const vus = Number(__ENV.VUS || '4');
const duration = __ENV.DURATION || '10s';

export const options = {
  tags: { run_id: runId, variant },
  scenarios: {
    pilot: {
      executor: 'constant-arrival-rate',
      rate,
      timeUnit: '1s',
      duration,
      preAllocatedVUs: vus,
      maxVUs: vus,
      gracefulStop: '10s',
    },
  },
};

export function setup() {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(runId)) {
    throw new Error('RUN_ID must be a UUID');
  }
  if (!['sync', 'async'].includes(variant)) throw new Error('VARIANT must be sync or async');
  if (!/^http:\/\/[a-z0-9-]+:[0-9]+\/audit$/.test(targetUrl)) {
    throw new Error('TARGET_URL must be an internal Compose /audit URL');
  }
  if (!Number.isInteger(rate) || rate < 1 || rate > 20 || !Number.isInteger(vus) || vus < 1 || vus > 50) {
    throw new Error('Pilot limits: RATE=1..20 and VUS=1..50');
  }
  if (!/^[1-9][0-9]?s$/.test(duration) || Number(duration.slice(0, -1)) > 60) {
    throw new Error('Pilot duration must be 1s..60s');
  }
  const urls = [targetUrl.replace('/audit', '/health')];
  if (variant === 'async') urls.push('http://sync-api:8080/health');
  for (const url of urls) {
    const readiness = http.get(url, { tags: { phase: 'readiness' }, timeout: '10s' });
    if (readiness.status !== 200) throw new Error(`Dependency not ready: ${url} (${readiness.status})`);
  }
}

function eventIdFor(iteration) {
  // First 80 bits identify this run; last 48 bits are the unique k6 iteration.
  const prefix = runId.replace(/-/g, '').slice(0, 20);
  const suffix = iteration.toString(16).padStart(12, '0');
  return `${prefix.slice(0, 8)}-${prefix.slice(8, 12)}-${prefix.slice(12, 16)}-${prefix.slice(16, 20)}-${suffix}`;
}

export default function () {
  const iteration = exec.scenario.iterationInTest;
  const eventId = eventIdFor(iteration);
  const occurredAt = new Date().toISOString();
  const tags = { run_id: runId, variant, event_id: eventId };
  const body = JSON.stringify({
    event_id: eventId,
    event_type: 'created',
    entity_type: 'pilot',
    entity_id: `E${iteration}`,
    actor_id: 'k6-pilot',
    source: `k6-pilot-${runId}`,
    occurred_at: occurredAt,
    payload: { value: iteration % 10 },
  });

  sent.add(1, { ...tags, iteration: String(iteration), occurred_at: occurredAt });
  const response = http.post(targetUrl, body, {
    headers: { 'Content-Type': 'application/json', 'X-Run-ID': runId },
    tags,
    timeout: '10s',
  });

  let idMatches = false;
  try {
    idMatches = response.json('event_id') === eventId;
  } catch (_) {
    // Missing or invalid response is recorded, never silently treated as success.
  }
  responded.add(1, {
    ...tags,
    http_status: String(response.status),
    id_matches: String(idMatches),
  });
}
