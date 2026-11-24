import { useEffect, useState } from "react"
import { createRoot } from "react-dom/client"
import { Activity, ArrowLeft, ChevronRight, CircleHelp, Database, GitCompareArrows, Presentation, ShieldCheck, Table2 } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { PairedChart } from "@/components/paired-chart"
import { DefenseFinding, DefenseNavigation, DefenseSidebar, ScenarioComparisonTable } from "@/components/defense-summary"
import { DefenseConclusions, DefenseMethod, DefenseSteps, ExplainResult, ReadingKey } from "@/components/defense-guide"
import { BLOCKS, COMMIT, DEFAULT_CONDITION, HTTP, choices, comparison, conditionLabel, finite, format, signed } from "@/lib/analysis"
import { defenseOverview, defenseScenario } from "@/lib/defense"
import "./index.css"

const GITHUB = "https://github.com/ilann47/TCC-2026/blob/main/"
const demo = "/"
const cardStyle = "min-w-0 gap-2 rounded-xl border-border bg-card py-3 shadow-[0_1px_3px_#26335c08]"
const headStyle = "px-3 sm:px-3.5"
const cellStyle = "px-2 py-1.5 align-middle text-xs"
const variantLabel = (variant) => variant === "sync" ? "Síncrona" : "Assíncrona"
const policies = [{ value: "a1", label: "Principal · A1" }, { value: "strict", label: "Sensibilidade estrita" }]
const numberIn = (value, model, digits = 2) => finite(value) ? format(value / model.scale, digits) : "—"

function PageHeader({ defense, onToggle }) {
  return <header className="border-b border-border bg-white">
    <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-2 px-3 py-2 sm:px-5">
      <div className="flex items-center gap-3">
        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary text-white"><GitCompareArrows size={16} /></span>
        <div><div className="text-sm font-bold tracking-tight">Laboratório de desempenho</div><div className="text-xs text-muted-foreground">TCC 2026 · Resultados da campanha</div></div>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        <Button variant="outline" size="sm" onClick={onToggle} className="h-8 rounded-lg">
          {defense ? <Table2 aria-hidden="true" size={15} /> : <Presentation aria-hidden="true" size={15} />}
          {defense ? "Consultar dados completos" : "Voltar à apresentação"}
        </Button>
        <nav aria-label="Painel local" className="flex items-center gap-1.5">
          <a href={demo} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border px-2.5 text-xs font-semibold text-foreground hover:bg-muted"><ArrowLeft aria-hidden="true" size={13} /> Demonstração k6</a>
          <a href="/resultados" aria-current="page" className="inline-flex h-8 items-center rounded-lg bg-primary px-2.5 text-xs font-semibold text-white">Resultados da campanha</a>
        </nav>
      </div>
    </div>
  </header>
}

