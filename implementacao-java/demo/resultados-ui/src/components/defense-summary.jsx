import { Activity, ArrowDown, ArrowRight, Database, Layers, Target } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { finite, format, signed } from "@/lib/analysis"
import { DEFENSE_SCENARIOS, SCENARIO_METRICS, scenarioComparisons } from "@/lib/defense"
import { defenseNarrative } from "@/lib/defense-guide"

const icons = { steady: Activity, "postgres-stop": Database, "consumer-stop": Layers }
const formatValue = (value, unit) => {
  if (!Array.isArray(value)) return format(value, unit === "eventos" ? 0 : 2)
  const [min, max] = value
  return min === max ? format(min, 2) : `[${format(min, 5)}; ${format(max, 5)}]`
}
const formatChange = (value, unit) => {
  if (Array.isArray(value)) {
    const [min, max] = value
    return min === max ? signed(min, 3) : `[${signed(min, 5)}; ${signed(max, 5)}]`
  }
  return finite(value) ? signed(value, 1) + (unit === "%" ? "%" : " " + unit) : "—"
}

export function DefenseNavigation({ condition, onChange }) {
  return <nav aria-label="Cenários da defesa" className="flex flex-wrap items-center justify-between gap-2">
    <div className="grid w-full grid-cols-3 gap-1 rounded-xl border border-border bg-white p-1 sm:w-auto">
      {DEFENSE_SCENARIOS.map((item) => {
        const Icon = icons[item.profile]
        const active = condition === item.id
        return <Button key={item.id} variant={active ? "default" : "ghost"} aria-pressed={active}
          onClick={() => onChange(item.id)} className="h-auto min-h-9 justify-start gap-2 px-2.5 py-1.5 whitespace-normal sm:px-3.5">
          <Icon aria-hidden="true" size={16} className="hidden shrink-0 min-[425px]:block" />
          <span className="text-left leading-tight">
            <span className="block text-xs font-semibold sm:text-sm">{item.label}</span>
            <span className={`block text-[11px] ${active ? "text-white/90" : "text-muted-foreground"}`}>{item.rate} eventos/s</span>
          </span>
        </Button>
      })}
    </div>
    <div className="flex flex-wrap gap-2 text-sm font-semibold text-primary">
      <a href="#comparar-cenarios" className="inline-flex items-center gap-1 rounded-md px-2 py-1 hover:underline">
        Outras cargas e rajada <ArrowDown size={15} aria-hidden="true" />
      </a>
      <a href="#evidencias" className="inline-flex items-center gap-1 rounded-md px-2 py-1 hover:underline">Repetições <ArrowDown size={15} aria-hidden="true" /></a>
    </div>
  </nav>
}

function DestinationFlow({ totals }) {
  return <div className="min-w-0 self-center rounded-lg border border-white/20 bg-white/8 px-3 py-2">
    <div className="mb-1.5 text-[11px] font-semibold tracking-wider text-slate-200 uppercase">Assíncrona · total nas cinco coletas</div>
    <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 tabnums sm:gap-x-3">
      <div><strong className="block text-lg leading-tight lg:text-xl">{format(totals.accepted, 0)}</strong><span className="text-xs text-slate-200">aceites</span></div>
      <ArrowRight className="text-slate-300" size={15} aria-hidden="true" />
      <div><strong className="block text-lg leading-tight text-teal-200 lg:text-xl">{format(totals.stored_final, 0)}</strong><span className="text-xs text-slate-200">no banco</span></div>
      <span className="text-sm text-slate-300">+</span>
      <div><strong className={`block text-lg leading-tight lg:text-xl ${totals.dlq_terminal ? "text-amber-200" : "text-slate-100"}`}>{format(totals.dlq_terminal, 0)}</strong><span className="text-xs text-slate-200">na DLQ</span></div>
    </div>
  </div>
}

