from aproxy.providers.provider_config import ProviderConfigItem


class SshProvider(ProviderConfigItem):
    def __init__(
        self,
        name: str,
        host: str,
        user: str,
        password: str = None,
        ssh_keys: str = None,
    ):
        super().__init__(name)
        if not host or not user:
            raise Exception("missing ssh config")
        self.__host = host
        self.__user = user
        self.__password = password
        self.__ssh_keys = ssh_keys

    def connect(self):
        print("connecting to ssh...")
        return super().connect()


def load_config(config: dict) -> SshProvider:
    user = config["user"] if "user" in config else None
    host = config["host"] if "host" in config else None
    return SshProvider(config["name"], host, user)
