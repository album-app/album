import sys
import argparse
from hips.deploy import deploy
from hips.run import run
from hips.repl import repl
from hips.search import search
from hips.install import install
from hips.remove import remove
from hips.containerize import containerize
from hips.tutorial import tutorial


def main():
    """Entry points of `hips`."""
    parser = argparse.ArgumentParser(
        description=
        'Helmholtz Imaging Platform (HIP) Solutions framework for running, building, and deploying generalized imaging solutions'
    )
    subparsers = parser.add_subparsers(help='sub-command help')

    # run
    parser_run = subparsers.add_parser('run', help='run a HIP Solution')
    parser_run.add_argument('path', type=str, help='path for the HIPS file')
    parser_run.set_defaults(func=run)

    # repl
    parser_repl = subparsers.add_parser(
        'repl', help='get an interactive repl for a HIP Solution')
    parser_repl.add_argument('path', type=str, help='path for the HIPS file')
    parser_repl.set_defaults(func=repl)

    # deploy
    parser_deploy = subparsers.add_parser('deploy',
                                          help='deploy a HIP Solution')
    parser_deploy.add_argument('path', type=str, help='path for the HIPS file')
    parser_deploy.set_defaults(func=deploy)

    # search
    parser_search = subparsers.add_parser(
        'search', help='search for a HIP Solution using keywords')
    parser_search.set_defaults(func=search)

    # install
    parser_install = subparsers.add_parser('install',
                                           help='install a HIP Solution')
    parser_install.add_argument('path',
                                type=str,
                                help='path for the HIPS file')
    parser_install.set_defaults(func=install)

    # remove
    parser_remove = subparsers.add_parser('remove',
                                          help='remove a HIP Solution')
    parser_remove.add_argument('path', type=str, help='path for the HIPS file')
    parser_remove.set_defaults(func=remove)

    # containerize
    parser_containerize = subparsers.add_parser(
        'containerize',
        help='create a Singularity container for a HIP Solution')
    parser_containerize.add_argument('path',
                                     type=str,
                                     help='path for the HIPS file')
    parser_containerize.set_defaults(func=containerize)

    # tutorial
    parser_tutorial = subparsers.add_parser(
        'tutorial', help='run a tutorial for a HIP Solution')
    parser_tutorial.add_argument('path',
                                 type=str,
                                 help='path for the HIPS file')
    parser_tutorial.set_defaults(func=tutorial)

    # ToDo: clean all hips environments

    # Parse args at the "hips" level
    args = parser.parse_args(sys.argv[1:3])

    # Run the respective subcommand
    sys.argv = sys.argv[2:]
    args.func(args)

    # h = Hips(args)


if __name__ == "__main__":
    main()
