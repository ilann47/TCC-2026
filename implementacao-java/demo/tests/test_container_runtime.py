"""No Docker calls: reject unsafe mounts, network exposure and container identities."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from container_runtime import panel_network, settings


def container():
    source = "/mnt/c/project/TCC-2026"
    return {
        "Config": {"Labels": {"com.docker.compose.project": "tcc-java-2026", "com.docker.compose.service": "painel"}},
        "HostConfig": {"Privileged": False, "PortBindings": {"5666/tcp": [{"HostIp": "127.0.0.1", "HostPort": "5666"}]}},
        "Mounts": [
            {"Destination": "/workspace", "Source": source, "Type": "bind", "RW": False},
            {"Destination": "/workspace/implementacao-java/.runtime/demonstracao", "Source": source + "/implementacao-java/.runtime/demonstracao", "Type": "bind", "RW": True},
            {"Destination": "/var/run/docker.sock", "Source": "/var/run/docker.sock", "Type": "bind", "RW": False},
        ],
        "NetworkSettings": {"Networks": {"tcc-java-2026_default": {"Gateway": "172.28.0.1"}}},
    }


class ContainerRuntimeTests(unittest.TestCase):
    def test_only_expected_host_paths_are_translated(self):
        value = settings(container())
        self.assertEqual(value["TCC_PANEL_HOST_APP"], "/mnt/c/project/TCC-2026/implementacao-java")
        self.assertEqual(value["TCC_PANEL_RESULTS_DIST"], "/opt/tcc-results")
        self.assertEqual(value["TCC_PANEL_GATEWAY"], "172.28.0.1")

    def test_unknown_project_or_service_is_rejected(self):
        for key, value in (("com.docker.compose.project", "other"), ("com.docker.compose.service", "sync-api")):
            info = container()
            info["Config"]["Labels"][key] = value
            with self.assertRaises(ValueError):
                settings(info)

    def test_public_port_and_privileged_are_rejected(self):
        for host in ("0.0.0.0", "", "192.168.0.1", "::"):
            info = container()
            info["HostConfig"]["PortBindings"]["5666/tcp"][0]["HostIp"] = host
            with self.subTest(host=host), self.assertRaises(ValueError):
                settings(info)
        info = container()
        info["HostConfig"]["Privileged"] = True
        with self.assertRaises(ValueError):
            settings(info)

    def test_repository_and_socket_cannot_be_writable_mounts(self):
        for index in (0, 2):
            info = container()
            info["Mounts"][index]["RW"] = True
            with self.subTest(index=index), self.assertRaises(ValueError):
                settings(info)

    def test_history_cannot_point_to_another_project_or_the_campaign(self):
        for path in ("/another/project", "/mnt/c/project/TCC-2026/implementacao-java/.runtime/reduzida65-2026-10-27-r2"):
            info = container()
            info["Mounts"][1]["Source"] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                settings(info)

    def test_unsafe_host_mount_names_are_rejected(self):
        for path in ("/", "relative/project", "/mnt/a/../private", "/mnt/a,extra", "/mnt/a\nextra"):
            info = container()
            info["Mounts"][0]["Source"] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                settings(info)

    def test_other_networks_or_invalid_gateways_are_rejected(self):
        info = container()
        info["NetworkSettings"]["Networks"]["foreign"] = {"Gateway": "172.30.0.1"}
        with self.assertRaises(ValueError):
            settings(info)
        for gateway in ("8.8.8.8", "0.0.0.0", "127.0.0.1", "", "::1"):
            info = container()
            info["NetworkSettings"]["Networks"]["tcc-java-2026_default"]["Gateway"] = gateway
            with self.subTest(gateway=gateway), self.assertRaises(ValueError):
                settings(info)

    def test_normal_host_mode_stays_loopback_only(self):
        self.assertEqual(panel_network({}, False), ("127.0.0.1", {"127.0.0.1"}))

    def test_container_mode_requires_container_and_private_gateway(self):
        env = settings(container())
        self.assertEqual(panel_network(env, True), ("0.0.0.0", {"127.0.0.1", "172.28.0.1"}))
        with self.assertRaises(ValueError):
            panel_network(env, False)
        for gateway in ("8.8.8.8", "0.0.0.0", "127.0.0.1", ""):
            with self.subTest(gateway=gateway), self.assertRaises(ValueError):
                panel_network(dict(env, TCC_PANEL_GATEWAY=gateway), True)
