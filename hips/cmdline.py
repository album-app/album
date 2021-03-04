import sys
import argparse
from hips import hips_debug
from hips.deploy import deploy
from hips.run import run
from hips.repl import repl
from hips.search import search
from hips.install import install
from hips.remove import remove
from hips.containerize import containerize
from hips.tutorial import tutorial

import logging
from utils import hips_logging


module_logger = logging.getLogger('hips')


def main():
    """Entry points of `hips`."""

    # retrieve logger
    hips_logging.configure_logging(hips_logging.LogLevel(hips_debug()), 'hips')

    # parent parser all inherit
    parent_parser = argparse.ArgumentParser(add_help=False)

    # parse logging
    parent_parser.add_argument(
        '--log',
        required=False,
        help='Logging level for your hips command. Choose between %s' %
             ", ".join([loglevel.name for loglevel in hips_logging.LogLevel]),
        default='INFO',
        type=(lambda choice: hips_logging.to_loglevel(choice, 'hips')),
    )

    # hips parser
    parser = argparse.ArgumentParser(
        add_help=False,
        description=
        'Helmholtz Imaging Platform (HIP) Solutions framework for running, building, and deploying generalized imaging solutions'
    )

    # hips command subparser
    subparsers = parser.add_subparsers(title='actions', help='sub-command help')

    # run
    parser_run = subparsers.add_parser('run', help='run a HIP Solution', parents=[parent_parser])
    parser_run.add_argument('path', type=str, help='path for the HIPS file')
    parser_run.set_defaults(func=run)

    # repl
    parser_repl = subparsers.add_parser(
        'repl', help='get an interactive repl for a HIP Solution', parents=[parent_parser])
    parser_repl.add_argument('path', type=str, help='path for the HIPS file')
    parser_repl.set_defaults(func=repl)

    # deploy
    parser_deploy = subparsers.add_parser('deploy',
                                          help='deploy a HIP Solution', parents=[parent_parser])
    parser_deploy.add_argument('path', type=str, help='path for the HIPS file')
    parser_deploy.set_defaults(func=deploy)

    # search
    parser_search = subparsers.add_parser(
        'search', help='search for a HIP Solution using keywords', parents=[parent_parser])
    parser_search.set_defaults(func=search)

    # install
    parser_install = subparsers.add_parser('install',
                                           help='install a HIP Solution', parents=[parent_parser])
    parser_install.add_argument('path',
                                type=str,
                                help='path for the HIPS file')
    parser_install.set_defaults(func=install)

    # remove
    parser_remove = subparsers.add_parser('remove',
                                          help='remove a HIP Solution', parents=[parent_parser])
    parser_remove.add_argument('path', type=str, help='path for the HIPS file')
    parser_remove.set_defaults(func=remove)

    # containerize
    parser_containerize = subparsers.add_parser(
        'containerize',
        help='create a Singularity container for a HIP Solution', parents=[parent_parser])
    parser_containerize.add_argument('path',
                                     type=str,
                                     help='path for the HIPS file')
    parser_containerize.set_defaults(func=containerize)

    # tutorial
    parser_tutorial = subparsers.add_parser(
        'tutorial', help='run a tutorial for a HIP Solution', parents=[parent_parser])
    parser_tutorial.add_argument('path',
                                 type=str,
                                 help='path for the HIPS file')
    parser_tutorial.set_defaults(func=tutorial)

    # ToDo: clean all hips environments

    module_logger.debug('Parsing base hips call arguments...')
    args = parser.parse_known_args(sys.argv[1:])

    # switch to desired logging level
    hips_logging.set_loglevel(args[0].log, 'hips')

    module_logger.debug("Running %s subcommand..." % sys.argv[1])
    sys.argv = args[1]  # unparsed arguments belonging to solution
    args[0].func(args[0])


if __name__ == "__main__":
    main()
