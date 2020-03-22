from colorama import Fore
from enum import Enum
import hexdump
from .proxy_config import ProxyItem


class Direction(Enum):
    LOCAL = 0
    REMOTE = 1


def get_direction_label(direction: Direction, textLabel: str = None):
    if direction == Direction.LOCAL:
        label = "==>"
    else:
        label = "<=="
    label = "[{} {}{}{}]".format(textLabel, Fore.GREEN, label, Fore.RESET)
    return label


def print_info(buffer: str, direction: Direction, config: ProxyItem):
    if config.verbosity == 0:
        return
    if not len(buffer):
        return
    label = get_direction_label(direction)
    color = Fore.CYAN if direction is Direction.LOCAL else Fore.YELLOW
    print(
        get_direction_label(direction, config.name)
        + color
        + " Received {} bytes of data from {}".format(str(len(buffer)), direction.name)
    )
    if config.verbosity > 2:
        hexdump.hexdump(buffer)

    print(Fore.RESET)
