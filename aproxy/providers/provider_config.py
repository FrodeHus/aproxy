import json, socket


class ProviderConfigItem:
    def __init__(self, name: str):
        self.name = name

    def connect(self, remote_address: str, remote_port: int):
        self.__remote_address = remote_address
        self.__remote_port = remote_port

    def client_connect(self) -> socket.socket:
        pass


class ProviderConfig:
    def __init__(self, name: str, provider: ProviderConfigItem):
        self.name = name
        self.provider = provider
