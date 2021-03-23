import hips


def tutorial(args):
    """Function corresponding to the `tutorial` subcommand of `hips`."""
    active_hips = hips.load_and_push_hips(args.path)
    print('This would run a tutorial for: %s' % active_hips['name'])
    hips.pop_active_hips()
