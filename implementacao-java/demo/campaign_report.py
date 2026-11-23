"""Read-only scientific report shared by the local panel and seminar slides."""
import argparse
import hashlib
import json
import math
import statistics
import subprocess
import sys
import threading
from collections import Counter
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
RELATIVE = Path("experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1")
PARTIAL_ID = "8733a7d2-89b5-4a5e-be22-0e4ed6e6b29b"
METRICS = [
    ("http_success_p95_ms", "p95 HTTP válido", "ms", "Média dos p95 por execução. Retorno HTTP, sem equivaler à conclusão assíncrona."),
    ("http_success_mean_ms", "HTTP médio", "ms", "Cada valor é a média HTTP de uma execução, sem agrupar seus eventos aos das demais."),
    ("http_success_median_ms", "Mediana HTTP", "ms", "Cada valor é a mediana HTTP de uma execução."),
    ("http_success_p99_ms", "p99 HTTP válido", "ms", "Projeção descritiva dos p99 já publicados por execução, sem nova medição."),
    ("commit_p95_ms", "p95 envio até commit", "ms", "Primária: exclui a parcial e sua contraparte no bloco 3 com banco parado. n=4 pares nessa condição."),
    ("commit_mean_ms", "Envio até commit médio", "ms", "Marco após o retorno da transação e conciliação com o banco. Ausência não vira zero."),
    ("commit_median_ms", "Mediana envio até commit", "ms", "Mesmo recorte de pares completos da análise primária de conclusão."),
    ("commit_p99_ms", "p99 envio até commit", "ms", "Projeção dos p99 publicados, com a mesma exclusão primária da conclusão."),
    ("throughput_lower", "Vazão concluída: limite inferior", "eventos/s", "Janela medida de 180 s. Limite contábil na parcial, sem imputação e sem usar drenagem para inflar a janela."),
    ("throughput_upper", "Vazão concluída: limite superior", "eventos/s", "Limite superior contábil, não intervalo de confiança."),
    ("http_error_percent", "Erros HTTP", "%", "503 continua erro mesmo quando a persistência final foi comprovada."),
    ("business_cpu_mean_percent", "CPU média do caminho completo", "% CPU lógica", "Soma simultânea de API+banco na síncrona e API+consumidor+banco+Kafka na assíncrona. 100% corresponde a uma CPU lógica."),
    ("business_memory_mean_mib", "Memória média do caminho completo", "MiB", "Médias por execução das somas simultâneas. Gerador e observador separados. Sem inferência financeira."),
    ("first_commit_after_restore_s", "Primeiro commit observado após retomada", "s", "Marco observado, não primeiro commit real desconhecido. Ausências permanecem sem valor."),
    ("stable_recovery_confirmed_s", "Confirmação da recuperação sustentada", "s", "Três janelas completas de 10 s ainda sob entrada ativa. Informe n observado e os cinco casos previstos."),
    ("backlog_recovery_s", "Persistência integral do backlog anterior", "s", "Não confundir com retorno do serviço ou primeiro commit. DLQ impede persistência integral dos aceites anteriores."),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_index(root):
    entries = {}
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        value, name = line.split("  ", 1)
        target = (root / name).resolve()
        if root.resolve() not in target.parents or name in entries:
            raise ValueError("Índice público inválido")
        entries[name] = value
    return entries


def read_verified(root, entries, name):
    path = root / name
    if name not in entries or digest(path) != entries[name]:
        raise ValueError("Checksum público divergente: " + name)
    return json.loads(path.read_text(encoding="utf-8"))


def eligible(run, metric, strict=False):
    if strict and run["profile"] == "postgres-stop" and run["block"] == 3:
        return False
    if metric.startswith("commit_") and not run["paired_commit_primary_included"]:
        return False
    value = run.get(metric)
    return type(value) in (int, float) and math.isfinite(value)


def stats(values):
    if not values:
        return {"n": 0, "values": []}
    return {"n": len(values), "values": values, "mean": statistics.mean(values),
            "median": statistics.median(values), "sd_sample": statistics.stdev(values) if len(values)>1 else None,
            "min": min(values), "max": max(values)}


def build_report(app=APP, full_verify=True):
    app = Path(app)
    root = app / RELATIVE
    if full_verify:
        check = subprocess.run([sys.executable, str(app / "experimento/verify_final_results.py")],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=True)
        verification = json.loads(check.stdout)
    else:
        verification = {"full_public_verifier_run": False}
    entries = load_index(root)
    catalog = read_verified(root, entries, "catalog.json")
    if (catalog["planned_runs"], catalog["complete_original_evidence"], catalog["partial_commit_timing"]) != (65,64,1):
        raise ValueError("Classificação diferente da campanha R2/A1 auditada")
    records = read_verified(root, entries, "per-run.json")
    if len(records) != 65 or len({run["run_id"] for run in records}) != 65:
        raise ValueError("Conjunto de UUIDs inválido")
    groups = read_verified(root, entries, "group-summary.json")
    strict = read_verified(root, entries, "strict-sensitivity.json")
    pairs = read_verified(root, entries, "paired.json")
    sensitivity = read_verified(root, entries, "partial-latency-sensitivity.json")
    source_names = ["catalog.json","per-run.json","group-summary.json","paired.json",
                    "strict-sensitivity.json","partial-latency-sensitivity.json"]
    for run in records:
        name = "runs/"+run["run_id"]+"-"+run["variant"]+".json"
        summary = read_verified(root, entries, name)
        run["http_status_counts"] = summary["http_status_counts"]
        run["original_instrument_valid"] = summary["instrument_valid"]
    if len(groups) != 13 or any(group["planned_n"] != 5 for group in groups):
        raise ValueError("Condições/repetições divergentes")
    # Extend the display with p99 already present in each published run, never
    # rewrite the frozen aggregate files or classify a partial as complete.
    for collection, strict_mode in ((groups,False),(strict,True)):
        for group in collection:
            runs = sorted((run for run in records if all(run[key] == group[key] for key in ("profile","rate","variant"))),key=lambda run:run["block"])
            for key in ("http_success_p99_ms","commit_p99_ms"):
                group["metrics"][key] = stats([run[key] for run in runs if eligible(run,key,strict_mode)])
    totals = Counter()
    for run in records:
        for key in ("offered","accepted","stored_final","dlq_terminal","pending_retained",
                    "accepted_unreconciled","database_duplicate_uuids","integrity_mismatches"):
            totals[key] += run[key]
    partial = next(run for run in records if run["run_id"] == PARTIAL_ID)
    report = {
        "schema": "tcc_campaign_dashboard_v1", "kind": "published_scientific_campaign_not_live_demo",
        "catalog": {key:catalog[key] for key in ("finished_utc","planned_runs","complete_original_evidence",
                    "partial_commit_timing","conditions","planned_repetitions","raw_files_verified","analysis_unit","resource_definition","collection_commits")},
        "verification": verification,
        "sources": [{"name":name,"sha256":entries[name]} for name in source_names],
        "public_index_sha256": digest(root / "SHA256SUMS"),
        "source_directory": RELATIVE.as_posix(),
        "method": {"warmup_s":60,"measurement_s":180,"post_observation_s":90,"requested_failure_s":40,
                   "steady_rates":[12,24,36,48],"burst_rates":[48,96,48],"pilot_validations":9,
                   "pairs":sum(len(group["pairs"]) for group in pairs),
                   "consumer_only_runs":sum(run["profile"] == "consumer-stop" for run in records),"independent_unit":"execução ou par, não evento",
                   "tools":"k6 gerou carga e exportou amostras. O analisador Java conciliou marcos e PostgreSQL. A escolha não demonstra superioridade do k6 sobre JMeter."},
        "metrics": [{"key":key,"label":label,"unit":unit,"definition":definition} for key,label,unit,definition in METRICS],
        "groups":groups,"strict_groups":strict,"paired":pairs,"runs":sorted(records,key=lambda run:(run["profile"],run["rate"],run["block"],run["variant"])),
        "totals":dict(totals),
        "partial": {"run_id":PARTIAL_ID,"block":partial["block"],"observed":partial["commit_observed_n"],
                    "stored":partial["stored_final"],"missing":partial["commit_unobserved_n"],
                    "throughput_lower":partial["throughput_lower"],"throughput_upper":partial["throughput_upper"],
                    "original_instrument_valid":partial["original_instrument_valid"],
                    "sensitivity_groups":sensitivity,
                    "explanation":"Na 37ª tentativa, um evento persistiu apesar de HTTP 503, sem registro do horário de seu commit. A parada do banco fazia parte do teste. A ausência do marco temporal foi uma limitação imprevista da evidência. A1 preserva o veredito original inválido e qualifica por métrica, sem repetir/substituir a coleta nem imputar o instante ausente.",
                    "primary_pairs":4,"post_hoc":"A1 decidida após as primeiras 37 tentativas e antes das 28 restantes."},
        "interpretations":[
            {"expectation":"Menor custo básico da síncrona em carga reduzida","status":"Apoio descritivo no recorte","evidence":"CPU e memória do caminho completo menores nos pares comparáveis. Dinheiro e esforço de manutenção não foram medidos."},
            {"expectation":"Menor latência de aceitação na assíncrona","status":"Apoio descritivo no recorte","evidence":"p95 HTTP menor nos cinco pares de cada uma das seis condições comparáveis. Nas condições sem falha, p95 de conclusão maior."},
            {"expectation":"Retenção de eventos com consumidor indisponível","status":"Apoio nos cinco casos examinados","evidence":"Todos os 10.801 aceites medidos terminaram persistidos, sem DLQ. Isso não testa perda física da máquina ou do broker."},
            {"expectation":"Todo aceite assíncrono acaba automaticamente no banco","status":"Generalização não sustentada","evidence":"Com banco parado, 14 aceites terminaram em DLQ. O sistema não faz replay automático dessa fila."},
            {"expectation":"Menor custo financeiro ou manutenção","status":"Inconclusivo","evidence":"Topologia e consumo de recursos não medem dinheiro nem esforço de manutenção."},
        ],
        "recovery_caveat":"O critério composto exige três janelas de 10 s sob carga ativa. O cálculo inclui DLQ como aceite sem commit. Três DLQ ultrapassam o limite de dois e impedem a aprovação em quatro casos de banco parado assíncrono. Isso não demonstra indisponibilidade contínua do serviço.",
        "limits":["Um computador compartilhado e dados sintéticos","Um broker, uma partição e uma réplica",
                  "Cinco tentativas por condição, sem teste de significância ou equivalência",
                  "Pausas operacionais documentadas e emenda A1 pós-hoc",
                  "Médias de recursos em falhas incluem componentes parados, sem provar eficiência",
                  "Janela finita de recuperação e tempos ausentes sem imputação",
                  "Sem custo financeiro, manutenção ou tolerância à perda física medidos"],
        "warmup_drops_note":"Onze dropped iterations ocorreram no aquecimento de uma execução de rajada. Não são drops da janela medida nem perda de registros enviados.",
    }
    return report


_lock = threading.Lock()
_cached = None


def get_report():
    global _cached
    with _lock:
        if _cached is None:
            _cached = build_report()
        return _cached


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = get_report()
    text = json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open("x",encoding="utf-8") as stream:
            stream.write(text)
        print(json.dumps({"output":str(args.output),"runs":len(result["runs"]),"groups":len(result["groups"])}))
    else:
        print(text)
