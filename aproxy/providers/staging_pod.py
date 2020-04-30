from colorama import Fore
from enum import Enum


class ExecCap(Enum):
    NONE = 0
    LIMITED = 1
    FULL = 2


class PackageManager(Enum):
    NONE = 0
    APK = 1
    APT = 2
    YUM = 3
    ZYPP = 4
    EMERGE = 5


class StagingPod:
    def __init__(
        self, user: str, package_manager: str, utils: [], pod_name: str, namespace: str
    ):
        super().__init__()
        self.package_manager = (
            PackageManager[package_manager.upper()]
            if package_manager
            else PackageManager.NONE
        )
        self.pod_name = pod_name
        self.namespace = namespace
        self.utils = utils
        self.user = user
        if user and user.find("exec failed") != -1:
            self.can_exec = ExecCap.LIMITED
            self.user = None
        elif not user:
            self.can_exec = ExecCap.NONE
            self.user = None
        else:
            self.can_exec = ExecCap.FULL

    def passthrough_ok(self):
        return False

    def can_be_staging(self):
        return (
            self.can_exec is ExecCap.FULL
            and self.user == "root"
            and (
                (self.utils and "socat" in self.utils)
                or self.package_manager != PackageManager.NONE
            )
        )

    def has_dependencies_installed(self):
        return self.utils and "socat" in self.utils

    def __str__(self):
        color = Fore.GREEN
        if self.can_exec is ExecCap.LIMITED and not self.user:
            color = Fore.YELLOW
        elif self.can_exec is ExecCap.NONE:
            color = Fore.RED

        return f"{self.namespace}/{self.pod_name} [exec: {color}{self.can_exec.name}{Fore.RESET}]\t[user: {self.user}]\t[pkg_mgr: {self.package_manager.name}]\t[utils: {self.utils}]"
