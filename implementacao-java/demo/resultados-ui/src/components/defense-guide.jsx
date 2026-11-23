import { ArrowRight, BookOpen, CheckCheck, CircleHelp, MessageSquareQuote, Pointer, Scale } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { DEFENSE_STEPS, defenseNarrative } from "@/lib/defense-guide"
import { format } from "@/lib/analysis"

const card = "min-w-0 gap-2 rounded-xl border-border py-3"

export function DefenseSteps({ active, onChange }) {
  return <nav aria-label="Roteiro da banca" className="sticky top-0 z-20 grid grid-cols-2 gap-1.5 rounded-xl border border-border bg-white p-1.5 shadow-sm sm:grid-cols-4">
    {DEFENSE_STEPS.map((step) => <Button key={step.id} variant={active === step.id ? "default" : "ghost"}
      aria-pressed={active === step.id} onClick={() => onChange(step.id)} className="h-auto justify-start whitespace-normal px-3 py-2 text-left">
      <span><span className="block text-sm font-semibold">{step.label}</span><span className={`block text-[11px] font-normal ${active === step.id ? "text-white/85" : "text-muted-foreground"}`}>{step.purpose}</span></span>
    </Button>)}
  </nav>
}

export function ExplainResult({ report, condition }) {
  const guide = defenseNarrative(report, condition)
  return <section aria-label="Como explicar este resultado" className="grid gap-2 rounded-xl border border-indigo-200 bg-indigo-50/60 p-3 lg:grid-cols-[minmax(0,.85fr)_minmax(0,1.15fr)]">
    <div>
      <h2 className="flex items-center gap-1.5 text-sm font-semibold"><Pointer size={15} aria-hidden="true" /> O que mostrar</h2>
      <p className="mt-1 text-[13px] leading-snug font-medium">{guide.question}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{guide.pointTo}</p>
    </div>
    <div className="border-border lg:border-l lg:pl-3">
      <h2 className="flex items-center gap-1.5 text-sm font-semibold"><MessageSquareQuote size={15} aria-hidden="true" /> Como explicar à banca</h2>
      <p className="mt-1 text-[13px] leading-relaxed">{guide.say}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground"><strong>Não confundir: </strong>{guide.caution}</p>
    </div>
  </section>
}

export function ReadingKey({ paired }) {
  return <div aria-label="Como ler os gráficos" className="grid gap-x-4 gap-y-1 rounded-lg border border-border bg-white px-3 py-2 text-xs leading-snug sm:grid-cols-2">
    <p><strong>HTTP:</strong> espera do cliente. <strong>Commit:</strong> gravação confirmada no banco.</p>
    <p><strong>p95:</strong> tempo até o qual ficaram 95% das observações de uma coleta; os cartões mostram a média desses p95.</p>
    <p><strong>201:</strong> gravado. <strong>202:</strong> publicado no Kafka; consumidor grava depois.</p>
    <p>{paired ? <><strong>Cada linha:</strong> um par da mesma repetição. Δ = assíncrona − síncrona; negativo significa menos tempo. Eixos independentes.</> : <><strong>Cada ponto:</strong> uma coleta assíncrona. Não há par síncrono nem diferença entre variantes.</>}</p>
  </div>
}

