from aproxy.providers.provider_config import Provider
from aproxy.providers.kubernetes_capabilites import KubeCapabilities
import socket
import aproxy.providers.kube_util as kube_util
from kubernetes import client, config
from kubernetes.client import configuration, V1Pod
from kubernetes.stream import stream
import select
import websocket
import six
import traceback


class KubernetesProvider(Provider):
    def __init__(self, name, context: str = None, staging_pod: str = None):
        super().__init__(name)
        self.staging_pod = None
        self.__staging_ready = False
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
            pod_info = kube_util.run_checks(self.__client, pod)
            if pod_info.can_connect():
                self.staging_pod = pod_info

        if not self.staging_pod:
            self.staging_pod = kube_util.find_eligible_staging_pod(self.__client)

        if self.staging_pod:
            self.is_connected = True

    def client_connect(self, remote_address, remote_port, client_socket):
        super().client_connect(remote_address, remote_port, client_socket)

        kube_util.setup_staging(
            self.__client, self.staging_pod, remote_address, remote_port
        )
        self.__create_connection(
            self.staging_pod, remote_address, remote_port, client_socket
        )

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
                    or len(data) == 3
                ):
                    continue
                data = data[1:]
                client_socket.send(data)


def load_config(config: dict) -> KubernetesProvider:
    name = config["name"]
    context = config["context"]
    staging_pod = config["stagingPod"] if "stagingPod" in config else None
    return KubernetesProvider(name, context, staging_pod)
