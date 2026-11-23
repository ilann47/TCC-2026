import { COMMIT, DEFAULT_CONDITION, HTTP, choices, comparison, finite, pairedEffect } from "./analysis.js"

export const DEFENSE_SCENARIOS = [
  {
    id: DEFAULT_CONDITION,
    label: "Carga constante",
    rate: 48,
    profile: "steady",
    title: "A assíncrona respondeu antes, mas gravou depois.",
    context: "As mesmas repetições apontam em direções opostas: o aceite ficou mais rápido, mas a conclusão demorou mais.",
    decision: "Use a síncrona quando a resposta precisar confirmar a gravação. Considere a assíncrona quando bastar confirmar a publicação e acompanhar a conclusão depois.",
    limit: "Comparação descritiva a 48 eventos/s; não mede capacidade máxima nem estabelece superioridade geral.",
  },
  {
    id: "postgres-stop|12",
    label: "Banco parado",
    rate: 12,
    profile: "postgres-stop",
    title: "Aceitar o evento não garantiu gravá-lo.",
    context: "Na parcial, um registro síncrono persistiu apesar do 503, sem marca temporal de commit.",
    decision: "Monitore gravação e fila de falhas (DLQ). A volta do banco não reprocessa a fila automaticamente.",
  },
  {
    id: "consumer-stop|12",
    label: "Consumidor parado",
    rate: 12,
    profile: "consumer-stop",
    title: "Todos os aceites foram gravados ao fim da observação.",
    context: "A publicação continuou com o consumidor parado. A gravação ocorreu depois, com tempo de conclusão na escala de segundos.",
    decision: "Se o registro puder esperar, a fila permite aceitar enquanto o consumidor está parado; acompanhe a pendência até confirmar a gravação.",
    limit: "Só houve coletas assíncronas nesse cenário. O resultado não prova tolerância à perda do broker ou da máquina.",
  },
]

export const defenseScenario = (id) => DEFENSE_SCENARIOS.find((item) => item.id === id)

export const SCENARIO_METRICS = [
  { key: HTTP, label: "HTTP p95" },
  { key: COMMIT, label: "Commit p95" },
  { key: "http_error_percent", label: "Erros HTTP" },
  { key: "business_cpu_mean_percent", label: "CPU média" },
  { key: "business_memory_mean_mib", label: "Memória média" },
]

export function scenarioComparisons(report) {
  return choices(report.groups).map(({ value, label }) => ({
    id: value,
    label,
    metrics: SCENARIO_METRICS.map(({ key }) => {
      const model = comparison(report, value, key, "a1")
      return {
        unit: model.unit,
        values: ["sync", "async"].map((variant) => finite(model[variant]?.mean) ? model[variant].mean / model.scale : null),
        pairs: model.pairs.length,
      }
    }),
  }))
}

export function defenseOverview(report, id) {
  const scenario = defenseScenario(id) ?? DEFENSE_SCENARIOS[0]
  const groups = report.groups.filter((group) => group.profile === scenario.profile && group.rate === scenario.rate)
  const async = groups.find((group) => group.variant === "async")?.totals
  const sync = groups.find((group) => group.variant === "sync")?.totals
  const variants = ["sync", "async"]
  const metric = (label, unit, key, changeUnit, relative = false) => {
    const model = comparison(report, scenario.id, key, "a1")
    const effect = pairedEffect(model)
    return { label, unit, values: variants.map((variant) => model[variant]?.mean ?? null),
      change: relative ? effect.percent : effect.delta, changeUnit }
  }
  const lower = comparison(report, scenario.id, "throughput_lower", "a1")
  const upper = comparison(report, scenario.id, "throughput_upper", "a1")
  const interval = (min, max) => finite(min) && finite(max) ? [min, max] : null
  const totals = (label, key) => ({ label, unit: "eventos", values: [sync?.[key] ?? null, async?.[key] ?? null] })
  const statuses = (variant, status) => {
    const runs = report.runs.filter((run) => run.profile === scenario.profile && run.rate === scenario.rate && run.variant === variant)
    return runs.length ? runs.reduce((sum, run) => sum + (run.http_status_counts[status] ?? 0), 0) : null
  }
  const storedPercent = (t) => t?.offered > 0 ? 100 * t.stored_final / t.offered : null
  const rows = [
    { label: "Vazão concluída", unit: "eventos/s", values: variants.map((variant) => interval(lower[variant]?.mean, upper[variant]?.mean)),
      change: interval(pairedEffect(lower).delta, pairedEffect(upper).delta), changeUnit: "ev/s" },
    metric("Erros HTTP", "%", "http_error_percent", "p.p."),
    metric("CPU média", "% CPU lógica", "business_cpu_mean_percent", "%", true),
    metric("Memória média", "MiB", "business_memory_mean_mib", "%", true),
    totals("Enviados", "offered"),
    totals("Aceitos por HTTP", "accepted"),
    totals("Gravados ao fim", "stored_final"),
    { label: "Gravados / enviados", unit: "%", values: [storedPercent(sync), storedPercent(async)] },
    { label: "Respostas 503", unit: "eventos", values: variants.map((variant) => statuses(variant, "503")) },
    totals("Na DLQ", "dlq_terminal"),
  ]
  return { scenario, rows, destinations: scenario.profile === "steady" ? null : async ?? null, hasSync: Boolean(sync) }
}
