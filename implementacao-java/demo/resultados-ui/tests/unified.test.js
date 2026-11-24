import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")

test("production bundle stays under the unified results route", () => {
  assert.match(read("../vite.config.js"), /base: "\/resultados\/"/)
})

test("navigation uses the same server and does not require a second port", () => {
  const results = read("../src/main.jsx")
  const demo = read("../../panel/index.html")
  assert.match(results, /const demo = "\/"/)
  assert.match(results, /aria-label="Painel local"/)
  assert.match(results, /href="\/resultados" aria-current="page"/)
  assert.match(demo, /href="\/" aria-current="page"/)
  assert.match(demo, /href="\/resultados"/)
  assert.doesNotMatch(results, /localhost:566[67]/)
})

test("result evidence is rendered without collapsed sections or reveal actions", () => {
  const results = read("../src/main.jsx")
  const navigation = read("../src/components/defense-summary.jsx")
  assert.doesNotMatch(results, /<details\b|<summary\b|showEvidence|showScenarios/)
  assert.match(results, /<section id="comparar-cenarios" aria-labelledby="comparar-cenarios-heading"/)
  assert.match(results, /<section id="evidencias" aria-labelledby="evidencias-heading"/)
  assert.match(results, /<ScenarioComparisonTable report=\{report\} condition=\{condition\}/)
  assert.match(results, /<section aria-label="Tempos de recupera\u00e7\u00e3o por execu\u00e7\u00e3o"/)
  assert.match(results, /<section aria-labelledby="auditoria-heading"/)
  assert.match(navigation, /href="#comparar-cenarios"/)
  assert.match(navigation, /href="#evidencias"/)
  assert.doesNotMatch(navigation, /onCompare|onEvidence|Ver repeti\u00e7\u00f5es/)
})

test("result interpretation keeps its content without a speaker-only heading", () => {
  const guide = read("../src/components/defense-guide.jsx")
  assert.doesNotMatch(guide, /Como explicar à banca|MessageSquareQuote/)
  assert.match(guide, /aria-label="Interpretação do resultado"/)
  assert.match(guide, /\{guide\.say\}/)
  assert.match(guide, /\{guide\.caution\}/)
})
