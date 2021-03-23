import hips


def containerize(args):
    """Function corresponding to the `containerize` subcommand of `hips`."""
    # Load HIPS
    active_hips = hips.load_and_push_hips(args.path)
    print('This would containerize: %s' % active_hips['name'])
    hips.pop_active_hips()
