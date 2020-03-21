import socket, threading
from enum import Enum
import hexdump
from colorama import Fore


class Direction(Enum):
    LOCAL = 0
    REMOTE = 1


class ProxyHandler:
    def __init__(
        self,
        client_socket,
        remote_host,
        remote_port,
        receive_first,
        dump_data: bool = True,
    ):
        super().__init__()
        self.__local = client_socket
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((remote_host, remote_port))
        self.__remote = remote_socket
        self.__dump_data = dump_data
        self.__rec_first = receive_first

    def start(self):
        self.__thread = threading.Thread(target=self.__proxy_loop)
        self.__thread.start()

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
        while True:
            self.__handle_traffic(Direction.LOCAL)
            self.__handle_traffic(Direction.REMOTE)

    def __handle_traffic(self, direction: Direction):
        if direction == Direction.LOCAL:
            receiver, sender = self.__local, self.__remote
        else:
            receiver, sender = self.__remote, self.__local

        buffer = self.__receive_from(receiver)
        self.__print_info(buffer, direction)

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
            print(
                "{} Sent to {}".format(
                    self.__get_direction_label(direction), outgoing.name
                )
            )

    def stop(self):
        self.__local.close()
        self.__remote.close()
        self.__thread._stop()

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
        if self.__dump_data:
            print(
                self.__get_direction_label(direction)
                + color
                + " Received {} bytes of data from {}".format(
                    str(len(buffer)), direction.name
                )
            )
            hexdump.hexdump(buffer)
            print(Fore.RESET)

    def __receive_from(self, connection: socket):
        buffer = b""
        connection.settimeout(0.2)
        try:
            bytes_recvd = 0
            while bytes_recvd < 4096:
                chunk = connection.recv(min(4096 - bytes_recvd, 2048))
                bytes_recvd = bytes_recvd + len(chunk)
                if not chunk:
                    break
                buffer += chunk
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
