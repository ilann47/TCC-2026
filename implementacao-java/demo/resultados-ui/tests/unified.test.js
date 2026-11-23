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
