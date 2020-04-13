from colorama import Fore
from enum import Enum
import hexdump
from .proxy_config import ProxyItem


class Direction(Enum):
    LOCAL = 0
    REMOTE = 1


def get_direction_label(
    direction: Direction, textLabel: str = None, config: ProxyItem = None
):
    if direction == Direction.LOCAL:
        label = "==>"
    else:
        label = "<=="
    label = f"[{textLabel} {Fore.GREEN}{label}{Fore.RESET}]"
    if config and config.provider:
        label = (
            label
            + f" {Fore.YELLOW}({Fore.RESET}{config.provider}{Fore.YELLOW}){Fore.RESET}"
        )
    return label


def print_info(buffer: str, direction: Direction, config: ProxyItem):
    if config.verbosity == 0:
        return
    if not len(buffer):
        return
    label = get_direction_label(direction, config)
    color = Fore.CYAN if direction is Direction.LOCAL else Fore.YELLOW
    print(
        get_direction_label(direction, config.name, config)
        + color
        + f" Received {str(len(buffer))} bytes of data from {direction.name}"
    )

    if config.verbosity > 2:
        hexdump.hexdump(buffer)

    print(Fore.RESET)
