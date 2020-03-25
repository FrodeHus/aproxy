from aproxy.providers.provider_config import ProviderConfigItem


class KubernetesProvider(ProviderConfigItem):
    def __init__(self, name, service: str = None, pod: str = None, context: str = None):
        super().__init__(name)
        self.__service = service
        self.__pod = pod
        self.__context = context

    def connect(self):
        print("connecting to kubernetes....")
        self.__upload_client()

    def __upload_client(self):
        pass


def load_config(config: dict) -> KubernetesProvider:
    name = config["name"]
    return KubernetesProvider(name)
