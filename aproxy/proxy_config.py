import json


class ProxyConfig:
    def __init__(self, proxies: []):
        self.proxies = proxies


class ProxyItem:
    def __init__(
        self,
        local_host: str,
        local_port: int,
        remote_host: str,
        remote_port: int,
        name: str,
        verbosity: int,
    ):
        self.local_host = local_host
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.receive_first = False
        self.name = name
        self.verbosity = verbosity


def dict_to_config(json_config: dict):
    verbosity = int(json_config["verbosity"]) if "verbosity" in json_config else 0
    proxies = []
    for item in json_config["proxies"]:
        local_host = item["localHost"] if "localHost" in item else "0.0.0.0"
        local_port = int(item["localPort"]) if "localPort" in item else 0
        remote_host = item["remoteHost"] if "remoteHost" in item else None
        remote_port = int(item["remotePort"]) if "remotePort" in item else 0
        verbosity = int(item["verbosity"]) if "verbosity" in item else 0
        name = item["name"] if "name" in item else "<noname>"
        proxy = ProxyItem(
            local_host, local_port, remote_host, remote_port, name, verbosity
        )
        proxies.append(proxy)
    config = ProxyConfig(proxies)
    return config


def load_config(configFile: str):
    with open(configFile, "r") as f:
        cfg = json.load(f)
        return dict_to_config(cfg)
