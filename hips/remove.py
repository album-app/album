from hips import Hips, get_active_hips


def remove(args):
    """Function corresponding to the `remove` subcommand of `hips`."""
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)
    hips = get_active_hips()

    print('This would remove: %s' % hips['name'])