export function DefenseFinding({ overview, httpPairs, commitPairs, report }) {
  const { scenario, destinations } = overview
  const guide = defenseNarrative(report, scenario.id)
  const index = DEFENSE_SCENARIOS.indexOf(scenario) + 1
  return <section className={`defense-finding grid min-w-0 gap-2.5 rounded-xl px-4 py-3 text-white sm:px-5 ${destinations ? "lg:grid-cols-[minmax(0,1fr)_auto]" : ""}`} aria-labelledby="defense-title">
    <div className="min-w-0">
      <p className="mb-0.5 text-[11px] font-bold tracking-[.15em] text-indigo-100 uppercase">
        Achado {index} de {DEFENSE_SCENARIOS.length} <span aria-hidden="true">·</span> {scenario.label} <span aria-hidden="true">·</span> {scenario.rate} eventos/s
      </p>
      <h1 id="defense-title" className="text-2xl leading-tight font-semibold tracking-tight sm:text-[1.8rem] lg:text-[2rem]">{scenario.title}</h1>
      <p className="mt-1 text-sm leading-snug text-slate-200 sm:text-[15px]">
        {scenario.profile === "steady" ? guide.pointTo : scenario.context}
        {scenario.profile === "postgres-stop" && <>{" "}<strong className="inline-block text-amber-200">A1: {httpPairs} pares HTTP · {commitPairs} de commit.</strong></>}
      </p>
    </div>
    {destinations && <DestinationFlow totals={destinations} />}
  </section>
}

export function DefenseSidebar({ overview, recovery, report }) {
  const { scenario, rows, hasSync } = overview
  const guide = defenseNarrative(report, scenario.id)
  return <aside className="grid min-w-0 content-start gap-2" aria-label="Indicadores e interpretação do cenário">
    <Card className="gap-1.5 rounded-xl border-border py-2.5">
      <CardHeader className="gap-0.5 px-3.5">
        <CardTitle className="text-[15px]">Evidências para a explicação</CardTitle>
        <CardDescription className="text-xs">Médias por coleta; contagens somadas nas cinco coletas.</CardDescription>
      </CardHeader>
      <CardContent className="px-3.5">
        <Table className="table-fixed" aria-label="Indicadores principais do cenário">
          <TableHeader><TableRow className="border-border bg-muted/60 hover:bg-muted/60">
            <TableHead className="h-7 w-[35%] pl-1.5 text-xs">Indicador</TableHead>
            {hasSync && <TableHead className="h-7 px-1 text-right text-xs font-semibold text-[var(--sync)]">Síncrona</TableHead>}
            <TableHead className="h-7 px-1 text-right text-xs font-semibold text-[var(--async)]">Assíncrona</TableHead>
            {hasSync && <TableHead className="h-7 px-1 text-right text-xs" title="Diferença calculada nos pares elegíveis">Δ A − S</TableHead>}
          </TableRow></TableHeader>
          <TableBody>
            {rows.filter(({ label }) => guide.metrics.includes(label)).map(({ label, unit, values, change, changeUnit }) => <TableRow key={label} className="border-border">
              <TableHead scope="row" className="h-auto px-1.5 py-0.5 text-xs whitespace-normal">
                {label} {unit !== "eventos" && <span className="text-[10px] font-normal text-muted-foreground">({unit})</span>}
              </TableHead>
              {(hasSync ? values : values.slice(1)).map((value, i) => <TableCell key={i} className="px-1 py-0.5 text-right text-xs font-semibold whitespace-normal tabnums">{formatValue(value, unit)}</TableCell>)}
              {hasSync && <TableCell className="px-1 py-0.5 text-right text-xs whitespace-normal text-muted-foreground tabnums">{formatChange(change, changeUnit)}</TableCell>}
            </TableRow>)}
          </TableBody>
        </Table>
        {hasSync && <p className="mt-1 text-[11px] leading-snug text-muted-foreground">Δ = assíncrona − síncrona, nos pares elegíveis. {scenario.profile === "steady" && "CPU e memória em % da síncrona. "}p.p. = pontos percentuais.</p>}
        {scenario.profile === "steady" && <p className="mt-2 border-t border-border pt-2 text-xs leading-relaxed text-muted-foreground"><strong>Recursos do caminho completo:</strong> API + banco na síncrona; API + Kafka + consumidor + banco na assíncrona. CPU: 100% corresponde a uma CPU lógica. Consumo não é custo financeiro.</p>}
        {scenario.profile === "consumer-stop" && <p className="mt-2 text-xs leading-relaxed text-muted-foreground">Contagens ao fim da observação. A ausência de uma coluna síncrona significa “não medido neste cenário”, não zero.</p>}
      </CardContent>
    </Card>
    <div className="rounded-xl border border-border bg-white px-3.5 py-2">
      <h2 className="flex items-center gap-1.5 text-sm font-semibold"><Target size={16} className="text-primary" aria-hidden="true" /> Decisão de projeto</h2>
      <p className="mt-1 text-[13px] leading-snug">{scenario.decision}</p>
      {scenario.profile === "postgres-stop" && <p className="mt-1.5 border-t border-border pt-1.5 text-xs leading-snug text-muted-foreground">
        <strong className="text-foreground">Recuperação assíncrona:</strong> {recovery.original}/{recovery.runs.length} pelo critério original; {recovery.exploratory}/{recovery.runs.length} na leitura exploratória. Os eventos na DLQ não foram gravados.
      </p>}
    </div>
    {scenario.limit && <p className="rounded-lg border border-border bg-muted/70 px-3 py-2 text-xs leading-snug text-muted-foreground">
      <strong className="text-foreground">Limite da evidência. </strong>{scenario.limit}
    </p>}
  </aside>
}

