"""Validate the local Compose container, map host bind paths and drop Unix privileges."""
import ipaddress
import json
import os
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath

WORKSPACE = Path("/workspace")
APP = WORKSPACE / "implementacao-java"
RUNTIME = APP / ".runtime/demonstracao"


def panel_network(environment, in_container):
    if environment.get("TCC_PANEL_CONTAINER") != "1":
        return "127.0.0.1", {"127.0.0.1"}
    if not in_container:
        raise ValueError("Modo de rede do painel permitido somente dentro do contêiner.")
    gateway = ipaddress.ip_address(environment.get("TCC_PANEL_GATEWAY", ""))
    if gateway.version != 4 or not gateway.is_private or gateway.is_loopback or gateway.is_unspecified:
        raise ValueError("Gateway privado inválido; não vou aceitar clientes adicionais.")
    return "0.0.0.0", {"127.0.0.1", str(gateway)}


def settings(info):
    labels = info.get("Config", {}).get("Labels", {})
    if (labels.get("com.docker.compose.project") != "tcc-java-2026"
            or labels.get("com.docker.compose.service") != "painel"):
        raise ValueError("O bootstrap aceita somente o painel deste projeto Compose.")
    host = info.get("HostConfig", {})
    bindings = host.get("PortBindings", {}).get("5666/tcp")
    if host.get("Privileged") or bindings != [{"HostIp": "127.0.0.1", "HostPort": "5666"}]:
        raise ValueError("O painel exige porta 5666 publicada exclusivamente em loopback, sem privileged.")
    mounts = {item.get("Destination"): item for item in info.get("Mounts", [])}
    workspace = mounts.get(str(WORKSPACE), {})
    source = PurePosixPath(workspace.get("Source", ""))
    if (workspace.get("Type") != "bind" or workspace.get("RW") is not False
            or not source.is_absolute() or len(source.parts) < 3 or ".." in source.parts
            or any(char in str(source) for char in "\r\n,\x00")):
        raise ValueError("O repositório deve ser um bind somente leitura, com caminho absoluto seguro.")
    runtime = mounts.get(str(RUNTIME), {})
    if (runtime.get("Type") != "bind" or runtime.get("RW") is not True
            or runtime.get("Source") != str(source / "implementacao-java/.runtime/demonstracao")):
        raise ValueError("A escrita deve apontar somente ao histórico da demonstração deste repositório.")
    socket = mounts.get("/var/run/docker.sock", {})
    if socket.get("Type") != "bind" or socket.get("RW") is not False:
        raise ValueError("Socket Docker local não encontrado no ponto previsto.")
    networks = info.get("NetworkSettings", {}).get("Networks", {})
    if set(networks) != {"tcc-java-2026_default"}:
        raise ValueError("O painel deve usar somente a rede deste Compose.")
    gateway = ipaddress.ip_address(networks["tcc-java-2026_default"].get("Gateway", ""))
    if gateway.version != 4 or not gateway.is_private or gateway.is_loopback or gateway.is_unspecified:
        raise ValueError("Gateway privado da rede Compose inválido.")
    return {"TCC_PANEL_CONTAINER": "1", "TCC_PANEL_GATEWAY": str(gateway),
            "TCC_PANEL_HOST_APP": str(source / "implementacao-java"),
            "TCC_PANEL_RESULTS_DIST": "/opt/tcc-results"}


def main():
    if not Path("/.dockerenv").is_file() or not stat.S_ISSOCK(Path("/var/run/docker.sock").stat().st_mode):
        raise ValueError("Este bootstrap deve rodar no contêiner local, com socket Unix Docker.")
    identity = os.environ.get("HOSTNAME", "")
    if not identity or any(char not in "0123456789abcdef" for char in identity):
        raise ValueError("Identidade do contêiner inválida.")
    result = subprocess.run(["docker", "inspect", identity], capture_output=True, check=True, timeout=10)
    info = json.loads(result.stdout)
    if len(info) != 1:
        raise ValueError("Esperado um único contêiner de painel.")
    environment = settings(info[0])
    owner = WORKSPACE.stat()
    uid, gid = owner.st_uid or 10001, owner.st_gid or 10001
    # Only the top-level demo directory may need ownership on a fresh clone.
    # Existing job, pair, evidence and campaign files are never rewritten/chowned here.
    if RUNTIME.stat().st_uid == 0:
        os.chown(RUNTIME, uid, gid)
    socket_gid = Path("/var/run/docker.sock").stat().st_gid
    os.setgroups(sorted({gid, socket_gid}))
    os.setgid(gid)
    os.setuid(uid)
    os.umask(0o002)
    os.environ.update(environment, HOME="/tmp", DOCKER_CONFIG="/tmp/docker")
    print("Painel Compose: interface unificada na porta 5666; nenhuma carga iniciada.", flush=True)
    os.execv(sys.executable, [sys.executable, "-B", str(APP / "demo/panel.py"), "--port", "5666"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(f"Painel não iniciado: {type(error).__name__}: {error}")
