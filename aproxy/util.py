from colorama import Fore
from enum import Enum
import hexdump


class Direction(Enum):
    LOCAL = 0
    REMOTE = 1


def get_direction_label(direction: Direction):
    if direction == Direction.LOCAL:
        label = "==>"
    else:
        label = "<=="
    label = "[{}{}{}]".format(Fore.GREEN, label, Fore.RESET)
    return label


def print_info(buffer: str, direction: Direction, dump_data: bool):
    if not len(buffer):
        return
    label = get_direction_label(direction)
    color = Fore.CYAN if direction is Direction.LOCAL else Fore.YELLOW
    print(
        get_direction_label(direction)
        + color
        + " Received {} bytes of data from {}".format(str(len(buffer)), direction.name)
    )
    if dump_data:
        hexdump.hexdump(buffer)

    print(Fore.RESET)
