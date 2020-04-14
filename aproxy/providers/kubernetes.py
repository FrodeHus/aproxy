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
        self.__client = client.CoreV1Api()
        print(f"[*] active host is {configuration.Configuration().host}")
        print("[*] detecting cluster services")
        services = self.__find_services()
        for svc in services:
            print(f"\t{svc[0].ljust(50)}\tip: {svc[1].ljust(15)}")
        pods = self.__client.list_pod_for_all_namespaces()
        print("[-] checking for exec capabilities...")
        for pod_info in pods.items:
            capabilities = self.__run_checks(pod_info)
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

    def __run_checks(self, pod_info: V1Pod) -> KubeCapabilities:
        user_script = "whoami"
        user = self.__exec(
            user_script, pod_info.metadata.name, pod_info.metadata.namespace
        )

        utils = self.__find_required_utils(pod_info)
        pkg_manager = self.__find_package_manager(pod_info)

        return KubeCapabilities(
            user,
            pkg_manager,
            utils,
            pod_info.metadata.name,
            pod_info.metadata.namespace,
        )

    def __find_package_manager(self, pod_info: V1Pod):
        pkg_manager_script = """
if [ -x "$(which apk 2>/dev/null)" ]; then echo apk; fi;
if [ -x "$(which apt-get 2>/dev/null)" ]; then echo apt; fi;
if [ -x "$(which zypper 2>/dev/null)" ]; then echo zypper; fi;
if [ -x "$(which yum 2>/dev/null)" ]; then echo yum; fi;
            """
        pkg_manager = self.__exec(
            pkg_manager_script, pod_info.metadata.name, pod_info.metadata.namespace,
        )

        if pkg_manager and pkg_manager.find("exec failed") != -1:
            pkg_manager = "none"

        return pkg_manager

    def __find_required_utils(self, pod_info: V1Pod):
        script = """
if [ -x "$(which socat 2>/dev/null)" ]; then echo socat; fi;
if [ -x "$(which python 2>/dev/null)" ]; then echo python; fi;
        """
        utils = self.__exec(script, pod_info.metadata.name, pod_info.metadata.namespace)
        if utils and utils.find("exec failed") != -1:
            utils = None
        elif utils:
            utils = utils.split("\n")

        return utils

    def __find_services(self):
        services = []
        service_list = self.__client.list_service_for_all_namespaces()
        for svc in service_list.items:
            services.append((svc.metadata.name, svc.spec.cluster_ip))
        return services

    def __exec(self, cmd: str, name: str, namespace: str = "default"):
        exec_command = [
            "/bin/sh",
            "-c",
            f"echo '{cmd}' > /tmp/test.sh; sh /tmp/test.sh; rm /tmp/test.sh",
        ]
        try:
            resp = stream(
                self.__client.connect_get_namespaced_pod_exec,
                name,
                namespace,
                command=exec_command,
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
