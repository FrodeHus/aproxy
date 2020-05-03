import socket, threading, sys, json
from enum import Enum
import hexdump
from colorama import Fore
import select
from .util import Direction, print_info, get_direction_label
from .proxy_config import load_config, ProxyConfig, ProxyItem
import time
from select import poll

running_proxies = {}
stop_proxies = False
config: ProxyConfig = None


def signal_handler(sig, frame):
    global running_proxies
    global stop_proxies

    if running_proxies:
        for proxy in running_proxies.values():
            proxy.stop()
        running_proxies.clear()
    stop_proxies = True
    sys.exit(0)


def start_from_config(configFile: str):
    global config
    config = load_config(configFile)

    print("[*] loaded config for {} proxies".format(len(config.proxies)))
    for proxy in config.proxies:
        thread = threading.Thread(target=start_proxy, args=(proxy,))
        thread.start()


def start_single_proxy(
    local_port: int,
    remote_port: int,
    remote_host: str,
    local_host: str = None,
    verbosity: int = 0,
):
    cfg = ProxyItem(
        local_host, local_port, remote_host, remote_port, "SingleHost", verbosity
    )
    start_proxy(cfg)


def start_proxy(proxy_config: ProxyItem):
    global running_proxies
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    remote_socket: socket.socket = None
    try:
        provider_config = config.providers[proxy_config.provider]
        provider = provider_config.provider
        if provider_config.depends_on and not provider.is_connected:
            print(
                f"[*] [{proxy_config.name}] checking that dependencies are met before connecting"
            )
            if not all(
                elem in config.providers["initialized"]
                for elem in provider_config.depends_on
            ):
                print(
                    f"[!!] [{proxy_config.name}] not all dependencies are initialized"
                )
                sys.exit(1)
            if not provider.initializing:
                provider.connect()
            else:
                print(
                    f"[*] [{proxy_config.name}] waiting for provider {provider.name} to finish initializing"
                )

        while provider.initializing:
            time.sleep(1)

        server.bind((proxy_config.local_host, proxy_config.local_port))
        print(f"[*] Listening on {proxy_config.local_host}:{proxy_config.local_port}")

    except Exception as e:
        print(
            f"[!!] Failed to listen on {proxy_config.local_host}:{proxy_config.local_port}: {str(e)}"
        )
        print(e)
        sys.exit(0)

    server.listen()
    global stop_proxies
    while not stop_proxies:
        client_socket, addr = server.accept()
        proxy = Proxy(client_socket, proxy_config, remote_socket)
        proxy.start()
        running_proxies[proxy.name] = proxy


class Proxy:
    def __init__(
        self,
        client_socket: socket.socket,
        config: ProxyItem,
        remote_host: socket.socket = None,
    ):
        super().__init__()

        self.name = "{}->{}:{}".format(
            client_socket.getsockname(), config.remote_host, config.remote_port
        )
        self._local = client_socket
        self._config = config
        self._stop = False
        if remote_host:
            self.__remote = remote_host
        else:
            self._remote_connect()

    def start(self):
        self._thread = threading.Thread(target=self._proxy_loop)
        self._thread.start()

    def stop(self):
        if self.__stop:
            return

        self._stop = True
        if self.__local:
            self._local.close()
            self._local = None

        if self.__remote:
            self.__remote.close()
            self.__remote = None

        print(Fore.MAGENTA + "Disconnected " + self.name + Fore.RESET)

    def _remote_connect(self):
        global config
        if self.__config.provider:
            provider_config = config.providers[self._config.provider]
            provider = provider_config.provider
            if not provider.is_connected:
                print("[*] connection was deferred - connecting to provider now...")
                provider.connect()

            self.__remote = provider.client_connect(
                self._config.remote_host, self._config.remote_port, self._local
            )
        else:
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((self._config.remote_host, self._config.remote_port))
            self.__remote = remote_socket

    def _proxy_loop(self):
        poller = poll()
        poller.register(self._local, select.POLLIN)
        poller.register(self.__remote, select.POLLIN)
        try:
            while True:
                if self.__stop or not self.__remote or not self.__local:
                    break
                r, w, x = select.select([self._local, self.__remote], [], [], 5.0)
                # channels = poller.poll(5.0)
                if self.__local in r:
                    data = self._local.recv(1024)
                    if len(data) == 0:
                        break
                    print_info(data, Direction.REMOTE, self._config)
                    self.__remote.send(data)
                if self.__remote in r:
                    data = self.__remote.recv(1024)
                    if len(data) == 0:
                        break
                    print_info(data, Direction.LOCAL, self._config)
                    self._local.send(data)
        except Exception:
            import traceback

            print(traceback.format_exc())

    def _request_handler(self, buffer: str):
        # perform any modifications bound for the remote host here
        return buffer

    def _response_handler(self, buffer: str):
        # perform any modifictions bound for the local host here
        return buffer
