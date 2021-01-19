import argparse
from . import *

def main():
    parser = argparse.ArgumentParser(description='Process a HIP Solution')
    subparsers = parser.add_subparsers(help='sub-command help')

    # run
    parser_run = subparsers.add_parser('run', help='run help')
    parser_run.add_argument('path', type=str, help='path for the HIPS file')
    parser_run.set_defaults(func=run)

    # deploy
    # export

    # Parse args then run the respective subcommand
    args = parser.parse_args()
    args.func(args)

    # h = Hips(args)

if __name__ == "__main__":
    main()
