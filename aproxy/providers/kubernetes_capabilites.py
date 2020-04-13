from colorama import Fore
from enum import Enum


class ExecCap(Enum):
    NONE = 0
    LIMITED = 1
    FULL = 2


class KubeCapabilities:
    def __init__(self, user: str):
        super().__init__()
        self.__user = user
        if user and user.find("exec failed") != -1:
            self.__can_exec = ExecCap.LIMITED
            self.__user = None
        elif not user:
            self.__can_exec = ExecCap.NONE
            self.__user = None
        else:
            self.__can_exec = ExecCap.FULL

    def passthrough_ok(self):
        return False

    def __str__(self):
        color = Fore.GREEN
        if self.__can_exec is ExecCap.LIMITED and not self.__user:
            color = Fore.YELLOW
        elif self.__can_exec is ExecCap.NONE:
            color = Fore.RED

        return f"capabilities: [exec: {color}{self.__can_exec.name}{Fore.RESET}]\t[user: {self.__user}]"
