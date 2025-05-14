from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict
from album.environments.utils.file_operations import write_dict_to_yml
from album.runner import album_logging

module_logger = album_logging.get_active_logger


def get_ssh_url(project_path: str, server_http_url : str) -> str:
    parsed_url = urlparse(server_http_url)

    ssh_url = "git@%s:%s" % (parsed_url.netloc, project_path)

    module_logger().debug("Set remote URL to %s..." % ssh_url)

    return ssh_url


def create_report(report_file: Path, report_vars: Dict[str, Any]) -> Path:
    write_dict_to_yml(report_file, report_vars)

    return report_file
