import hips


def containerize(args):
    """Function corresponding to the `containerize` subcommand of `hips`."""
    # Load HIPS
    hips.load_and_push_hips(args.path)
    active_hips = hips.get_active_hips()
    print('This would containerize: %s' % active_hips['name'])
    hips.pop_active_hips()
