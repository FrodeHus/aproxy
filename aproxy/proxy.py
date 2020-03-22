import socket, threading, sys, json
from enum import Enum
import hexdump
from colorama import Fore
import select
from .util import Direction, print_info, get_direction_label
from .proxy_config import load_config, ProxyConfig, ProxyItem

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
    config = load_config(configFile)

    print("Loaded config for {} proxies".format(len(config.proxies)))
    for proxy in config.proxies:
        thread = threading.Thread(target=start_proxy, args=(proxy,))
        thread.start()


def start_proxy(config: ProxyItem):
    global running_proxies
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((config.local_host, config.local_port))
        print("[*] Listening on %s:%d" % (config.local_host, config.local_port))
    except Exception as e:
        print("[!!] Failed to listen on %s:%d" % (config.local_host, config.local_port))
        print(e)
        sys.exit(0)

    server.listen()
    global stop_proxies
    while not stop_proxies:
        client_socket, addr = server.accept()
        print("[==>] Received incoming connection from %s:%d" % (addr[0], addr[1]))
        proxy = Proxy(client_socket, config)
        proxy.start()
        running_proxies[proxy.name] = proxy


class Proxy:
    def __init__(self, client_socket: socket.socket, config: ProxyItem):
        super().__init__()

        self.name = "{}->{}:{}".format(
            client_socket.getsockname(), config.remote_host, config.remote_port
        )
        self.__local = client_socket
        self.__config = config
        self.__stop = False
        self.__remote_connect()

    def start(self):
        self.__thread = threading.Thread(target=self.__proxy_loop)
        self.__thread.start()

    def stop(self):
        if self.__stop:
            return

        self.__stop = True
        if self.__local:
            self.__local.close()
            self.__local = None

        if self.__remote:
            self.__remote.close()
            self.__remote = None

        print(Fore.MAGENTA + "Disconnected " + self.name + Fore.RESET)

    def __remote_connect(self):
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((self.__config.remote_host, self.__config.remote_port))
        self.__remote = remote_socket

    def __receive_first(self, receive_first):
        if receive_first:
            remote_buffer = self.__receive_from(self.__remote)
            if self.__dump_data:
                hexdump(remote_buffer)
            remote_buffer = self.__response_handler(remote_buffer)
            if len(remote_buffer):
                print(
                    "[<==] Receiving {} bytes for localhost".format(
                        str(len(remote_buffer))
                    )
                )
                self.__local.send(remote_buffer)

    def __proxy_loop(self):
        self.__receive_first(self.__config.receive_first)
        try:
            while True:
                if self.__stop:
                    break
                self.__handle_traffic(Direction.LOCAL)
                self.__handle_traffic(Direction.REMOTE)
        except Exception:
            import traceback

            print(traceback.format_exc())

    def __handle_traffic(self, direction: Direction):
        if direction == Direction.LOCAL:
            receiver, sender = self.__local, self.__remote
        else:
            receiver, sender = self.__remote, self.__local

        buffer = self.__receive_from(receiver)

        print_info(buffer, direction, self.__config.dump_data)
        handler = (
            self.__request_handler
            if direction == Direction.LOCAL
            else self.__response_handler
        )

        buffer = handler(buffer)
        sender.send(buffer)
        if len(buffer):
            outgoing = (
                Direction.LOCAL if direction is Direction.REMOTE else Direction.REMOTE
            )
            print("{} Sent to {}".format(get_direction_label(direction), outgoing.name))

    def __receive_from(self, connection: socket):
        buffer = b""
        if not connection:
            return buffer

        connection.settimeout(0.1)
        try:

            while True:
                chunk = connection.recv(4096)
                if not chunk:
                    break

                buffer += chunk
            if not len(buffer):
                self.stop()

        except socket.timeout:
            pass
        except socket.error as e:
            print(Fore.RED + e + Fore.RESET)
            pass
        return buffer

    def __request_handler(self, buffer: str):
        # perform any modifications bound for the remote host here
        return buffer

    def __response_handler(self, buffer: str):
        # perform any modifictions bound for the local host here
        return buffer
