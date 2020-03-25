from aproxy.providers.provider_config import ProviderConfigItem
import socket


class K8sPossiblities:
    def __init__(self):
        super().__init__()

    def passthrough_ok(self):
        return False


class KubernetesProvider(ProviderConfigItem):
    def __init__(self, name, service: str = None, pod: str = None, context: str = None):
        super().__init__(name)
        self.__service = service
        self.__pod = pod
        self.__context = context

    def connect(self) -> socket.socket:
        print("connecting to kubernetes [context: {}] ....".format(self.__context))
        possibilies = self.__run_checks()
        if not possibilies.passthrough_ok:
            self.__upload_client()
        else:
            pass
        return self.__create_connection(None, None)

    def __run_checks(self) -> K8sPossiblities:
        return K8sPossiblities()

    def __upload_client(self):
        print("uploading payload....")
        pass

    def __create_connection(self, host: str, port: int):
        print("connecting to {}:{}... ".format(host, port))
        pass

    def __can_I_do_this_without_uploads(self) -> bool:
        pass


def load_config(config: dict) -> KubernetesProvider:
    name = config["name"]
    return KubernetesProvider(name)
