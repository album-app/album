from hips_runner import logging
from hips.core.model.server import HipsServer

module_logger = logging.get_active_logger


def start_server(args):
    HipsServer(args.port).start()

