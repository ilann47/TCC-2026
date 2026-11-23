import { HTTP, finite, format, pairedEffect, signed } from "@/lib/analysis"

const X_SYNC = 92
const X_ASYNC = 272
const TOP = 14
const BOTTOM = 113
const syncColor = "var(--sync)"
const asyncColor = "var(--async)"

export function PairedChart({ model, selected, onSelect, title, defense = false }) {
  const values = model.rows.flatMap((row) => [row.sync, row.async]).filter(finite).map((n) => n / model.scale)
  if (!values.length) {
    return <div role="status" className="grid min-h-28 place-items-center rounded-lg border border-dashed border-border p-2 text-center text-xs text-muted-foreground">
      Nenhum valor elegível neste recorte. Ausência não equivale a zero.
    </div>
  }
  const min = Math.min(...values), max = Math.max(...values)
  const pad = Math.max((max - min) * 0.16, Math.abs(max) * 0.025, 0.001)
  const lo = min >= 0 ? Math.max(0, min - pad) : min - pad
  const hi = max + pad
  const y = (value) => BOTTOM - (value / model.scale - lo) / (hi - lo) * (BOTTOM - TOP)
  const ordered = [...model.rows].sort((a, b) => Number(a.block === selected) - Number(b.block === selected))
  const active = model.rows.find((row) => row.block === selected)
  const renderValue = (value) => finite(value) ? format(value / model.scale, 3) + " " + model.unit : "sem valor"
  const standalone = model.rows.every((row) => row.sync === null)
  const single = defense && standalone
  const asyncX = single ? 190 : X_ASYNC
  const effect = pairedEffect(model)
  return <figure className="min-w-0">
    <svg viewBox="0 0 337 145" className={`block h-auto w-full ${defense ? "max-h-[190px]" : "max-h-44"}`} role="img"
      aria-label={title + ". " + (single ? model.rows.filter((row) => finite(row.async)).length + " coletas assíncronas, sem contraparte síncrona" : model.pairs.length + " pares elegíveis") + ", unidade " + model.unit + "."}>
      <title>{title}</title>
      {[0, 1, 2, 3].map((i) => {
        const gy = TOP + (BOTTOM - TOP) * i / 3
        return <g key={i}>
          <line x1="53" x2="324" y1={gy} y2={gy} stroke={defense ? "#d9e0ef" : "#e5eaf3"} strokeDasharray={i === 3 ? undefined : "4 4"} />
          <text x="47" y={gy + 4} textAnchor="end" className="chart-tick">{format(hi - (hi - lo) * i / 3, 2)}</text>
        </g>
      })}
      {!single && <line x1={X_SYNC} x2={X_SYNC} y1={TOP} y2={BOTTOM} stroke="#e3e8f1" />}
      <line x1={asyncX} x2={asyncX} y1={TOP} y2={BOTTOM} stroke="#e3e8f1" />
      {ordered.map((row) => {
        const s = finite(row.sync), a = finite(row.async), highlighted = row.block === selected
        if (!s && !a) return null
        const opacity = selected && !highlighted ? 0.26 : 1
        // Small horizontal offsets distinguish overlapping repetitions without changing any y-value.
        const offset = (row.block - 3) * 3
        return <g key={row.block} opacity={opacity} data-pair={row.block} className="cursor-pointer" onClick={() => onSelect(highlighted ? null : row.block)}>
          <title>{"R" + row.block + " · Síncrona: " + renderValue(row.sync) + " · Assíncrona: " + renderValue(row.async)}</title>
          {s && a && <>
            <line x1={X_SYNC + offset} x2={X_ASYNC + offset} y1={y(row.sync)} y2={y(row.async)} stroke="transparent" strokeWidth="14" />
            <line data-pair-link={row.block} x1={X_SYNC + offset} x2={X_ASYNC + offset} y1={y(row.sync)} y2={y(row.async)}
              stroke={highlighted ? "#273b71" : defense ? "#7b8db3" : "#a1aec9"} strokeWidth={highlighted ? 2.7 : defense ? 2.2 : 1.7} />
          </>}
          {s && <circle cx={X_SYNC + offset} cy={y(row.sync)} r={highlighted ? 6 : 4.7} fill={syncColor} stroke="white" strokeWidth="1.2" />}
          {a && <circle cx={asyncX + offset} cy={y(row.async)} r={highlighted ? 6 : 4.7} fill={asyncColor} stroke="white" strokeWidth="1.2" />}
        </g>
      })}
      {!single && <text x={X_SYNC} y="135" textAnchor="middle" fill={syncColor} className="chart-variant">Síncrona</text>}
      <text x={asyncX} y="135" textAnchor="middle" fill={asyncColor} className="chart-variant">Assíncrona</text>
    </svg>
    <figcaption className={`min-h-6 rounded-md bg-muted px-2 py-1 leading-snug text-muted-foreground ${defense ? "text-xs font-medium" : "text-[11px]"}`}>
      {active
        ? <>R{active.block} · S: {renderValue(active.sync)} · A: {renderValue(active.async)}
          {finite(active.delta) ? " · A − S: " + signed(active.delta / model.scale, 3) + " " + model.unit : " · " + active.coverage}</>
        : standalone ? "Apenas coletas assíncronas neste recorte."
          : effect.n ? <>
            Δ médio (A − S): <strong>{signed(effect.delta)} {model.unit}</strong>
            {defense && model.key === HTTP && effect.percent !== null && <> · <strong>{signed(effect.percent, 1)}%</strong></>}
            {defense && (effect.lower > 0 || effect.higher > 0) && <>
              {effect.lower ? " · A menor em " + effect.lower : " · A maior em " + effect.higher}/{effect.n} pares
            </>}
          </>
            : "Sem pares completos para este indicador. Pontos isolados não geram diferenças."}
    </figcaption>
  </figure>
}
