import sys
import socket
import signal
import os
from .proxy import Proxy, signal_handler
from knack import CLI
from knack.commands import CLICommandsLoader, CommandGroup
from knack.arguments import ArgumentsContext, CLIArgumentType


class CommandLoader(CLICommandsLoader):
    def load_command_table(self, args):
        with CommandGroup(self, "proxy", "aproxy.proxy#{}") as g:
            g.command("single", "start_proxy")
            g.command("start", "start_from_config")
        return super(CommandLoader, self).load_command_table(args)

    def load_arguments(self, command):
        with ArgumentsContext(self, "proxy single") as ac:
            ac.argument("local_port", type=int)
            ac.argument("remote_port", type=int)
        return super(CommandLoader, self).load_arguments(command)


name = "aproxy"
cli = CLI(
    cli_name=name,
    config_dir=os.path.expanduser(os.path.join("~", ".{}".format(name))),
    config_env_var_prefix=name,
    commands_loader_cls=CommandLoader,
)
signal.signal(signal.SIGINT, signal_handler)

exit_code = cli.invoke(sys.argv[1:])
sys.exit(exit_code)
