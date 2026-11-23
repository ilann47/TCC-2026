import assert from "node:assert/strict"
import { execFileSync } from "node:child_process"
import test from "node:test"
import { fileURLToPath } from "node:url"
import { COMMIT, DEFAULT_CONDITION, HTTP, choices, comparison, pairedEffect } from "../src/lib/analysis.js"
import { DEFENSE_SCENARIOS, defenseOverview, scenarioComparisons } from "../src/lib/defense.js"
import { DEFENSE_STEPS, defenseNarrative } from "../src/lib/defense-guide.js"

const python = process.env.TCC_REPORT_PYTHON || (process.platform === "win32" ? "python" : "python3")
const script = fileURLToPath(new URL("../scripts/read_report.py", import.meta.url))
const report = JSON.parse(execFileSync(python, ["-B", "-X", "utf8", script], {
  encoding: "utf8", timeout: 70_000,
  env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
}))

test("load the verified campaign without changing its classification", () => {
  assert.equal(report.catalog.planned_runs, 65)
  assert.equal(report.catalog.complete_original_evidence, 64)
  assert.equal(report.catalog.partial_commit_timing, 1)
  assert.equal(report.verification.published_files_verified, 268)
  assert.equal(choices(report.groups).length, 7)
})

test("48/s shows two measures and the same five repetitions", () => {
  const http = comparison(report, DEFAULT_CONDITION, HTTP, "a1")
  const commit = comparison(report, DEFAULT_CONDITION, COMMIT, "a1")
  assert.deepEqual(http.pairs.map((row) => row.block), [1, 2, 3, 4, 5])
  assert.deepEqual(commit.pairs.map((row) => row.block), [1, 2, 3, 4, 5])
  assert.equal(http.sync.mean.toFixed(2), "4.34")
  assert.equal(http.async.mean.toFixed(2), "2.60")
  assert.equal(commit.sync.mean.toFixed(2), "3.92")
  assert.equal(commit.async.mean.toFixed(2), "5.83")
  assert.ok(http.pairs.every((row) => row.delta < 0))
  assert.ok(commit.pairs.every((row) => row.delta > 0))
})

test("A1 preserves HTTP but excludes both sides of R3 from commit", () => {
  const http = comparison(report, "postgres-stop|12", HTTP, "a1")
  const commit = comparison(report, "postgres-stop|12", COMMIT, "a1")
  assert.equal(http.pairs.length, 5)
  assert.deepEqual(commit.pairs.map((row) => row.block), [1, 2, 4, 5])
  assert.deepEqual([commit.rows[2].sync, commit.rows[2].async, commit.rows[2].delta], [null, null, null])
  assert.equal(commit.unit, "s")
  assert.equal(commit.scale, 1000)
})

test("strict sensitivity removes the affected pair in both charts", () => {
  for (const key of [HTTP, COMMIT]) {
    const result = comparison(report, "postgres-stop|12", key, "strict")
    assert.deepEqual(result.pairs.map((row) => row.block), [1, 2, 4, 5])
    assert.equal(result.rows[2].coverage, "Par fora da análise estrita")
  }
})

test("consumer stop shows unpaired async observations without inventing deltas", () => {
  for (const key of [HTTP, COMMIT]) {
    const result = comparison(report, "consumer-stop|12", key, "a1")
    assert.equal(result.pairs.length, 0)
    assert.ok(result.rows.every((row) => row.sync === null && Number.isFinite(row.async) && row.delta === null))
  }
})

test("exploratory recovery remains separate from the original and DLQ is not persisted", () => {
  const summary = report.groups.find((group) => group.profile === "postgres-stop" && group.variant === "async")
  assert.equal(summary.stable_recovery_observed_n, report.exploratory_recovery.original)
  assert.equal(report.exploratory_recovery.original, 1)
  assert.equal(report.exploratory_recovery.exploratory, 5)
  assert.equal(report.exploratory_recovery.runs.reduce((n, run) => n + run.dlq_terminal, 0), 14)
  assert.equal(summary.totals.stored_final + summary.totals.dlq_terminal, summary.totals.accepted)
})

test("defense shortcuts point to real campaign conditions, with steady 48/s first", () => {
  const conditions = new Set(choices(report.groups).map(({ value }) => value))
  assert.deepEqual(DEFENSE_SCENARIOS.map(({ id }) => id), ["steady|48", "postgres-stop|12", "consumer-stop|12"])
  assert.ok(DEFENSE_SCENARIOS.every(({ id }) => conditions.has(id)))
  const overview = defenseOverview(report, DEFAULT_CONDITION)
  assert.equal(overview.destinations, null)
  assert.equal(overview.hasSync, true)
  assert.deepEqual(overview.rows.find(({ label }) => label === "Gravados ao fim").values, [43204, 43205])
  assert.deepEqual(overview.rows.find(({ label }) => label === "Na DLQ").values, [0, 0])
})

