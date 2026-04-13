"""Utility functions for continuous integration processes in Album."""

from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

from album.environments.utils.file_operations import write_dict_to_yml
from album.runner import album_logging

module_logger = album_logging.get_active_logger


def get_ssh_url(project_path: str, server_http_url: str) -> str:
    """Convert an HTTP URL to an SSH URL for Git operations."""
    parsed_url = urlparse(server_http_url)

    ssh_url = f"git@{parsed_url.netloc}:{project_path}"

    module_logger().info(f"Converted HTTP URL to SSH: {server_http_url} → {ssh_url}")

    return ssh_url


def create_report(report_file: Path, report_vars: Dict[str, Any]) -> Path:
    """Create a report file in yml format with the provided variables."""
    module_logger().info(
        "Writing report to %s with keys: %s"
        % (report_file, ", ".join(report_vars.keys()))
    )
    write_dict_to_yml(report_file, report_vars)

    return report_file
