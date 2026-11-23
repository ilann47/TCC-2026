import { COMMIT, HTTP, comparison, finite, format, pairedEffect } from "./analysis.js"
import { defenseOverview } from "./defense.js"

export const DEFENSE_STEPS = [
  { id: "method", label: "1. Método", purpose: "O que foi comparado" },
  { id: "results", label: "2. Resultados", purpose: "O que os gráficos mostram" },
  { id: "failures", label: "3. Falhas", purpose: "O destino de cada aceite" },
  { id: "conclusions", label: "4. Conclusão", purpose: "O que posso afirmar" },
]

export function defenseNarrative(report, condition) {
  const overview = defenseOverview(report, condition)
  const http = comparison(report, condition, HTTP, "a1")
  const commit = comparison(report, condition, COMMIT, "a1")
  const value = (model, variant) => `${format(finite(model[variant]?.mean) ? model[variant].mean / model.scale : null)} ${model.unit}`
  const totals = overview.destinations
  if (overview.scenario.profile === "postgres-stop") return {
    question: "Aceitar uma requisição significa que o registro terminou no banco?",
    pointTo: `Aponte para os destinos: ${format(totals.accepted, 0)} aceites = ${format(totals.stored_final, 0)} no banco + ${format(totals.dlq_terminal, 0)} na fila de falhas.`,
    say: `“Na assíncrona, o cliente recebeu a confirmação do Kafka. Ao fim, ${format(totals.dlq_terminal, 0)} desses aceites estavam na DLQ, não no PostgreSQL. Na síncrona, houve um registro gravado apesar do HTTP 503: falta o horário desse commit, por isso comparo conclusão com ${commit.pairs.length} pares, sem inventar esse tempo.”`,
    caution: "503 é erro HTTP, mas não prova ausência no banco. DLQ é destino de falha conhecido, não gravação bem-sucedida nem perda sem destino.",
    metrics: ["Erros HTTP", "Aceitos por HTTP", "Gravados ao fim", "Respostas 503", "Na DLQ"],
  }
  if (overview.scenario.profile === "consumer-stop") return {
    question: "O sistema consegue receber enquanto o consumidor está parado?",
    pointTo: `Aponte para ${format(totals.accepted, 0)} aceites e ${format(totals.stored_final, 0)} gravações finais; os pontos são ${http.async?.n ?? 0} coletas apenas assíncronas.`,
    say: `“O Kafka continuou recebendo enquanto o consumidor estava parado. Ao fim da observação, os ${format(totals.accepted, 0)} aceites estavam no banco e ${format(totals.dlq_terminal, 0)} na DLQ. O cliente recebeu a resposta antes; a gravação esperou o consumidor. Aqui não existe contraparte síncrona.”`,
    caution: "Gravado ao fim não significa gravado imediatamente. Este cenário não testa perda do broker ou da máquina.",
    metrics: ["Enviados", "Aceitos por HTTP", "Gravados ao fim", "Na DLQ"],
  }
  const effect = pairedEffect(http)
  return {
    question: "Responder ao cliente mais rápido também significou gravar mais rápido?",
    pointTo: `HTTP: ${value(http, "sync")} → ${value(http, "async")}. Gravação: ${value(commit, "sync")} → ${value(commit, "async")}. São médias dos p95 por coleta.`,
    say: `“Nos ${http.pairs.length} pares a ${overview.scenario.rate} eventos/s, a assíncrona teve menor p95 HTTP em ${effect.lower} pares. Mas o p95 até gravar no banco foi maior. O 201 síncrono já confirma a gravação; o 202 assíncrono confirma o Kafka. Portanto, resposta rápida não é conclusão rápida.”`,
    caution: "O gráfico HTTP inclui respostas bem-sucedidas. A diferença é descritiva neste ambiente, não prova de superioridade geral ou de capacidade máxima.",
    metrics: ["Vazão concluída", "Erros HTTP", "CPU média", "Memória média"],
  }
}