export function ScenarioComparisonTable({ report, condition }) {
  return <Card className="min-w-0 scroll-mt-3 gap-2 rounded-xl border-border py-3">
    <CardHeader className="gap-0.5 px-3.5">
      <CardTitle className="text-base">Comparação entre cargas e cenários</CardTitle>
      <CardDescription className="text-xs">
        Médias por coleta · <span className="font-semibold text-[var(--sync)]">Síncrona</span> / <span className="font-semibold text-[var(--async)]">Assíncrona</span> · Não medido: —.
      </CardDescription>
    </CardHeader>
    <CardContent className="space-y-1 px-3.5">
      <Table aria-label="Comparação entre cargas e cenários" className="min-w-[725px] tabnums">
        <TableHeader><TableRow className="border-border bg-muted/60">
          <TableHead className="h-7 text-xs">Cenário · eventos/s</TableHead>
          {SCENARIO_METRICS.map(({ key, label }) => <TableHead key={key} className="h-7 text-right text-xs">{label}</TableHead>)}
        </TableRow></TableHeader>
        <TableBody>{scenarioComparisons(report).map(({ id, label, metrics }) =>
          <TableRow key={id} className="border-border" data-state={id === condition ? "selected" : undefined}>
            <TableHead scope="row" className="h-auto py-1 text-xs font-semibold">{label}</TableHead>
            {metrics.map(({ unit, values, pairs }, index) =>
              <TableCell key={SCENARIO_METRICS[index].key} title={pairs ? pairs + " pares elegíveis" : "Sem par entre variantes"} className="py-1 text-right text-xs">
                <span className="font-semibold text-[var(--sync)]">{format(values[0])}</span>
                <span className="text-muted-foreground"> / </span>
                <span className="font-semibold text-[var(--async)]">{format(values[1])}</span>{" "}
                <span className="text-[10px] text-muted-foreground">{unit}</span>
              </TableCell>)}
          </TableRow>)}</TableBody>
      </Table>
      <p className="text-[11px] leading-snug text-muted-foreground">Cada linha é um cenário, sem juntar repetições de cargas diferentes. No banco parado, commit usa quatro pares (A1). No consumidor parado, só a assíncrona foi medida.</p>
    </CardContent>
  </Card>
}
