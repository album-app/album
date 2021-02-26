from hips import Hips, get_active_hips


def containerize(args):
    """Function corresponding to the `containerize` subcommand of `hips`."""
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)
    hips = get_active_hips()

    print('This would containerize: %s' % hips['name'])
