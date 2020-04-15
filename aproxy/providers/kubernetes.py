from aproxy.providers.provider_config import ProviderConfigItem
from aproxy.providers.kubernetes_capabilites import KubeCapabilities
import socket
from kubernetes import client, config
from kubernetes.client import configuration, V1Pod
from kubernetes.client.api import core_v1_api
from kubernetes.stream import stream
from colorama import Fore


class KubernetesProvider(ProviderConfigItem):
    def __init__(
        self, name, context: str = None,
    ):
        super().__init__(name)
        self.__context = context

    def connect(self) -> socket.socket:
        if self.is_connected:
            return

        super().connect()
        config.load_kube_config(context=self.__context)
        self.__client = client.CoreV1Api()
        print(f"[*] active host is {configuration.Configuration().host}")
        pods = self.__client.list_pod_for_all_namespaces()
        print(
            f"[*] found {len(pods.items)} pods - checking for eligible staging candidates"
        )
        pod_capabilities = []
        for pod_info in pods.items:
            capabilities = self.__run_checks(pod_info)
            pod_capabilities.append(capabilities)

        self.eligible_pods = [pod for pod in pod_capabilities if pod.can_connect()]
        print(f"\tfound {len(self.eligible_pods)}")
        self.is_connected = True

    def client_connect(self, remote_address, remote_port, client_socket):
        super().client_connect(remote_address, remote_port, client_socket)

        print(f"[+] valid pods for proxy staging: {len(self.eligible_pods)}")
        print(f"[+] selecting {self.eligible_pods[0]}")
        self.__create_connection(self.eligible_pods[0], remote_address, remote_port)

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

    def __create_connection(
        self, pod: KubeCapabilities, remote_address: str, remote_port: int
    ):
        print(
            f"[+] starting reverse proxy on {pod.namespace}/{pod.pod_name} using {pod.utils[0]} for {remote_address}:{remote_port}"
        )
        script = f"""
socat TCP-LISTEN:{remote_port},reuseaddr,fork TCP:{remote_address}:{remote_port} &
        """
        result = self.__exec(script, pod.pod_name, pod.namespace)
        get = stream(
            self.__client.connect_get_namespaced_pod_portforward,
            pod.pod_name,
            pod.namespace,
            ports=remote_port,
            _request_timeout=10,
            _preload_content=False,
        )

        put = stream(
            self.__client.connect_post_namespaced_pod_portforward,
            pod.pod_name,
            pod.namespace,
            ports=remote_port,
            _request_timeout=10,
            _preload_content=False,
        )

        while get.is_open():
            get.update(timeout=1)
            put.update(timeout=1)
            put.write_stdin("GET / HTTP/1.1\n\n")
            if get.peek_stdout():
                print("GET STDOUT: %s" % get.read_stdout())
            if put.peek_stdout():
                print("PUT STDOUT: %s" % put.read_stdout())
            if get.peek_stderr():
                print("GET STDERR: %s" % get.read_stderr())
            if put.peek_stderr():
                print("PUT STDERR: %s" % put.read_stderr())

        pass


def load_config(config: dict) -> KubernetesProvider:
    name = config["name"]
    context = config["context"]
    return KubernetesProvider(name, context)
