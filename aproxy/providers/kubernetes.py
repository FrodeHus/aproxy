from aproxy.providers.provider_config import Provider
from aproxy.providers.kubernetes_capabilites import KubeCapabilities
import socket
from kubernetes import client, config
from kubernetes.client import configuration, V1Pod
from kubernetes.client.api import core_v1_api
from kubernetes.stream import stream
from colorama import Fore
from progress.bar import FillingCirclesBar
import select
import websocket
import six


class KubernetesProvider(Provider):
    def __init__(self, name, context: str = None, staging_pod: str = None):
        super().__init__(name)
        self.__context = context
        self.__staging_pod_name = staging_pod

    def connect(self) -> socket.socket:
        if self.is_connected:
            return

        super().connect()
        config.load_kube_config(context=self.__context)
        self.__client = client.CoreV1Api()
        print(f"[*] active host is {configuration.Configuration().host}")
        if self.__staging_pod_name:
            print(f"[*] using configured staging pod: {self.__staging_pod_name}")
            pod_values = self.__staging_pod_name.split(sep="/")
            pod = self.__client.read_namespaced_pod(pod_values[1], pod_values[0])
            pod_info = self.__run_checks(pod)
            if pod_info.can_connect():
                self.staging_pod = pod_info

        if not self.staging_pod:
            self.staging_pod = self.__find_eligible_staging_pod()

        if self.staging_pod:
            self.is_connected = True

    def client_connect(self, remote_address, remote_port, client_socket):
        super().client_connect(remote_address, remote_port, client_socket)

        self.__setup_staging(remote_address, remote_port)
        self.__create_connection(
            self.staging_pod, remote_address, remote_port, client_socket
        )

    def __find_eligible_staging_pod(self):
        pods = self.__client.list_pod_for_all_namespaces()
        print(
            f"[*] found {len(pods.items)} pods - checking for eligible staging candidates (this may take a while)"
        )
        pod_capabilities = []
        with FillingCirclesBar("[*] Processing...", max=len(pods.items)) as bar:
            for pod_info in pods.items:
                capabilities = self.__run_checks(pod_info)
                pod_capabilities.append(capabilities)
                bar.next()

        self.eligible_pods = [pod for pod in pod_capabilities if pod.can_connect()]
        print(f"[+] valid pods for proxy staging: {len(self.eligible_pods)}")
        for pod in self.eligible_pods:
            print(f"\t{pod.namespace}/{pod.pod_name}")

        print(f"[+] selecting {self.eligible_pods[0]}")
        return self.eligible_pods[0]

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

    def __exec(self, cmd: str, name: str, namespace: str = "default", tty=False):
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
                tty=tty,
            )
            if not resp:
                return None
            if resp.lower().find("no such file or directory") != -1:
                return None

            return resp.strip()
        except:
            return None

    def __upload_client(self):
        print("uploading payload....")
        pass

    def __payload_already_running(
        self, pod: V1Pod, remote_address: str, remote_port: int
    ):
        socat_cmd = f"socat TCP-LISTEN:{remote_port},reuseaddr,fork TCP:{remote_address}:{remote_port}"
        script = f"""if [ -n "$(ps -ef | grep '[s]ocat tcp-l:{remote_port}')" ]; then echo running; fi;"""
        result = self.__exec(script, pod.metadata.name, pod.metadata.namespace)
        if result and result.find("running") != -1:
            return True
        return False

    def __setup_staging(self, remote_address: str, remote_port: int):
        pod = self.staging_pod
        if not pod:
            print("[!!] no staging pod available")
            self.__staging_ready = False

        print(
            f"[+] starting reverse proxy on {pod.namespace}/{pod.pod_name} using {pod.utils[0]} for {remote_address}:{remote_port}"
        )
        socat_cmd = f"socat TCP-LISTEN:{remote_port},reuseaddr,fork TCP:{remote_address}:{remote_port}"
        script = f"""if [ -z "$(ps -ef | grep '[s]ocat tcp-l:{remote_port}')" ]; then {socat_cmd} &; fi;"""
        result = self.__exec(socat_cmd, pod.pod_name, pod.namespace)
        self.__staging_ready = True

    def __create_connection(
        self,
        pod: KubeCapabilities,
        remote_address: str,
        remote_port: int,
        client_socket: socket.socket,
    ):
        if not self.__staging_ready:
            print("[!!] not forwarding traffic - staging not ready")
            return

        fwd = stream(
            self.__client.connect_post_namespaced_pod_portforward,
            pod.pod_name,
            pod.namespace,
            ports=remote_port,
            _preload_content=False,
        )

        remote: websocket.WebSocket = fwd.sock  # let the kubernetes-client do the heavy lifting, then grab the websocket - the stream component is weird with portforwarding

        while True:
            r, _, _ = select.select([client_socket, remote], [], [])
            if client_socket in r:
                data = client_socket.recv(1024)
                if len(data) == 0:
                    break
                binary = six.PY3 and type(data) == six.binary_type
                opcode = (
                    websocket.ABNF.OPCODE_BINARY
                    if binary
                    else websocket.ABNF.OPCODE_TEXT
                )
                channel_prefix = chr(0)
                if binary:
                    channel_prefix = six.binary_type(channel_prefix, "ascii")
                payload = channel_prefix + data
                remote.send(payload, opcode=opcode)

            if remote in r:
                op_code, frame = remote.recv_data_frame()
                if op_code == websocket.ABNF.OPCODE_CLOSE:
                    if client_socket:
                        client_socket.close()
                    break

                if (
                    op_code == websocket.ABNF.OPCODE_BINARY
                    or op_code == websocket.ABNF.OPCODE_TEXT
                ):
                    data = frame.data
                if len(data) == 0:
                    break

                # seems to be some kubernetes websocket control messages that gets sent
                if (
                    data[1] == ord("@")
                    or data == b"\x00\xea\x0c"
                    or data == b"\x01\xea\x0c"
                    or data == b"\x00P\x00"
                    or data == b"\x01P\x00"
                ):
                    continue
                data = data[1:]
                client_socket.send(data)


def load_config(config: dict) -> KubernetesProvider:
    name = config["name"]
    context = config["context"]
    staging_pod = config["stagingPod"] if "stagingPod" in config else None
    return KubernetesProvider(name, context, staging_pod)
