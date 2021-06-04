from hips.core.controller.deploy_manager import DeployManager
from hips_runner import logging

module_logger = logging.get_active_logger


deploy_manager = DeployManager()


def deploy(args):
    deploy_manager.deploy(args.path, args.catalog, args.dry_run, args.trigger_pipeline)

