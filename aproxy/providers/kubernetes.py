from aproxy.providers.provider_config import ProviderConfigItem
import socket


class K8sPossiblities:
    def __init__(self):
        super().__init__()

    def passthrough_ok(self):
        return False


class KubernetesProvider(ProviderConfigItem):
    EXEC_URL = "wss://{}:8443/api/v1/namespaces/default/pods/{}/exec?command={}&stderr=true&stdin=true&stdout=true&tty=false"

    def __init__(
        self,
        name,
        api_url: str,
        service: str = None,
        pod: str = None,
        context: str = None,
    ):
        super().__init__(name)
        self.__service = service
        self.__pod = pod
        self.__context = context

    def connect(self, remote_address: str, remote_port: int) -> socket.socket:
        super().connect(remote_address, remote_port)
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

    def __exec(self, cmd: str):
        url = self.EXEC_URL.format(self.__url, self.__pod, cmd)


def load_config(config: dict) -> KubernetesProvider:
    name = config["name"]
    return KubernetesProvider(name)
