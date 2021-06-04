from hips.core.controller.remove_manager import RemoveManager


remove_manager = RemoveManager()


def remove(args):
    remove_manager.remove(args.path, args.remove_deps)


