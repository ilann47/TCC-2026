import { execFile } from "node:child_process"
import { fileURLToPath } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

function verifiedReport() {
  let cached
  function load() {
    if (!cached) {
      const python = process.env.TCC_REPORT_PYTHON || (process.platform === "win32" ? "python" : "python3")
      const script = fileURLToPath(new URL("./scripts/read_report.py", import.meta.url))
      cached = new Promise((resolve, reject) => {
        execFile(python, ["-B", "-X", "utf8", script], {
          timeout: 70_000, maxBuffer: 8 * 1024 * 1024, windowsHide: true,
          env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
        }, (error, stdout) => error ? reject(error) : resolve(stdout))
      }).catch((error) => { cached = undefined; throw error })
    }
    return cached
  }
  function middleware(server) {
    server.middlewares.use(async (req, res, next) => {
      if (req.url?.split("?")[0] !== "/api/campaign") return next()
      res.setHeader("Content-Type", "application/json; charset=utf-8")
      res.setHeader("Cache-Control", "no-store")
      if (req.method !== "GET") {
        res.statusCode = 405
        res.setHeader("Allow", "GET")
        return res.end(JSON.stringify({ error: "O relatório é somente leitura." }))
      }
      try {
        res.end(await load())
      } catch (error) {
        server.config.logger.error("Falha ao verificar os relatórios: " + error.message.split("\n")[0])
        res.statusCode = 503
        res.end(JSON.stringify({ error: "Não foi possível verificar os relatórios locais. Confira a instalação do Python e o conjunto publicado da campanha." }))
      }
    })
  }
  return { name: "tcc-verified-campaign", configureServer: middleware, configurePreviewServer: middleware }
}

export default defineConfig({
  base: "/resultados/",
  plugins: [react(), tailwindcss(), verifiedReport()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { host: "127.0.0.1", port: 5667, strictPort: true },
  preview: { host: "127.0.0.1", port: 5667, strictPort: true },
})
