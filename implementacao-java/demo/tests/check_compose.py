"""Read-only Compose integration check. Never starts a service or prints secrets."""
import json
import subprocess
from pathlib import Path

APP = Path(__file__).resolve().parents[2]


def config(*files):
    result = subprocess.run(["docker", "compose", *files, "config", "--format", "json"],
                            cwd=APP, capture_output=True, check=True)
    return json.loads(result.stdout)


base = config("-f", "docker-compose.yml")
local = config()
assert set(local["services"]) == set(base["services"]) | {"painel", "k6-preparar"}
tool = local["services"]["k6-preparar"]
assert tool["entrypoint"] == ["k6"] and tool["command"] == ["version"], "Preparation must not run a workload"
assert "@sha256:" in tool["image"] and tool["image"] in (APP / "demo/apresentacao.sh").read_text(), "Keep the exact same k6 image"
for name, service in base["services"].items():
    if name == "postgres":
        expected = dict(service)
        expected["ports"] = local["services"][name]["ports"]
        assert expected == local["services"][name], "Only the local PostgreSQL publication may differ"
    else:
        assert service == local["services"][name], "Original service changed: " + name
panel = local["services"]["painel"]
assert panel["read_only"] and not panel.get("privileged", False)
assert panel["ports"][0]["host_ip"] == "127.0.0.1"
assert str(panel["ports"][0]["published"]) == "5666"
assert panel["cap_drop"] == ["ALL"]
assert panel["init"] and "KILL" in panel["cap_add"], "Init must forward signals to the non-root Python child"
mounts = {item["target"]: item for item in panel["volumes"]}
assert mounts["/workspace"]["read_only"]
assert mounts["/var/run/docker.sock"]["read_only"]
assert not mounts["/workspace/implementacao-java/.runtime/demonstracao"].get("read_only", False)
assert local["volumes"] == base["volumes"], "Persistent database/Kafka volumes must be preserved"
print("Compose approved: original services/volumes preserved; panel and non-load k6 preparation added; loopback publication; no service started.")
