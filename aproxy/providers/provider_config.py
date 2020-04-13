import json, socket


class ProviderConfigItem:
    def __init__(self, name: str):
        self.name = name

    def connect(self):
        pass

    def client_connect(
        self, remote_address: str, remote_port: int, client_socket: socket.socket
    ) -> socket.socket:
        pass


class ProviderConfig:
    def __init__(self, name: str, provider: ProviderConfigItem):
        self.name = name
        self.provider = provider
