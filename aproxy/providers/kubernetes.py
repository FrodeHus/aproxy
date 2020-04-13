from aproxy.providers.provider_config import ProviderConfigItem
from aproxy.providers.kubernetes_capabilites import KubeCapabilities
import socket
from kubernetes import client, config
from kubernetes.client import configuration, V1Pod
from kubernetes.client.api import core_v1_api
from kubernetes.stream import stream
from colorama import Fore


class KubernetesProvider(ProviderConfigItem):
    EXEC_URL = "wss://{}:8443/api/v1/namespaces/default/pods/{}/exec?command={}&stderr=true&stdin=true&stdout=true&tty=false"

    def __init__(
        self, name, context: str = None,
    ):
        super().__init__(name)
        self.__context = context
        config.load_kube_config(context=context)
        print(f"[*] active host is {configuration.Configuration().host}")
        v1 = client.CoreV1Api()
        pods = v1.list_pod_for_all_namespaces()
        print("[-] checking for exec capabilities...")
        for pod_info in pods.items:
            capabilities = self.__run_checks(v1, pod_info)
            print(f"\t{capabilities}")

    def connect(self, remote_address: str, remote_port: int) -> socket.socket:
        super().connect()

        print("connecting to kubernetes [context: {}] ....".format(self.__context))
        possibilies = self.__run_checks()
        if not possibilies.passthrough_ok():
            self.__upload_client()
        else:
            pass
        return self.__create_connection(None, None)

    def __run_checks(self, client: core_v1_api, pod_info: V1Pod) -> KubeCapabilities:
        exec_command = ["/bin/sh", "-c", "whoami"]
        user = self.__exec(
            exec_command, client, pod_info.metadata.name, pod_info.metadata.namespace
        )
        return KubeCapabilities(user)

    def __exec(
        self, cmd: [], client: core_v1_api, name: str, namespace: str = "default"
    ):
        try:
            resp = stream(
                client.connect_get_namespaced_pod_exec,
                name,
                namespace,
                command=cmd,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
            )
            if not resp:
                return None
            return resp.strip()
        except:
            return None

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
    context = config["context"]
    return KubernetesProvider(name, context)
