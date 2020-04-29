import json, socket


class Provider:
    is_connected = False

    def __init__(self, name: str):
        self.name = name

    def connect(self):
        pass

    def client_connect(
        self, remote_address: str, remote_port: int, client_socket: socket.socket
    ) -> socket.socket:
        pass


class ProviderConfig:
    def __init__(self, name: str, depends_on: [], provider: Provider):
        self.__name = name
        self.__provider = provider
        self.__depends_on = depends_on

    @property
    def depends_on(self):
        return self.__depends_on

    @property
    def name(self):
        return self.__name

    @property
    def provider(self) -> Provider:
        return self.__provider
