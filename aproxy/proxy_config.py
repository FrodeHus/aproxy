import json
import importlib
from aproxy.providers.provider_config import ProviderConfigItem, ProviderConfig


class ProxyConfig:
    def __init__(self, providers: [], proxies: []):
        self.proxies = proxies
        self.providers = providers


class ProxyItem:
    def __init__(
        self,
        local_host: str,
        local_port: int,
        remote_host: str,
        remote_port: int,
        name: str,
        verbosity: int,
        provider: str = None,
    ):
        self.local_host = local_host
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.receive_first = False
        self.name = name
        self.verbosity = verbosity
        self.provider = provider


def dict_to_config(json_config: dict):
    proxies = []
    for item in json_config["proxies"]:
        local_host = item["localHost"] if "localHost" in item else "0.0.0.0"
        local_port = int(item["localPort"]) if "localPort" in item else 0
        remote_host = item["remoteHost"] if "remoteHost" in item else None
        remote_port = int(item["remotePort"]) if "remotePort" in item else 0
        verbosity = int(item["verbosity"]) if "verbosity" in item else 0
        name = item["name"] if "name" in item else "<noname>"
        provider = item["provider"] if "provider" in item else None
        proxy = ProxyItem(
            local_host, local_port, remote_host, remote_port, name, verbosity, provider
        )
        proxies.append(proxy)
    providers = __load_provider_config(json_config["providerConfig"])
    config = ProxyConfig(providers, proxies)
    return config


def __load_provider_config(cfg: dict):
    providers = {}
    for provider in cfg:
        name = provider["name"]
        provider_name = provider["provider"]["name"]
        full_name = "aproxy.providers." + provider_name
        provider_module = importlib.import_module(full_name)
        provider = provider_module.load_config(provider["provider"])
        providers[name] = provider

    return providers


def load_config(configFile: str):
    with open(configFile, "r") as f:
        cfg = json.load(f)
        return dict_to_config(cfg)
