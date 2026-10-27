import http from 'k6/http';
import exec from 'k6/execution';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

// Presentation only. It does not change the frozen experimental workload.
const sent = new Counter('demo_sent');
const errors = new Counter('demo_errors');
const run = __ENV.RUN_ID;
const variant = __ENV.VARIANT;
const rate = Number(__ENV.DEMO_RATE || '5');
const seconds = Number(__ENV.DEMO_SECONDS || '20');
const target = __ENV.TARGET_URL;
const targets = { sync: 'http://sync-api:8080/audit', async: 'http://async-api:8081/audit' };

export const options = {
  tags: { run_id: run, variant },
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
  scenarios: {
    demo: { executor: 'constant-arrival-rate', rate, timeUnit: '1s', duration: `${seconds}s`,
      preAllocatedVUs: 8, maxVUs: 8, gracefulStop: '10s' },
  },
  thresholds: {
    'http_req_duration{phase:demo}': ['max>=0'],
    'http_req_failed{phase:demo}': ['rate==0'],
    'checks{phase:demo}': ['rate==1'],
    demo_sent: ['count>0'],
    demo_errors: ['count==0'],
    dropped_iterations: ['count==0'],
  },
};

export function setup() {
  if (!/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(run)) throw new Error('RUN_ID inválido');
  if (!targets[variant] || target !== targets[variant]) throw new Error('Alvo fora dos serviços locais da demonstração');
  if (!Number.isInteger(rate) || rate < 1 || rate > 10 || !Number.isInteger(seconds) || seconds < 1 || seconds > 30) {
    throw new Error('Limites da demonstração: taxa 1..10/s e duração 1..30s');
  }
  const health = http.get(target.replace('/audit', '/health'), { timeout: '10s', tags: { phase: 'readiness' } });
  if (health.status !== 200) throw new Error('API não está pronta; use a opção 1 do menu');
}

export default function () {
  const i = exec.scenario.iterationInTest;
  const prefix = run.replace(/-/g, '').slice(0, 20);
  const id = `${prefix.slice(0, 8)}-${prefix.slice(8, 12)}-${prefix.slice(12, 16)}-${prefix.slice(16, 20)}-${i.toString(16).padStart(12, '0')}`;
  const tags = { phase: 'demo', event_id: id };
  const body = JSON.stringify({ event_id: id, event_type: 'created', entity_type: 'demonstracao',
    entity_id: `K6-${i}`, actor_id: 'apresentacao-k6', source: `demo-k6-${run}`,
    occurred_at: new Date().toISOString(), payload: { value: i % 10 } });
  sent.add(1);
  const response = http.post(target, body, { headers: { 'Content-Type': 'application/json', 'X-Run-ID': run }, timeout: '10s', tags });
  let validBody = false;
  try {
    const result = response.json();
    validBody = result.event_id === id && (variant === 'sync'
      ? ['persisted', 'duplicate'].includes(result.status) : result.status === 'accepted');
  } catch (_) { /* Invalid JSON is a failed assertion, never success. */ }
  const ok = check(response, { 'HTTP, UUID e status correspondem ao contrato': r => r.status === (variant === 'sync' ? 201 : 202) && validBody }, { phase: 'demo' });
  errors.add(ok ? 0 : 1);
}

export function handleSummary(data) {
  const metric = name => data.metrics[name] ? data.metrics[name].values : {};
  const timings = metric('http_req_duration{phase:demo}');
  const summary = { kind: 'presentation_demo_not_definitive', run_id: run, variant, rate, seconds,
    sent: metric('demo_sent').count || 0, errors: metric('demo_errors').count || 0,
    dropped_iterations: metric('dropped_iterations').count || 0,
    http_duration_ms: timings, latency_scope: 'Somente HTTP dos eventos; exclui readiness. Não mede tempo até commit.' };
  const ms = value => typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(2)} ms` : 'sem dados';
  const text = [ '', 'RESUMO DA DEMONSTRAÇÃO (não é resultado definitivo)',
    `Variante: ${variant} | taxa programada: ${rate}/s | duração: ${seconds}s`,
    `Eventos enviados: ${summary.sent} | respostas inválidas: ${summary.errors} | iterações não iniciadas: ${summary.dropped_iterations}`,
    `HTTP médio: ${ms(timings.avg)} | mediana: ${ms(timings.med)} | p95: ${ms(timings['p(95)'])} | p99: ${ms(timings['p(99)'])}`,
    '201 confirma persistência; 202 confirma publicação no Kafka. Não compare ambos como se fossem tempo até gravação.', '' ].join('\n');
  return { '/output/resumo.json': JSON.stringify(summary, null, 2),
    '/output/k6-summary.json': JSON.stringify(data), stdout: text };
}