function Hero({ report, defense }) {
  const catalog = report?.catalog
  return <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-border pb-2">
    {defense
      ? <div className="flex items-center gap-2 text-sm font-semibold">
        <Badge className="rounded-md bg-primary"><Presentation aria-hidden="true" size={12} /> Modo Banca</Badge>
        <span>Síncrona × Assíncrona</span>
      </div>
      : <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">Síncrona × Assíncrona</h1>}
    {catalog && <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
      <Badge variant="secondary" className="rounded-md">{defense ? "Campanha do TCC" : "R2/A1"}</Badge>
      <span className="tabnums"><strong className="text-foreground">{catalog.planned_runs}</strong> coletas · {catalog.complete_original_evidence} completas · {catalog.partial_commit_timing} parcial</span>
      <span className="inline-flex items-center gap-1"><ShieldCheck size={13} className="text-emerald-700" /> Somente leitura</span>
    </p>}
  </div>
}

function GridTable({ columns, rows, label }) {
  return <div className="max-w-full overflow-x-auto rounded-xl border border-border">
    <Table aria-label={label}>
      <TableHeader className="bg-muted/70"><TableRow>
        {columns.map((column) => <TableHead key={column} className="h-7 px-2 text-[11px] font-semibold text-muted-foreground">{column}</TableHead>)}
      </TableRow></TableHeader>
      <TableBody>{rows.map((row, i) => <TableRow key={row.key ?? i} data-state={row.selected ? "selected" : undefined} className="tabnums">
        {(row.cells ?? row).map((cell, j) => <TableCell key={j} className={cellStyle}>{cell}</TableCell>)}
      </TableRow>)}</TableBody>
    </Table>
  </div>
}

function Control({ id, label, value, setValue, options }) {
  return <div className="min-w-0">
    <label htmlFor={id} className="mb-1 block text-[11px] font-semibold text-foreground">{label}</label>
    <Select value={value} onValueChange={setValue}>
      <SelectTrigger id={id} className="h-8! w-full min-w-0 bg-white text-xs"><SelectValue /></SelectTrigger>
      <SelectContent>{options.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent>
    </Select>
  </div>
}

function VariantSummary({ model, defense }) {
  const variants = defense && !model.sync ? [["async", model.async]] : [["sync", model.sync], ["async", model.async]]
  return <div className={`grid gap-1.5 ${variants.length === 2 ? "grid-cols-2" : ""}`}>
    {variants.map(([variant, stat]) =>
      <div key={variant} className={`min-w-0 rounded-lg border border-border bg-muted/45 px-2 py-1.5 ${defense ? "lg:px-3" : ""}`}>
        <p className={`flex items-center gap-1 font-medium ${defense ? "text-xs" : "text-[11px] text-muted-foreground"}`}>
          <span className="size-1.5 rounded-full" style={{ background: "var(--" + variant + ")" }} />{variantLabel(variant)}
        </p>
        <p className={`tabnums leading-tight font-bold tracking-tight ${defense ? "text-xl lg:text-[1.8rem]" : "text-base sm:text-lg"}`}>
          {defense && finite(stat?.mean) ? (stat.mean / model.scale).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : numberIn(stat?.mean, model)}
          {" "}<span className={`font-normal text-muted-foreground ${defense ? "text-xs" : "text-[10px]"}`}>{stat?.n ? model.unit : ""}</span>
        </p>
        <p className={`text-muted-foreground ${defense ? "text-[11px]" : "text-[10px]"}`}>{stat?.n ? `${defense ? "Média dos p95" : "Média"} · n=${stat.n}` : stat ? "Sem valor elegível" : "Não aplicável"}</p>
      </div>)}
  </div>
}

function ChartCard({ icon: Icon, title, subtitle, model, selected, onSelect, label, defense = false }) {
  return <Card className={cardStyle} data-chart={label}>
    <CardHeader className={headStyle}>
      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-1.5">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="grid size-6 shrink-0 place-items-center rounded-md bg-accent text-primary"><Icon size={14} /></span>
          <div className="min-w-0">
            <CardTitle className={`leading-tight ${defense ? "text-base" : "text-sm"}`}>{title}</CardTitle>
            <CardDescription className={`leading-tight ${defense ? "text-xs" : "text-[10px]"}`}>{subtitle}</CardDescription>
          </div>
        </div>
        <Badge variant="outline" className="tabnums rounded-md border-border bg-white px-1.5 text-[11px]" data-pair-count={model.pairs.length}>
          {defense && !model.sync ? `${model.async?.n ?? 0} coletas` : `${model.pairs.length} ${model.pairs.length === 1 ? "par" : "pares"}`}
        </Badge>
      </div>
    </CardHeader>
    <CardContent className={headStyle + " space-y-1"}>
      <VariantSummary model={model} defense={defense} />
      <PairedChart title={title} model={model} selected={selected} onSelect={onSelect} defense={defense} />
    </CardContent>
  </Card>
}

function RunTable({ model, selected, onSelect }) {
  return <GridTable label={model.metric.label + " por repetição"}
    columns={["Repetição", "Síncrona (" + model.unit + ")", "Assíncrona (" + model.unit + ")", "A − S (" + model.unit + ")", "Cobertura"]}
    rows={model.rows.map((row) => ({
      key: row.block, selected: row.block === selected,
      cells: [
        <Button size="sm" variant={row.block === selected ? "default" : "ghost"} className="h-7 px-2 text-xs" aria-pressed={row.block === selected} onClick={() => onSelect(row.block === selected ? null : row.block)}>R{row.block}</Button>,
        numberIn(row.sync, model, 3), numberIn(row.async, model, 3),
        signed(finite(row.delta) ? row.delta / model.scale : null, 3),
        <span className="text-xs text-muted-foreground">{row.coverage}</span>,
      ],
    }))} />
}

function PairedValues({ http, commit, selected, onSelect }) {
  const delta = (row, model) => signed(finite(row.delta) ? row.delta / model.scale : null, 3)
  const blockValue = (row, name, model) => numberIn(row[name], model, 3)
  return <Card className={cardStyle}>
    <CardHeader className={headStyle + " gap-0"}>
      <CardTitle className="text-sm">Valores por repetição</CardTitle>
      <CardDescription className="text-[11px]">HTTP em {http.unit} · Commit em {commit.unit} · Δ = A − S · “—” sem valor elegível</CardDescription>
    </CardHeader>
    <CardContent className={headStyle}>
      <GridTable label="HTTP e commit por repetição" columns={["Rep.", "HTTP S", "HTTP A", "Δ HTTP", "Commit S", "Commit A", "Δ commit"]}
        rows={http.rows.map((h, index) => {
          const c = commit.rows[index]
          return { key: h.block, selected: h.block === selected, cells: [
            <Button size="sm" variant={h.block === selected ? "default" : "ghost"} className="h-6 px-1.5 text-[11px]" aria-pressed={h.block === selected}
              title={"HTTP: " + h.coverage + ". Commit: " + c.coverage + "."} onClick={() => onSelect(h.block === selected ? null : h.block)}>R{h.block}</Button>,
            blockValue(h, "sync", http), blockValue(h, "async", http), delta(h, http),
            blockValue(c, "sync", commit), blockValue(c, "async", commit), delta(c, commit),
          ] }
        })} />
    </CardContent>
  </Card>
}

const shortMetrics = {
  http_success_p95_ms: "HTTP p95", http_success_mean_ms: "HTTP médio",
  http_success_median_ms: "HTTP mediana", http_success_p99_ms: "HTTP p99",
  commit_p95_ms: "Commit p95", commit_mean_ms: "Commit médio",
  commit_median_ms: "Commit mediana", commit_p99_ms: "Commit p99",
  throughput_lower: "Vazão · limite inferior", throughput_upper: "Vazão · limite superior",
  http_error_percent: "Erros HTTP", business_cpu_mean_percent: "CPU média",
  business_memory_mean_mib: "Memória média", first_commit_after_restore_s: "Primeiro commit após retomada",
  stable_recovery_confirmed_s: "Recuperação sustentada", backlog_recovery_s: "Backlog integral",
}

function MetricsMatrix({ report, condition, policy, selected, onSelect }) {
  const [expanded, setExpanded] = useState(null)
  const priority = [HTTP, COMMIT, "throughput_lower", "throughput_upper", "http_error_percent", "business_cpu_mean_percent", "business_memory_mean_mib"]
  const metricKeys = [...new Set([...priority, ...report.metrics.map((metric) => metric.key)])]
  const models = metricKeys.map((key) => comparison(report, condition, key, policy))
  const active = models.find((model) => model.key === expanded)
  const summaryCell = (stat, model) => <span className="whitespace-nowrap">
    {numberIn(stat?.mean, model)}
    {stat?.n > 0 && <span className="ml-1 text-[10px] text-muted-foreground" title={"Número de coletas: " + stat.n}>n={stat.n}</span>}
  </span>
  return <Card className={cardStyle}>
    <CardHeader className={headStyle + " gap-0"}>
      <CardTitle className="text-sm">Matriz de indicadores</CardTitle>
      <CardDescription className="text-[11px]">Médias por coleta e diferenças por par. Clique no indicador para ver o detalhe.</CardDescription>
    </CardHeader>
    <CardContent className={headStyle + " space-y-2"}>
      <GridTable label="Todos os indicadores do cenário" columns={["Indicador", "Síncrona", "Assíncrona", "Δ A − S"]}
        rows={models.map((model) => {
          const delta = model.pairs.length ? model.pairs.reduce((sum, row) => sum + row.delta, 0) / model.pairs.length / model.scale : null
          return { key: model.key, selected: expanded === model.key, cells: [
            <button type="button" aria-expanded={expanded === model.key} aria-controls={expanded === model.key ? "metric-detail" : undefined}
              onClick={() => setExpanded(expanded === model.key ? null : model.key)}
              className="flex items-center gap-0.5 text-left font-medium text-primary hover:underline">
              {shortMetrics[model.key] ?? model.metric.label}
              <span className="ml-0.5 text-[10px] font-normal text-muted-foreground">({model.unit})</span><ChevronRight size={11} />
            </button>,
            summaryCell(model.sync, model), summaryCell(model.async, model),
            <span className="whitespace-nowrap" title={model.pairs.length + " pares elegíveis"}>{signed(delta)}{model.pairs.length > 0 && <span className="ml-1 text-[10px] text-muted-foreground">{model.pairs.length}p</span>}</span>,
          ] }
        })} />
      <p className="text-[10px] leading-tight text-muted-foreground">n = coletas elegíveis; p = pares elegíveis. Δ de vazão usa limites contábeis. CPU: 100% = uma CPU lógica.</p>
      {active && <section id="metric-detail" className="space-y-2 rounded-lg border border-border bg-muted/30 p-2">
        <div className="flex flex-wrap items-start justify-between gap-1">
          <h3 className="text-xs font-semibold">{active.metric.label}</h3>
          <Button variant="ghost" size="sm" className="h-6 text-[11px]" onClick={() => setExpanded(null)}>Fechar detalhe</Button>
        </div>
        <p className="text-[11px] text-muted-foreground">{active.metric.definition}</p>
        <GridTable label="Estatísticas por variante" columns={["Variante", "n", "Média", "Mediana", "DP", "Mín.", "Máx."]}
          rows={[["sync", active.sync], ["async", active.async]].map(([name, stats]) => [variantLabel(name), stats?.n ?? "—", ...["mean", "median", "sd_sample", "min", "max"].map((key) => numberIn(stats?.[key], active, 3))])} />
        <RunTable model={active} selected={selected} onSelect={onSelect} />
      </section>}
    </CardContent>
  </Card>
}

function RecoveryStrip({ review }) {
  const dlq = review.runs.reduce((total, run) => total + run.dlq_terminal, 0)
  return <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 rounded-lg border border-border bg-white px-3 py-1.5 text-[11px] text-muted-foreground">
    <a href="#falhas" className="font-semibold text-primary underline-offset-2 hover:underline">Banco parado · Assíncrona</a>
    <span><strong className="tabnums text-foreground">{review.original}/{review.runs.length}</strong> original</span>
    <span><strong className="tabnums text-foreground">{review.exploratory}/{review.runs.length}</strong> exploratória</span>
    <span><strong className="tabnums text-foreground">{dlq}</strong> na DLQ, fora do banco</span>
  </div>
}

function RepetitionSelector({ selected, onSelect }) {
  return <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
    <div className="text-xs font-semibold">Realçar repetição</div>
    <div className="flex flex-wrap items-center gap-1" aria-label="Selecionar repetição">
      {BLOCKS.map((block) => <Button key={block} size="sm" variant={selected === block ? "default" : "outline"} className="h-7 px-2 text-xs" aria-pressed={selected === block} onClick={() => onSelect(selected === block ? null : block)}>R{block}</Button>)}
      {selected && <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => onSelect(null)}>Limpar</Button>}
    </div>
  </div>
}

function Defense({ report, condition, setCondition }) {
  const [selected, setSelected] = useState(null)
  const overview = defenseOverview(report, condition)
  const http = comparison(report, condition, HTTP, "a1")
  const commit = comparison(report, condition, COMMIT, "a1")
  return <section className="space-y-2" aria-label="Modo Banca">
    <DefenseNavigation condition={condition} onChange={(value) => { setCondition(value); setSelected(null) }} />
    <DefenseFinding overview={overview} httpPairs={http.pairs.length} commitPairs={commit.pairs.length} report={report} />
    <div className="grid items-start gap-2 lg:grid-cols-[minmax(0,2.15fr)_minmax(315px,1fr)]">
      <div className="min-w-0 space-y-2">
        <div className="grid items-stretch gap-2 min-[520px]:grid-cols-2">
          <ChartCard icon={Activity} title="Resposta HTTP" subtitle="Espera do cliente · p95 das respostas bem-sucedidas" model={http} selected={selected} onSelect={setSelected} label="http" defense />
          <ChartCard icon={Database} title="Envio até commit" subtitle="Tempo até gravar no banco · p95 por coleta" model={commit} selected={selected} onSelect={setSelected} label="commit" defense />
        </div>
        <ReadingKey paired={overview.hasSync} />
      </div>
      <DefenseSidebar overview={overview} recovery={report.exploratory_recovery} report={report} />
    </div>
    <ExplainResult report={report} condition={condition} />
    <section id="comparar-cenarios" aria-labelledby="comparar-cenarios-heading" className="rounded-xl border border-border bg-white p-3 scroll-mt-3">
      <h2 id="comparar-cenarios-heading" className="text-sm font-semibold text-primary">Outras cargas e rajada · comparar os sete recortes</h2>
      <div className="pt-3"><ScenarioComparisonTable report={report} condition={condition} /></div>
    </section>
    <section id="evidencias" aria-labelledby="evidencias-heading" className="space-y-2 rounded-xl border border-border bg-white p-3 scroll-mt-3">
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <div>
          <h2 id="evidencias-heading" className="text-base font-semibold">Evidências por coleta</h2>
          <p className="text-xs text-muted-foreground">Cinco tentativas por condição. A unidade de análise é a coleta ou o par, não cada evento.</p>
        </div>
        <RepetitionSelector selected={selected} onSelect={setSelected} />
      </div>
      <div className="grid items-start gap-2 min-[1100px]:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
        <PairedValues http={http} commit={commit} selected={selected} onSelect={setSelected} />
        <MetricsMatrix key={condition} report={report} condition={condition} policy="a1" selected={selected} onSelect={setSelected} />
      </div>
    </section>
  </section>
}

function Comparison({ report, condition, setCondition, policy, setPolicy }) {
  const [selected, setSelected] = useState(null)
  const http = comparison(report, condition, HTTP, policy)
  const commit = comparison(report, condition, COMMIT, policy)
  return <section id="comparacao" className="space-y-2">
    <Card className={cardStyle}>
      <CardContent className={headStyle + " grid grid-cols-2 gap-x-2 gap-y-1.5 md:grid-cols-[1fr_.8fr_1fr] md:items-end"}>
        <Control id="scenario" label="Cenário e carga" value={condition} setValue={(value) => { setCondition(value); setSelected(null) }} options={choices(report.groups)} />
        <Control id="policy" label="Regra de análise" value={policy} setValue={(value) => { setPolicy(value); setSelected(null) }} options={policies} />
        <div className="col-span-2 flex flex-wrap items-center gap-x-2 gap-y-1 md:col-span-1 md:block">
          <RepetitionSelector selected={selected} onSelect={setSelected} />
        </div>
      </CardContent>
    </Card>
    {condition.startsWith("postgres-stop") && <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-[11px] leading-relaxed text-amber-950">
      <strong>R3 parcial:</strong> {policy === "strict" ? "excluída dos indicadores comparativos na regra estrita." : "elegível para HTTP; as duas execuções do par ficam fora de commit."} O instante ausente não foi estimado.
    </p>}
    <div className="grid items-start gap-2 min-[1100px]:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
      <div className="min-w-0 space-y-2">
        <div className="grid gap-2 min-[540px]:grid-cols-2">
          <ChartCard icon={Activity} title="Resposta HTTP" subtitle="p95 HTTP válido por coleta" model={http} selected={selected} onSelect={setSelected} label="http" />
          <ChartCard icon={Database} title="Envio até commit" subtitle="p95 até gravar por coleta" model={commit} selected={selected} onSelect={setSelected} label="commit" />
        </div>
        <p className="px-1 text-[10px] leading-relaxed text-muted-foreground">Linhas ligam as execuções do mesmo par. Eixos independentes. HTTP 201 confirma gravação; 202 confirma publicação no Kafka.</p>
        <PairedValues http={http} commit={commit} selected={selected} onSelect={setSelected} />
        {condition.startsWith("postgres-stop") && <RecoveryStrip review={report.exploratory_recovery} />}
      </div>
      <MetricsMatrix report={report} condition={condition} policy={policy} selected={selected} onSelect={setSelected} />
    </div>
  </section>
}

function Failures({ report }) {
  const faults = report.groups.filter((group) => group.profile.endsWith("-stop"))
  const review = report.exploratory_recovery
  const dlq = review.runs.reduce((total, run) => total + run.dlq_terminal, 0)
  const recoveryRuns = report.runs.filter((run) => run.profile.endsWith("-stop"))
  return <section id="falhas" aria-label="Falhas e recuperação" className="space-y-2 scroll-mt-3">
    <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 px-4 py-3">
      <h1 className="text-lg font-semibold">O que aconteceu depois do aceite?</h1>
      <p className="mt-1 text-sm leading-relaxed"><strong>Mostre primeiro a tabela:</strong> com consumidor parado, todos os aceites terminaram no banco. Com banco parado, parte dos aceites terminou na fila de falhas. Depois mostre a recuperação: voltar a operar não significa recuperar automaticamente todos os eventos anteriores.</p>
    </div>
    <Card className={cardStyle}>
      <CardHeader className={headStyle}><CardTitle>Destinos dos eventos</CardTitle><CardDescription>Totais das cinco tentativas em cada condição de falha. Aceite HTTP e gravação final são medidas diferentes.</CardDescription></CardHeader>
      <CardContent className={headStyle + " space-y-3"}>
        <GridTable label="Destinos e integridade" columns={["Cenário / variante", "Enviados", "Aceitos", "No banco", "DLQ", "Fora do banco", "HTTP 503", "Sem destino conciliado"]}
          rows={faults.map((g) => {
            const runs = recoveryRuns.filter((run) => run.profile === g.profile && run.variant === g.variant)
            return [conditionLabel(g.profile, g.rate) + " / " + variantLabel(g.variant), ...["offered", "accepted", "stored_final", "dlq_terminal", "nonpersisted_final"].map((key) => format(g.totals[key], 0)), format(runs.reduce((n, run) => n + (run.http_status_counts["503"] ?? 0), 0), 0), format(g.totals.accepted_unreconciled, 0)]
          })} />
        <p className="text-xs leading-relaxed text-muted-foreground">Na campanha: {format(report.totals.database_duplicate_uuids, 0)} UUIDs duplicados no banco; {format(report.totals.integrity_mismatches, 0)} divergências de conteúdo ou hash; {format(report.totals.pending_retained, 0)} pendências retidas; {format(report.totals.accepted_unreconciled, 0)} aceites sem destino conciliado. Isso não prova entrega exatamente uma vez.</p>
      </CardContent>
    </Card>
    <Card className={cardStyle}>
      <CardHeader className={headStyle}><CardTitle>Recuperação no banco parado · Assíncrona</CardTitle><CardDescription>Os dois critérios respondem a perguntas diferentes.</CardDescription></CardHeader>
      <CardContent className={headStyle + " space-y-2"}>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-border bg-muted/70 p-2.5"><Badge variant="outline">Critério original</Badge><p className="tabnums mt-1 text-xl font-semibold">{review.original}/{review.runs.length}</p><p className="text-xs text-muted-foreground">Conta aceites na DLQ como pendência sem commit.</p></div>
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-2.5"><Badge variant="outline">Leitura exploratória posterior</Badge><p className="tabnums mt-1 text-xl font-semibold">{review.exploratory}/{review.runs.length}</p><p className="text-xs text-muted-foreground">Separa da pendência ativa os destinos com confirmação de DLQ observada. Não substitui o critério original.</p></div>
        </div>
        <Alert><CircleHelp /><AlertTitle>{dlq} eventos na DLQ continuaram fora do PostgreSQL</AlertTitle><AlertDescription>O resultado exploratório não substitui o original. Não houve nova carga nem reclassificação das coletas.</AlertDescription></Alert>
        <p className="rounded-lg bg-muted p-3 text-sm leading-relaxed"><strong>Como explicar:</strong> “O resultado original foi {review.original}/{review.runs.length}. A leitura posterior chegou a {review.exploratory}/{review.runs.length} ao separar os destinos de falha já conhecidos da pendência ativa. Isso não gravou os {dlq} eventos da DLQ e não alterou o resultado original.”</p>
        <GridTable label="Recuperação original e exploratória por repetição" columns={["Repetição", "DLQ terminal", "Critério original", "Leitura exploratória", "Confirmação exploratória (s)"]}
          rows={review.runs.map((run) => ["R" + run.block, run.dlq_terminal, run.original ? "Observado" : "Não observado", run.exploratory ? "Observado" : "Não observado", format(run.confirmation_s)])} />
      </CardContent>
    </Card>
    <section aria-label="Tempos de recuperação por execução" className="rounded-xl border border-border bg-white p-3"><Card className={cardStyle}>
      <CardHeader className={headStyle}><CardTitle>Marcos de recuperação originais</CardTitle><CardDescription>Tempos após o comando de retomada. {report.recovery_caveat}</CardDescription></CardHeader>
      <CardContent className={headStyle}>
        <GridTable label="Marcos originais por coleta" columns={["Cenário / variante", "Repetição", "Primeiro commit (s)", "Confirmação (s)", "Backlog integral (s)", "Critério sustentado"]}
          rows={recoveryRuns.map((run) => [conditionLabel(run.profile, run.rate) + " / " + variantLabel(run.variant), "R" + run.block, format(run.first_commit_after_restore_s), format(run.stable_recovery_confirmed_s), format(run.backlog_recovery_s), run.stable_recovery_observed ? "Observado" : "Não observado"])} />
      </CardContent>
    </Card></section>
  </section>
}

function Sources({ report }) {
  const m = report.method
  const sources = [...report.sources.map(({ name, sha256 }) => ({ name, sha256, path: "implementacao-java/" + report.source_directory + "/" + name })), { name: "recuperacao-exploratoria.json", ...report.exploratory_recovery }]
  return <section id="fontes" aria-label="Método e fontes" className="grid items-start gap-2 scroll-mt-3 lg:grid-cols-2">
    <Card className={cardStyle}>
      <CardHeader className={headStyle}><CardTitle>Protocolo e limites</CardTitle><CardDescription>A unidade de análise é a execução ou o par, não cada evento.</CardDescription></CardHeader>
      <CardContent className={headStyle + " space-y-3 text-sm leading-relaxed"}>
        <p>{report.catalog.conditions} condições, {report.catalog.planned_repetitions} tentativas por condição. {m.pairs} pares comparáveis e {m.consumer_only_runs} coletas apenas assíncronas, com consumidor parado.</p>
        <p>Aquecimento: {m.warmup_s} s. Janela medida: {m.measurement_s} s. Observação posterior: {m.post_observation_s} s. Parada solicitada: {m.requested_failure_s} s. {m.tools}</p>
        <p>{report.warmup_drops_note}</p>
        <Separator />
        <ul className="list-disc space-y-1 pl-5 text-muted-foreground">{report.limits.map((limit) => <li key={limit}>{limit}</li>)}</ul>
      </CardContent>
    </Card>
    <Card className={cardStyle}>
      <CardHeader className={headStyle}><CardTitle>Coleta parcial</CardTitle><CardDescription>{report.partial.post_hoc}</CardDescription></CardHeader>
      <CardContent className={headStyle + " space-y-3 text-sm leading-relaxed"}>
        <p>{report.partial.explanation}</p>
        <p>Tempos observados: {format(report.partial.observed, 0)} de {format(report.partial.stored, 0)} registros no banco. Marco ausente: {report.partial.missing}. Pares completos para conclusão primária neste cenário: {report.partial.primary_pairs}.</p>
        <p className="text-xs text-muted-foreground">Vazão parcial: [{format(report.partial.throughput_lower, 5)}; {format(report.partial.throughput_upper, 5)}] eventos/s. Limites contábeis, não intervalo de confiança.</p>
      </CardContent>
    </Card>
    <Card className={cardStyle}>
      <CardHeader className={headStyle}><CardTitle>Hipóteses no recorte testado</CardTitle></CardHeader>
      <CardContent className={headStyle + " space-y-2"}>
        {report.interpretations.map((item) => <article key={item.expectation} className="rounded-xl border border-border p-3.5">
          <div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-semibold">{item.expectation}</h3><Badge variant="secondary">{item.status}</Badge></div>
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{item.evidence}</p>
        </article>)}
      </CardContent>
    </Card>
    <Card className={cardStyle}>
      <CardHeader className={headStyle}><CardTitle>Fontes e rastreabilidade</CardTitle><CardDescription>{format(report.verification.published_files_verified, 0)} arquivos públicos verificados. {format(report.catalog.raw_files_verified, 0)} itens no catálogo bruto original, sem repetir aqui a auditoria dos conteúdos brutos.</CardDescription></CardHeader>
      <CardContent className={headStyle}>
        <ul className="divide-y divide-border">{sources.map((source) => <li key={source.name} className="py-2.5">
          <a className="text-sm font-medium text-primary underline decoration-primary/35 underline-offset-2" href={GITHUB + source.path} target="_blank" rel="noreferrer">{source.name}</a>
          <p className="mt-1 break-all font-mono text-xs text-muted-foreground">SHA-256: {source.sha256}</p>
        </li>)}</ul>
      </CardContent>
    </Card>
  </section>
}

function App() {
  const [state, setState] = useState({ loading: true })
  const [defense, setDefense] = useState(true)
  const [condition, setCondition] = useState(DEFAULT_CONDITION)
  const [policy, setPolicy] = useState("a1")
  const [defenseStep, setDefenseStep] = useState("results")
  const toggleMode = () => {
    if (!defense && !defenseScenario(condition)) setCondition(DEFAULT_CONDITION)
    setDefense(!defense)
  }
  useEffect(() => {
    const controller = new AbortController()
    fetch("/api/campaign", { signal: controller.signal }).then(async (response) => {
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? "Relatório indisponível.")
      setState({ report: data })
    }).catch((error) => {
      if (!controller.signal.aborted) setState({ error: error.message })
    })
    return () => controller.abort()
  }, [])
  return <>
    <PageHeader defense={defense} onToggle={toggleMode} />
    <main className="mx-auto max-w-[1500px] space-y-2 px-3 pt-2.5 pb-7 sm:px-5">
      <Hero report={state.report} defense={defense} />
      {state.loading && <p role="status" className="rounded-xl border border-border bg-white p-5 text-sm text-muted-foreground">Verificando os relatórios publicados da campanha…</p>}
      {state.error && <Alert variant="destructive"><AlertTitle>Relatório indisponível</AlertTitle><AlertDescription>{state.error}</AlertDescription></Alert>}
      {state.report && <>
        {defense ? <>
          <DefenseSteps active={defenseStep} onChange={(step) => { setDefenseStep(step); window.scrollTo(0, 0) }} />
          {defenseStep === "method" && <DefenseMethod report={state.report} />}
          {defenseStep === "results" && <Defense report={state.report} condition={condition} setCondition={setCondition} />}
          {defenseStep === "failures" && <Failures report={state.report} />}
          {defenseStep === "conclusions" && <DefenseConclusions report={state.report} />}
          <section aria-labelledby="auditoria-heading" className="rounded-xl border border-border bg-white p-3"><h2 id="auditoria-heading" className="text-sm font-semibold text-primary">Auditoria, fontes e detalhes do protocolo</h2><div className="pt-3"><Sources report={state.report} /></div></section>
        </> : <>
          <Comparison report={state.report} condition={condition} setCondition={setCondition} policy={policy} setPolicy={setPolicy} />
          <Failures report={state.report} />
          <Sources report={state.report} />
        </>}
      </>}
      <footer className="pt-2 text-center text-xs text-muted-foreground">Campanha do TCC · Análise descritiva · Nenhum teste de carga é iniciado nesta tela.</footer>
    </main>
  </>
}

createRoot(document.getElementById("root")).render(<App />)
