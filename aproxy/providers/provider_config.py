import json, socket


class Provider:
    def __init__(self, name: str):
        self.name = name
        self._is_connected = False
        self._initializing = False

    def connect(self):
        pass

    def client_connect(
        self, remote_address: str, remote_port: int, client_socket: socket.socket
    ) -> socket.socket:
        pass

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @is_connected.setter
    def is_connected(self, value: bool):
        self._is_connected = value

    @property
    def initializing(self) -> bool:
        return self._initializing

    @initializing.setter
    def initializing(self, value: bool):
        self._initializing = value


class ProviderConfig:
    def __init__(self, name: str, depends_on: [], provider: Provider):
        self._name = name
        self._provider = provider
        self._depends_on = depends_on

    @property
    def depends_on(self):
        return self._depends_on

    @property
    def name(self):
        return self._name

    @property
    def provider(self) -> Provider:
        return self._provider
