import json


class ProviderConfigItem:
    def __init__(self, name: str):
        self.name = name

    def connect(self):
        pass


class ProviderConfig:
    def __init__(self, name: str, provider: ProviderConfigItem):
        self.name = name
        self.provider = provider
