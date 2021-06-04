from hips.core.controller.install_manager import InstallManager
from hips_runner import logging

module_logger = logging.get_active_logger


install_manager = InstallManager()


def install(args):
    install_manager.install(args.path)

