"""Small, standard-library-only helpers for the local presentation menu."""
import argparse
import json
import math
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def canonical_uuid(value):
    result = str(uuid.UUID(value))
    if result != value:
        raise ValueError("UUID deve estar no formato canônico, em minúsculas")
    return result


def build_payload(event_id, run_id, variant):
    canonical_uuid(event_id)
    canonical_uuid(run_id)
    if variant not in ("sync", "async"):
        raise ValueError("variante inválida")
    return {
        "event_id": event_id,
        "event_type": "created",
        "entity_type": "demonstracao",
        "entity_id": f"DEMO-{variant}-{event_id[:8]}",
        "actor_id": "apresentacao",
        "source": f"demo-apresentacao-{run_id}",
        "occurred_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "payload": {"acao": "demonstracao local", "variante": variant},
    }


def loopback_url(mapping):
    match = re.fullmatch(r"127\.0\.0\.1:([0-9]{1,5})", mapping.strip())
    if not match or not 1 <= int(match[1]) <= 65535:
        raise ValueError("esperada uma única porta publicada em 127.0.0.1; alvo remoto recusado")
    return "http://" + match[0]


def verify_response(body, event_id, code):
    canonical_uuid(event_id)
    if not isinstance(body, dict) or body.get("event_id") != event_id:
        raise ValueError("resposta não devolveu o UUID enviado")
    statuses = {"201": ("persisted", "duplicate"), "202": ("accepted",), "200": ("persisted",)}
    if code not in statuses or body.get("status") not in statuses[code]:
        raise ValueError("status do corpo não corresponde ao contrato HTTP")


def verify_k6(summary):
    if summary.get("kind") != "presentation_demo_not_definitive":
        raise ValueError("resumo não pertence à demonstração")
    if summary.get("sent", 0) <= 0:
        raise ValueError("nenhum evento enviado")
    if summary.get("errors") != 0 or summary.get("dropped_iterations") != 0:
        raise ValueError("houve resposta inválida ou iteração não iniciada; examine os arquivos")
    for field in ("avg", "med", "p(95)", "p(99)", "max"):
        value = summary.get("http_duration_ms", {}).get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"métrica HTTP ausente/inválida: {field}")


def load_json(file):
    return json.loads(Path(file).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    payload = sub.add_parser("payload")
    payload.add_argument("event_id")
    payload.add_argument("run_id")
    payload.add_argument("variant", choices=("sync", "async"))
    address = sub.add_parser("address")
    address.add_argument("mapping")
    pretty = sub.add_parser("pretty")
    pretty.add_argument("file")
    response = sub.add_parser("response")
    response.add_argument("file")
    response.add_argument("event_id")
    response.add_argument("http_code")
    k6 = sub.add_parser("k6")
    k6.add_argument("file")
    args = parser.parse_args()
    try:
        if args.command == "payload":
            print(json.dumps(build_payload(args.event_id, args.run_id, args.variant), ensure_ascii=False, indent=2))
        elif args.command == "address":
            print(loopback_url(args.mapping))
        elif args.command == "pretty":
            print(json.dumps(load_json(args.file), ensure_ascii=False, indent=2))
        elif args.command == "response":
            verify_response(load_json(args.file), args.event_id, args.http_code)
        else:
            verify_k6(load_json(args.file))
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"Falha de conferência: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
