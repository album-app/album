from pathlib import Path
from urllib.parse import urlparse

from album.core.utils.operations.file_operations import write_dict_to_yml

from album.runner import album_logging

module_logger = album_logging.get_active_logger


def get_ssh_url(project_path, server_http_url):
    parsed_url = urlparse(server_http_url)

    ssh_url = "git@%s:%s" % (parsed_url.netloc, project_path)

    module_logger().debug("Set remote URL to %s..." % ssh_url)

    return ssh_url


def create_report(report_file: Path, report_vars: dict) -> Path:
    write_dict_to_yml(report_file, report_vars)

    return report_file
