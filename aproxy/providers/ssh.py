from aproxy.providers.provider_config import ProviderConfigItem
import sys
import socket
import paramiko
import threading


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

    def connect(self, remote_address: str, remote_port: int) -> socket.socket:
        super().connect(remote_address, remote_port)
        print("connecting to ssh...")
        self.__remote_address = remote_address
        self.__remote_port = remote_port
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(self.__host, username=self.__user)
            trans: paramiko.Transport = client.get_transport()
            trans.request_port_forward("", 4444)
            trans.open_session()
            provider_server = threading.Thread(
                target=self.__serve_connections, args=(trans,)
            )
            provider_server.start()
        except paramiko.SSHException as err:
            print("Unable to enable reverse port forwarding: {}".format(str(err)))
            sys.exit(1)

    def client_connect(self):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(("127.0.0.1", 4444))
        return client_socket

    def __serve_connections(self, client_transport: paramiko.Transport):
        while True:
            try:
                chan = client_transport.accept(60)
                if not chan:
                    continue
                thread = threading.Thread(
                    target=handler,
                    args=(chan, self.__remote_address, self.__remote_port),
                )
                thread.start()
            except Exception as err:
                client_transport.cancel_port_forward("", 4444)
                client_transport.close()
                print(
                    f"Error occured while proxying to {self.__remote_address}: {str(err)}"
                )


def handler(channel, remote_address, remote_port):
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        remote_socket.connect((remote_address, remote_port))
    except:
        print(f"Unable to connect to {remote_address}:{remote_port}")
        sys.exit(1)


def load_config(config: dict) -> SshProvider:
    user = config["user"] if "user" in config else None
    host = config["host"] if "host" in config else None
    return SshProvider(config["name"], host, user)
