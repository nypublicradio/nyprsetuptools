import sys
from argparse import ArgumentParser, SUPPRESS
from setuptools.dist import Distribution

from nyprsetuptools import DockerDeploy, LambdaDeploy


def make_command(CommandClass):
    dist = Distribution()
    cmd = CommandClass(dist)

    for long_opt, short_opt, help_text in cmd.user_options:
        if long_opt.endswith('='):
            action = 'store'
            default = None
        else:
            action = 'store_true'
            default = False
        long_opt = '--{}'.format(long_opt.rstrip('='))

        if short_opt:
            short_opt = '-{}'.format(short_opt)

        opts = filter(None, [short_opt, long_opt])
        yield (opts, help_text, action, default)


def make_cli(command_classes):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    for cls in command_classes:
        subparser = subparsers.add_parser(cls.__name__)
        subparser.add_argument('--cls', help=SUPPRESS, default=cls)
        for opts, help_text, action, default in make_command(cls):
            subparser.add_argument(*opts, help=help_text, action=action,
                                   default=default)
    args = parser.parse_args()
    if not args.__dict__:
        sys.exit(parser.print_help())
    return args.__dict__


def run_cmd():
    classes = [DockerDeploy, LambdaDeploy]
    args = make_cli(classes)
    dist = Distribution()
    cls = args.pop('cls')
    cmd = cls(dist)

    cmd.initialize_options()
    for key, value in args.items():
        if value:
            setattr(cmd, key, value)
    cmd.finalize_options()
    cmd.run()
