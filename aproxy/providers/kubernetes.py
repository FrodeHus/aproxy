from aproxy.providers.provider_config import Provider
from aproxy.providers.staging_pod import StagingPod
import socket
import aproxy.providers.kube_util as kube_util
from kubernetes import client, config
from kubernetes.client import configuration, V1Pod
from kubernetes.stream import stream
import select
import websocket
import six
import threading
import traceback

CHANNEL_STDIN = 0
CHANNEL_STDOUT = 1
CHANNEL_ERR = 2


class KubernetesProvider(Provider):
    def __init__(self, name, context: str = None, staging_pod: str = None):
        super().__init__(name)
        self.staging_pod = None
        self._staging_ready = False
        self._context = context
        self._staging_pod_name = staging_pod

    @property
    def exclude_namespaces(self):
        return self.__exclude_namespaces

    @exclude_namespaces.setter
    def exclude_namespaces(self, namespaces: []):
        self._exclude_namespaces = namespaces

    def connect(self) -> socket.socket:
        if self.is_connected:
            return
        self.initializing = True
        super().connect()
        config.load_kube_config(context=self._context)
        self._client = client.CoreV1Api()
        print(f"[*] active host is {configuration.Configuration().host}")
        if self._staging_pod_name:
            print(f"[*] using configured staging pod: {self.__staging_pod_name}")
            pod_values = self._staging_pod_name.split(sep="/")
            pod = self._client.read_namespaced_pod(pod_values[1], pod_values[0])
            pod_info = kube_util.run_checks(self._client, pod)
            if pod_info.can_be_staging():
                self.staging_pod = pod_info

        if not self.staging_pod:
            self.staging_pod = kube_util.find_eligible_staging_pod(
                self._client, self.exclude_namespaces
            )

        if self.staging_pod:
            self.is_connected = True
        self.initializing = False

    def client_connect(self, remote_address, remote_port, client_socket):
        super().client_connect(remote_address, remote_port, client_socket)

        kube_util.setup_staging(
            self._client, self.staging_pod, remote_address, remote_port
        )

        thread = threading.Thread(
            target=self._create_connection,
            args=(self.staging_pod, remote_address, remote_port, client_socket),
        )
        thread.start()

    def _create_connection(
        self,
        pod: StagingPod,
        remote_address: str,
        remote_port: int,
        client_socket: socket.socket,
    ):
        # if not self.__staging_ready:
        #     print("[!!] not forwarding traffic - staging not ready")
        #     return

        k8sclient = client.CoreV1Api()
        fwd = stream(
            k8sclient.connect_post_namespaced_pod_portforward,
            pod.pod_name,
            pod.namespace,
            ports=remote_port,
            _preload_content=False,
            _request_timeout=5.0,
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
                channel_prefix = chr(CHANNEL_STDIN)
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

                channel = data[0]
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

        if fwd.is_open():
            fwd.close()


def load_config(config: dict) -> KubernetesProvider:
    name = config["name"]
    context = config["context"]
    staging_pod = config["stagingPod"] if "stagingPod" in config else None
    exclude_namespaces = (
        config["excludeNamespaces"] if "excludeNamespaces" in config else None
    )

    provider = KubernetesProvider(name, context, staging_pod)
    provider.exclude_namespaces = exclude_namespaces
    return provider