export function DefenseMethod({ report }) {
  const m = report.method
  return <section aria-label="Método para explicar na banca" className="space-y-2">
    <Card className={card}>
      <CardHeader className="gap-1 px-4"><CardTitle className="flex items-center gap-2 text-base"><BookOpen size={17} /> O que foi comparado?</CardTitle><CardDescription>Dois caminhos para processar o mesmo tipo de registro de auditoria. A resposta HTTP não confirma a mesma etapa.</CardDescription></CardHeader>
      <CardContent className="grid gap-2 px-4 md:grid-cols-2">
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3"><Badge>Síncrona · HTTP 201</Badge><p className="mt-2 text-sm font-semibold">Cliente → API → PostgreSQL → resposta</p><p className="mt-1 text-sm text-muted-foreground">O cliente espera a transação terminar. A resposta bem-sucedida já confirma a gravação.</p></div>
        <div className="rounded-lg border border-teal-200 bg-teal-50 p-3"><Badge variant="secondary">Assíncrona · HTTP 202</Badge><p className="mt-2 text-sm font-semibold">Cliente → API → Kafka → resposta</p><p className="mt-1 text-sm text-muted-foreground">Depois: Kafka → consumidor → PostgreSQL. O aceite não confirma o commit no banco.</p></div>
      </CardContent>
    </Card>
    <div className="grid gap-2 md:grid-cols-2">
      <Card className={card}>
        <CardHeader className="gap-1 px-4"><CardTitle>Por que comparar cinco pares?</CardTitle></CardHeader>
        <CardContent className="space-y-2 px-4 text-sm leading-relaxed">
          <p><strong>{report.catalog.planned_runs} tentativas = {report.catalog.conditions} condições × {report.catalog.planned_repetitions} repetições.</strong> Foram {m.pairs} pares entre variantes e {m.consumer_only_runs} coletas só assíncronas, com consumidor parado.</p>
          <p>Cada par reúne a mesma condição e repetição. Cada ponto é uma execução, não um evento individual; milhares de eventos não viram milhares de repetições independentes.</p>
          <p className="rounded-lg bg-muted p-2.5"><strong>O que dizer:</strong> “Comparei as variantes por repetição, sem juntar todas as requisições em uma única amostra.”</p>
        </CardContent>
      </Card>
      <Card className={card}>
        <CardHeader className="gap-1 px-4"><CardTitle>Como cada execução foi observada?</CardTitle></CardHeader>
        <CardContent className="space-y-2 px-4 text-sm leading-relaxed">
          <div className="flex flex-wrap items-center gap-2 rounded-lg bg-muted p-2.5 text-xs"><span>Aquecer <strong>{m.warmup_s} s</strong></span><ArrowRight size={14} /><span>Medir <strong>{m.measurement_s} s</strong></span><ArrowRight size={14} /><span>Observar depois <strong>{m.post_observation_s} s</strong></span></div>
          <p>Nos cenários de falha, a parada solicitada foi de <strong>{m.requested_failure_s} s</strong>. Esse tempo não é o resultado de recuperação.</p>
          <p>{m.tools}</p><p className="text-xs text-muted-foreground">A vazão conta commits na janela medida, não gravações posteriores como se tivessem acontecido sob carga.</p>
        </CardContent>
      </Card>
    </div>
    <Card className={card}>
      <CardHeader className="gap-1 px-4"><CardTitle className="flex items-center gap-2 text-base"><CircleHelp size={17} /> Por que há uma coleta parcial?</CardTitle><CardDescription>{report.partial.post_hoc}</CardDescription></CardHeader>
      <CardContent className="grid gap-3 px-4 text-sm leading-relaxed md:grid-cols-2">
        <div className="space-y-2"><p>{report.partial.explanation}</p><p><strong>Evidência:</strong> {format(report.partial.observed, 0)} horários observados em {format(report.partial.stored, 0)} gravações. Falta {report.partial.missing} marco temporal; não foi estimado.</p></div>
        <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3"><p><strong>Impacto mostrado no painel:</strong> cinco pares para HTTP; {report.partial.primary_pairs} pares para a comparação primária de conclusão no banco parado.</p><p><strong>Por que não repetir?</strong> Preservou-se a tentativa planejada e o resultado desfavorável. Uma reposição após observar a falha mudaria o conjunto da análise; exigiria uma nova decisão metodológica, não apagar ou substituir a original.</p><p className="text-xs">O veredito original continua inválido; a emenda A1 qualifica somente as métricas sustentadas pela evidência.</p></div>
      </CardContent>
    </Card>
    <p className="rounded-lg border border-border bg-white px-4 py-3 text-sm"><strong>Escopo da conclusão:</strong> estudo local, dados sintéticos e cinco repetições por condição. Não é benchmark de capacidade máxima, teste de significância ou prova de superioridade universal.</p>
  </section>
}

export function DefenseConclusions({ report }) {
  return <section aria-label="Conclusões para explicar na banca" className="space-y-2">
    <Card className={card}>
      <CardHeader className="gap-1 px-4"><CardTitle className="flex items-center gap-2 text-lg"><Scale size={18} /> A escolha depende da confirmação que o cliente precisa</CardTitle><CardDescription>Os resultados sustentam compromissos de projeto, não um vencedor geral.</CardDescription></CardHeader>
      <CardContent className="grid gap-2 px-4 text-sm md:grid-cols-2">
        <article className="rounded-lg border border-border p-3"><h2 className="font-semibold text-[var(--sync)]">Quando considerar a síncrona</h2><p className="mt-1 leading-relaxed">Quando a resposta precisar confirmar que o registro já está no banco. No recorte medido sem falha, teve menor p95 até commit e menor consumo do caminho completo.</p></article>
        <article className="rounded-lg border border-border p-3"><h2 className="font-semibold text-[var(--async)]">Quando considerar a assíncrona</h2><p className="mt-1 leading-relaxed">Quando for aceitável confirmar a publicação e gravar depois. O aceite foi mais rápido; com consumidor parado, a fila reteve os aceites. É necessário acompanhar pendências e DLQ.</p></article>
      </CardContent>
    </Card>
    <Card className={card}>
      <CardHeader className="gap-1 px-4"><CardTitle className="flex items-center gap-2 text-base"><CheckCheck size={17} /> O que as hipóteses receberam de apoio?</CardTitle><CardDescription>Apoio descritivo no recorte não equivale a confirmação estatística.</CardDescription></CardHeader>
      <CardContent className="space-y-2 px-4">
        {report.interpretations.map((item) => <article key={item.expectation} className="grid gap-1 rounded-lg border border-border p-3 sm:grid-cols-[minmax(0,.9fr)_minmax(0,1.1fr)]"><div><h2 className="text-sm font-semibold">{item.expectation}</h2><p className="mt-1 text-xs font-medium text-primary">{item.status}</p></div><p className="text-sm leading-relaxed text-muted-foreground">{item.evidence}</p></article>)}
      </CardContent>
    </Card>
    <div className="grid gap-2 md:grid-cols-2">
      <div className="rounded-xl border border-border bg-white p-4"><h2 className="text-sm font-semibold">Limitações que preciso mencionar</h2><ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-muted-foreground">{report.limits.map((item) => <li key={item}>{item}</li>)}</ul></div>
      <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4"><h2 className="text-sm font-semibold">Frase para encerrar</h2><p className="mt-2 text-sm leading-relaxed">“A assíncrona não foi simplesmente mais rápida: ela antecipou a confirmação de aceite e adiou a gravação. A síncrona confirmou a gravação na própria resposta. Nas falhas, precisei olhar o destino dos eventos, não apenas o código HTTP. A escolha depende desse compromisso e dos limites do ambiente avaliado.”</p><p className="mt-3 text-xs text-muted-foreground">CPU e memória não medem custo financeiro ou esforço de manutenção. Fila de falhas não é sucesso de persistência.</p></div>
    </div>
  </section>
}
