import hips


def remove(args):
    """Function corresponding to the `remove` subcommand of `hips`."""
    hips.load_and_push_hips(args.path)
    active_hips = hips.get_active_hips()
    print('This would remove: %s' % active_hips['name'])
    hips.pop_active_hips()