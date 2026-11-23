export const HTTP = "http_success_p95_ms"
export const COMMIT = "commit_p95_ms"
export const DEFAULT_CONDITION = "steady|48"
export const BLOCKS = [1, 2, 3, 4, 5]

export const finite = (value) => typeof value === "number" && Number.isFinite(value)
export const format = (value, digits = 2) => finite(value)
  ? value.toLocaleString("pt-BR", { maximumFractionDigits: digits })
  : "—"
export const signed = (value, digits = 2) => finite(value)
  ? (value > 0 ? "+" : "") + format(value, digits)
  : "—"

export function pairedEffect(model) {
  const n = model.pairs.length
  if (!n) return { n, delta: null, percent: null, lower: 0, higher: 0 }
  const sum = (key) => model.pairs.reduce((total, pair) => total + pair[key], 0)
  const difference = sum("delta")
  const baseline = sum("sync")
  return {
    n, delta: difference / n / model.scale,
    percent: baseline > 0 ? 100 * difference / baseline : null,
    lower: model.pairs.filter((pair) => pair.delta < 0).length,
    higher: model.pairs.filter((pair) => pair.delta > 0).length,
  }
}

const profileOrder = ["steady", "burst", "postgres-stop", "consumer-stop"]
export function conditionLabel(profile, rate) {
  if (profile === "steady") return "Constante · " + rate + " eventos/s"
  if (profile === "burst") return "Rajada · 48 → 96 → 48 eventos/s"
  if (profile === "postgres-stop") return "Banco parado · " + rate + " eventos/s"
  return "Consumidor parado · " + rate + " eventos/s"
}

export function choices(groups) {
  return [...new Map(groups.map(({ profile, rate }) => [profile + "|" + rate, { profile, rate }])).entries()]
    .sort(([, a], [, b]) => profileOrder.indexOf(a.profile) - profileOrder.indexOf(b.profile) || a.rate - b.rate)
    .map(([value, { profile, rate }]) => ({ value, label: conditionLabel(profile, rate) }))
}

export function eligible(run, key, policy) {
  return Boolean(run)
    && !(policy === "strict" && run.profile === "postgres-stop" && run.block === 3)
    && !(key.startsWith("commit_") && !run.paired_commit_primary_included)
    && finite(run[key])
}

export function comparison(report, condition, key, policy) {
  const [profile, rateText] = condition.split("|")
  const rate = Number(rateText)
  const belongs = (item) => item.profile === profile && item.rate === rate
  const groups = (policy === "strict" ? report.strict_groups : report.groups).filter(belongs)
  const runs = report.runs.filter(belongs)
  const rows = BLOCKS.map((block) => {
    const sync = runs.find((run) => run.block === block && run.variant === "sync")
    const async = runs.find((run) => run.block === block && run.variant === "async")
    const s = eligible(sync, key, policy) ? sync[key] : null
    const a = eligible(async, key, policy) ? async[key] : null
    let delta = null
    if (s !== null && a !== null) {
      // For bounded throughput, retain the conservative difference bounds.
      delta = key === "throughput_lower" ? a - sync.throughput_upper
        : key === "throughput_upper" ? a - sync.throughput_lower : a - s
    }
    const coverage = !sync ? "Apenas assíncrona"
      : policy === "strict" && profile === "postgres-stop" && block === 3 ? "Par fora da análise estrita"
      : key.startsWith("commit_") && profile === "postgres-stop" && block === 3 ? "Par fora da conclusão"
      : delta !== null ? "Par elegível" : "Sem medição comparável"
    return { block, sync: s, async: a, delta, coverage }
  })
  const pairs = rows.filter((row) => finite(row.delta))
  const metric = report.metrics.find((item) => item.key === key)
  const seconds = metric.unit === "ms" && Math.max(0, ...rows.flatMap((row) => [row.sync, row.async]).filter(finite)) >= 1000
  return {
    key, rows, pairs, metric, unit: seconds ? "s" : metric.unit, scale: seconds ? 1000 : 1,
    sync: groups.find((group) => group.variant === "sync")?.metrics[key],
    async: groups.find((group) => group.variant === "async")?.metrics[key],
  }
}