test("defense bank-stop highlights async destinations without applying them to other scenarios", () => {
  const overview = defenseOverview(report, "postgres-stop|12")
  assert.deepEqual([overview.destinations.accepted, overview.destinations.stored_final, overview.destinations.dlq_terminal], [10804, 10790, 14])
  assert.deepEqual(overview.rows.find(({ label }) => label === "Na DLQ").values, [0, 14])
  const [syncThroughput] = overview.rows.find(({ label }) => label === "Vazão concluída").values
  assert.ok(syncThroughput[0] < syncThroughput[1], "partial timing retains throughput bounds")
})

test("defense consumer-stop leaves the synchronous side inapplicable", () => {
  const overview = defenseOverview(report, "consumer-stop|12")
  assert.equal(overview.hasSync, false)
  assert.ok(overview.rows.every(({ values }) => values[0] === null))
  assert.deepEqual([overview.destinations.accepted, overview.destinations.stored_final, overview.destinations.dlq_terminal], [10801, 10801, 0])
})

test("paired percentage uses the synchronous mean of the same eligible pairs", () => {
  const model = comparison(report, DEFAULT_CONDITION, HTTP, "a1")
  const effect = pairedEffect(model)
  assert.equal(effect.lower, 5)
  assert.ok(Math.abs(effect.percent - 100 * (model.async.mean / model.sync.mean - 1)) < 1e-9)
  const commit = pairedEffect(comparison(report, "postgres-stop|12", COMMIT, "a1"))
  assert.equal(commit.n, 4)
  assert.equal(pairedEffect(comparison(report, "consumer-stop|12", COMMIT, "a1")).percent, null)
  assert.equal(pairedEffect(comparison(report, DEFAULT_CONDITION, "http_error_percent", "a1")).percent, null)
})

test("scenario comparisons keep all seven recortes and don't fill missing data with zero", () => {
  const rows = scenarioComparisons(report)
  assert.deepEqual(rows.map(({ id }) => id), choices(report.groups).map(({ value }) => value))
  assert.equal(rows.find(({ id }) => id === "postgres-stop|12").metrics[1].pairs, 4)
  assert.ok(rows.find(({ id }) => id === "consumer-stop|12").metrics.every(({ values, pairs }) => values[0] === null && pairs === 0))
})

test("bank-stop separates HTTP status, acceptance and persistence", () => {
  const { rows } = defenseOverview(report, "postgres-stop|12")
  const values = (label) => rows.find((row) => row.label === label).values
  assert.deepEqual(values("Respostas 503"), [2452, 0])
  assert.deepEqual(values("Aceitos por HTTP"), [8351, 10804])
  assert.deepEqual(values("Gravados ao fim"), [8352, 10790])
  assert.deepEqual(values("Na DLQ"), [0, 14])
})

test("defense follows method, measured results, faults and scoped conclusions", () => {
  assert.deepEqual(DEFENSE_STEPS.map(({ id }) => id), ["method", "results", "failures", "conclusions"])
  assert.ok(DEFENSE_STEPS.every(({ label, purpose }) => label && purpose))
})

test("speaking guide points to the real HTTP and commit values, not a new pooled result", () => {
  const guide = defenseNarrative(report, DEFAULT_CONDITION)
  assert.match(guide.pointTo, /4,34 ms → 2,6 ms/)
  assert.match(guide.pointTo, /3,92 ms → 5,83 ms/)
  assert.match(guide.pointTo, /médias dos p95 por coleta/)
  assert.match(guide.say, /5 pares a 48 eventos\/s/)
  assert.match(guide.say, /202 assíncrono confirma o Kafka/)
  assert.match(guide.caution, /não prova/)
  assert.deepEqual(guide.metrics, ["Vazão concluída", "Erros HTTP", "CPU média", "Memória média"])
})

test("bank-stop explanation retains the partial and separates known DLQ from successful persistence", () => {
  const guide = defenseNarrative(report, "postgres-stop|12")
  assert.match(guide.pointTo, /10\.804 aceites = 10\.790 no banco \+ 14 na fila de falhas/)
  assert.match(guide.say, /4 pares, sem inventar esse tempo/)
  assert.match(guide.say, /gravado apesar do HTTP 503/)
  assert.match(guide.caution, /não prova ausência no banco/)
  assert.ok(!guide.metrics.includes("CPU média"), "stopped components are not used as an efficiency headline")
})

test("consumer-stop explanation uses observed final destinations without inventing a synchronous comparison", () => {
  const guide = defenseNarrative(report, "consumer-stop|12")
  assert.match(guide.pointTo, /10\.801 aceites e 10\.801 gravações finais/)
  assert.match(guide.say, /0 na DLQ/)
  assert.match(guide.say, /não existe contraparte síncrona/)
  assert.match(guide.caution, /não significa gravado imediatamente/)
  assert.ok(guide.metrics.every((name) => !["CPU média", "Memória média"].includes(name)))
})

test("speaking guide does not turn an unavailable summary into zero", () => {
  const copy = structuredClone(report)
  copy.groups.find((group) => group.profile === "steady" && group.rate === 48 && group.variant === "sync").metrics[COMMIT].mean = null
  const guide = defenseNarrative(copy, DEFAULT_CONDITION)
  assert.match(guide.pointTo, /Gravação: — ms/)
  assert.doesNotMatch(guide.pointTo, /Gravação: 0 ms/)
})
