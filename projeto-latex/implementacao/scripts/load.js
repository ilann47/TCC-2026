import http from 'k6/http';
import exec from 'k6/execution';
import { SharedArray } from 'k6/data';

// k6 1.4.0. No remote imports: all inputs belong to this recorded run.
const config = JSON.parse(open('/input/config.json'));
const payloads = new SharedArray('payloads', () => JSON.parse(open('/input/payloads.json')));
const scenarios = {};
for (const phase of config.phases) {
  scenarios[phase.name] = {
    executor: 'constant-arrival-rate',
    rate: phase.rate,
    timeUnit: '1s',
    duration: `${phase.seconds}s`,
    startTime: `${phase.start_seconds}s`,
    preAllocatedVUs: config.preallocated_vus,
    maxVUs: config.max_vus,
    gracefulStop: `${config.http_timeout_seconds}s`,
    tags: { phase: phase.analysis_phase, run_id: config.run_id, variant: config.variant },
  };
}

export const options = {
  scenarios,
  maxRedirects: 0,
  // UUID is in console records, never a high-cardinality time-series tag.
  systemTags: ['scenario', 'status', 'method', 'name', 'expected_response'],
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(95)', 'p(99)'],
};

export function setup() {
  console.log(JSON.stringify({ kind: 'generator_started', run_id: config.run_id, wall_time_ms: Date.now() }));
}

export default function () {
  const phase = config.phases.find((item) => item.name === exec.scenario.name);
  // Preserve the predeclared equal volume even if the scheduler starts an extra
  // iteration at the duration boundary. Record it; never borrow the next phase's
  // payload, repeat a UUID or hide a dropped scheduled arrival.
  if (exec.scenario.iterationInTest >= phase.rate * phase.seconds) {
    console.log(JSON.stringify({ kind: 'scheduler_excess_iteration', run_id: config.run_id,
      phase: phase.analysis_phase, segment: phase.name, iteration_index: exec.scenario.iterationInTest,
      scheduled_count: phase.rate * phase.seconds, wall_time_ms: Date.now() }));
    return;
  }
  const index = phase.payload_offset + exec.scenario.iterationInTest;
  const payload = payloads[index];
  if (!payload) {
    exec.test.abort(`No recorded payload for index ${index}`);
    return;
  }
  const common = {
    run_id: config.run_id, event_id: payload.event_id, variant: config.variant,
    scenario: config.scenario, phase: phase.analysis_phase, segment: phase.name, payload_index: index,
  };
  const body = JSON.stringify(payload);
  const sentAt = Date.now();
  console.log(JSON.stringify({ ...common, kind: 'request_sent', sent_at_ms: sentAt,
    phase_start_ms: exec.scenario.startTime, phase_seconds: phase.seconds }));
  const response = http.post(config.url + '/audit', body, {
    headers: { 'Content-Type': 'application/json', 'X-Run-ID': config.run_id },
    timeout: `${config.http_timeout_seconds}s`,
    tags: { name: 'POST /audit' },
  });
  const finishedAt = Date.now();
  console.log(JSON.stringify({
    ...common, kind: 'http_response', sent_at_ms: sentAt, finished_at_ms: finishedAt,
    http_wall_duration_ms: finishedAt - sentAt,
    http_transport_duration_ms: response.timings.duration,
    http_status: response.status, error_code: response.error_code || null,
    response_body: response.body, timings_ms: response.timings,
  }));
}

export function handleSummary(data) {
  return { '/output/k6-summary.json': JSON.stringify(data, null, 2),
    stdout: JSON.stringify({ kind: 'generator_finished', run_id: config.run_id,
      dropped_iterations: data.metrics.dropped_iterations ? data.metrics.dropped_iterations.values.count : 0 }) + '\n' };
}
