import json, socket


class Provider:
    def __init__(self, name: str):
        self.name = name
        self.__is_connected = False
        self.__initializing = False

    def connect(self):
        pass

    def client_connect(
        self, remote_address: str, remote_port: int, client_socket: socket.socket
    ) -> socket.socket:
        pass

    @property
    def is_connected(self) -> bool:
        return self.__is_connected

    @is_connected.setter
    def is_connected(self, value: bool):
        self.__is_connected = value

    @property
    def initializing(self) -> bool:
        return self.__initializing

    @initializing.setter
    def initializing(self, value: bool):
        self.__initializing = value


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
