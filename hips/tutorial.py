from hips import Hips, get_active_hips


def tutorial(args):
    """Function corresponding to the `tutorial` subcommand of `hips`."""
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)
    hips = get_active_hips()

    print('This would run a tutorial for: %s' % hips['name'])
