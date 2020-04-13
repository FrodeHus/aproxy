from aproxy.providers.provider_config import ProviderConfigItem
import sys
import socket
import paramiko
import threading
import socketserver


class ForwardServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


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
        self.__ssh_client: socket.socket = None

    def connect(self) -> socket.socket:
        if self.__ssh_client:
            return

        print(f"[*] connecting to ssh {self.__user}:{self.__host}...")
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                self.__host,
                username=self.__user,
                password=self.__password,
                look_for_keys=True,
            )
            self.__ssh_client = client
        except Exception as e:
            print(f"Failed to connect to remote SSH server: {str(e)}")
            sys.exit(1)

    def client_connect(
        self, remote_address: str, remote_port: int, client_socket: socket.socket
    ):
        try:
            transport = self.__ssh_client.get_transport()
            return transport.open_channel(
                "direct-tcpip",
                (remote_address, remote_port),
                client_socket.getpeername(),
            )
        except Exception as e:
            print(f"Failed to open tunnel: {str(e)}")


def load_config(config: dict) -> SshProvider:
    user = config["user"] if "user" in config else None
    host = config["host"] if "host" in config else None
    return SshProvider(config["name"], host, user)
