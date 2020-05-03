import json
import importlib
from aproxy.providers.provider_config import Provider, ProviderConfig
from colorama import Fore


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
    providers = _load_provider_config(json_config["providerConfig"])
    config = ProxyConfig(providers, proxies)
    return config


def _load_provider_config(cfg: dict):
    provider_configurations = {}
    for provider in cfg:
        name = provider["name"]
        depends_on = "dependsOn" in provider and provider["dependsOn"]
        provider_name = provider["provider"]["name"]
        full_name = "aproxy.providers." + provider_name
        print(
            f"[*] loading provider configuration for {provider_name} ({full_name}) as {name}"
        )
        provider_module = importlib.import_module(full_name)
        provider = provider_module.load_config(provider["provider"])
        provider_config = ProviderConfig(name, depends_on, provider)

        provider_configurations[name] = provider_config

    provider_configurations["initialized"] = _initialize_providers(
        provider_configurations
    )
    return provider_configurations


def _initialize_providers(providers: {}):
    initialized = []
    for config_name in providers:
        if config_name in initialized:
            continue
        config = providers[config_name]
        if not config.depends_on:
            config.provider.connect()
            if config.provider.is_connected:
                initialized.append(config_name)
    return initialized


def load_config(configFile: str):
    with open(configFile, "r") as f:
        cfg = json.load(f)
        return dict_to_config(cfg)
