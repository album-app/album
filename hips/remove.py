import hips


def remove(args):
    """Function corresponding to the `remove` subcommand of `hips`."""
    active_hips = hips.load_and_push_hips(args.path)
    print('This would remove: %s' % active_hips['name'])
    hips.pop_active_hips()