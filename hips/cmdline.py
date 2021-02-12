import sys
import argparse
from hips.deploy import deploy
from hips.run import run
from hips.repl import repl


def main():
    parser = argparse.ArgumentParser(description='Process a HIP Solution')
    subparsers = parser.add_subparsers(help='sub-command help')

    # run
    parser_run = subparsers.add_parser('run', help='run help')
    parser_run.add_argument('path', type=str, help='path for the HIPS file')
    parser_run.set_defaults(func=run)

    # repl
    parser_repl = subparsers.add_parser('repl', help='repl help')
    parser_repl.add_argument('path', type=str, help='path for the HIPS file')
    parser_repl.set_defaults(func=repl)

    # deploy
    parser_run = subparsers.add_parser('deploy', help='deploy help')
    parser_run.add_argument('path', type=str, help='path for the HIPS file')
    parser_run.set_defaults(func=deploy)

    # Parse args at the "hips" level
    args = parser.parse_args(sys.argv[1:3])

    # Run the respective subcommand
    sys.argv = sys.argv[2:]
    args.func(args)

    # h = Hips(args)


if __name__ == "__main__":
    main()
