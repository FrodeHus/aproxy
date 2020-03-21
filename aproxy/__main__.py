import sys
import socket
import signal
from .proxy_handler import ProxyHandler

proxy: ProxyHandler = None


def server_loop(local_host, local_port, remote_host, remote_port, receive_first):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((local_host, local_port))
        print("[*] Listening on %s:%d" % (local_host, local_port))
    except Exception as e:
        print("[!!] Failed to listen on %s:%d" % (local_host, local_port))
        print(e)
        sys.exit(0)

    server.listen(5)
    while True:
        client_socket, addr = server.accept()
        print("[==>] Received incoming connection from %s:%d" % (addr[0], addr[1]))
        proxy = ProxyHandler(client_socket, remote_host, remote_port, receive_first)
        proxy.start()


def signal_handler(sig, frame):
    global proxy
    if proxy:
        proxy.stop()
    sys.exit(0)


def main():
    if len(sys.argv[1:]) != 5:
        print(
            "Usage: ./aproxy.py [localhost] [localport] [remotehost] [remoteport] [receive_first]"
        )
        print("Example: ./aproxy.py 127.0.0.1 9000 10.12.13.14 9000 True")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    local_host = sys.argv[1]
    local_port = int(sys.argv[2])
    remote_host = sys.argv[3]
    remote_port = int(sys.argv[4])
    receive_first = sys.argv[5]

    if "True" in receive_first:
        receive_first = True
    else:
        receive_first = False

    server_loop(local_host, local_port, remote_host, remote_port, receive_first)


main()
