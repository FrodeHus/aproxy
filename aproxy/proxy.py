import socket, threading, sys, json
from enum import Enum
import hexdump
from colorama import Fore
import select

running_proxies = {}
stop_proxies = False


class Direction(Enum):
    LOCAL = 0
    REMOTE = 1


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
    with open(configFile, "r") as cfg:
        config = json.load(cfg)
    print("Loaded config for {} proxies".format(len(config["proxies"])))
    for proxy in config["proxies"]:
        dump_data = True if "dumpData" in proxy and proxy["dumpData"] else False

        thread = threading.Thread(
            target=start_proxy,
            args=(
                proxy["localPort"],
                proxy["remoteAddress"],
                proxy["remotePort"],
                proxy["localAddress"],
                False,
                dump_data,
            ),
        )
        thread.start()


def start_proxy(
    local_port: int,
    remote_host: str,
    remote_port: int,
    local_host: str = "0.0.0.0",
    receive_first: bool = False,
    dump_data: bool = False,
):
    global running_proxies
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((local_host, local_port))
        print("[*] Listening on %s:%d" % (local_host, local_port))
    except Exception as e:
        print("[!!] Failed to listen on %s:%d" % (local_host, local_port))
        print(e)
        sys.exit(0)

    server.listen(5)
    global stop_proxies
    while not stop_proxies:
        client_socket, addr = server.accept()
        print("[==>] Received incoming connection from %s:%d" % (addr[0], addr[1]))
        proxy = Proxy(client_socket, remote_host, remote_port, receive_first, dump_data)
        proxy.start()
        running_proxies[proxy.name] = proxy


class Proxy:
    def __init__(
        self,
        client_socket: socket.socket,
        remote_host: str,
        remote_port: int,
        receive_first: bool,
        dump_data: bool = True,
    ):
        super().__init__()

        self.name = "{}->{}:{}".format(
            client_socket.getsockname(), remote_host, remote_port
        )
        self.__local = client_socket
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((remote_host, remote_port))

        self.__remote = remote_socket
        self.__dump_data = dump_data
        self.__rec_first = receive_first
        self.__stop = False

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
        self.__receive_first(self.__rec_first)
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
        rdy_read = []
        if direction == Direction.LOCAL:
            receiver, sender = self.__local, self.__remote
            try:
                rdy_read, _, _ = select.select([receiver,], [], [])
            except select.error:
                self.stop()
                return
        else:
            receiver, sender = self.__remote, self.__local

        if not rdy_read or len(rdy_read) > 0:
            buffer = self.__receive_from(receiver)

        self.__print_info(buffer, direction)
        handler = (
            self.__request_handler
            if direction == Direction.LOCAL
            else self.__response_handler
        )

        buffer = handler(buffer)
        try:
            sender.send(buffer)
            if len(buffer):
                outgoing = (
                    Direction.LOCAL
                    if direction is Direction.REMOTE
                    else Direction.REMOTE
                )
                print(
                    "{} Sent to {}".format(
                        self.__get_direction_label(direction), outgoing.name
                    )
                )
        except:
            pass

    def __get_direction_label(self, direction: Direction):
        if direction == Direction.LOCAL:
            label = "==>"
        else:
            label = "<=="
        label = "[{}{}{}]".format(Fore.GREEN, label, Fore.RESET)
        return label

    def __print_info(self, buffer: str, direction: Direction):
        if not len(buffer):
            return
        label = self.__get_direction_label(direction)
        color = Fore.CYAN if direction is Direction.LOCAL else Fore.YELLOW
        print(
            self.__get_direction_label(direction)
            + color
            + " Received {} bytes of data from {}".format(
                str(len(buffer)), direction.name
            )
        )
        if self.__dump_data:
            hexdump.hexdump(buffer)

        print(Fore.RESET)

    def __receive_from(self, connection: socket):
        buffer = b""
        if not connection:
            return buffer

        MSG_LEN = 4096
        connection.settimeout(0.1)
        try:

            bytes_recvd = 0
            while bytes_recvd < MSG_LEN:
                chunk = connection.recv(min(MSG_LEN - bytes_recvd, 1024))
                if not chunk:
                    break

                bytes_recvd = bytes_recvd + len(chunk)
                buffer += chunk

        except socket.timeout:
            pass
        except socket.error as e:
            print(Fore.RED + e + Fore.RESET)
            pass
        if not len(buffer):
            self.stop()
        return buffer

    def __disconnected(self, connection: socket):
        try:
            rdy_read, rdy_write, sock_err = select.select([connection,], [], [])
            return len(rdy_read) == 0
        except select.error:
            return True
        except:
            return True

    def __request_handler(self, buffer: str):
        # perform any modifications bound for the remote host here
        return buffer

    def __response_handler(self, buffer: str):
        # perform any modifictions bound for the local host here
        return buffer
