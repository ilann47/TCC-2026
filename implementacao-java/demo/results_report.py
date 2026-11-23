"""Same verified, read-only payload for the unified panel and Vite development."""
import threading

from campaign_report import APP, get_report as campaign_report, load_index, read_verified


def build_report():
    # A new outer object leaves the canonical campaign's cached report unchanged.
    report = dict(campaign_report())
    release = APP.parent / "entregas/2026-10-30-entrega-04-correcao-parecer"
    entries = load_index(release)
    name = "recuperacao-exploratoria.json"
    exploratory = read_verified(release, entries, name)
    report["exploratory_recovery"] = {
        "original": exploratory["original_observed"],
        "exploratory": exploratory["exploratory_observed"],
        "runs": [
            {
                "block": run["block"],
                "dlq_terminal": run["dlq_terminal"],
                "original": run["original"]["observed"],
                "exploratory": run["exploratory"]["observed"],
                "confirmation_s": run["exploratory"]["timing"]["confirmed_after_restore_s"],
            }
            for run in exploratory["runs"]
        ],
        "path": "entregas/2026-10-30-entrega-04-correcao-parecer/" + name,
        "sha256": entries[name],
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
