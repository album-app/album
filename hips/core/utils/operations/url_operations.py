from pathlib import Path

import requests

from hips_runner import logging
from hips.core.utils.operations.file_operations import create_path_recursively
from hips.ci.zenodo_api import ResponseStatus

module_logger = logging.get_active_logger


# todo: write tests
def is_downloadable(url):
    """Shows if url is a downloadable resource."""
    h = requests.head(url, allow_redirects=True)
    header = h.headers
    content_type = header.get('content-type')
    if 'html' in content_type.lower():
        return False
    return True


# todo: write tests
def download_resource(url, path):
    """Downloads a resource given its url."""
    module_logger().debug("Download url %s to %s..." % (url, path))

    path = Path(path)

    if not is_downloadable(url):
        raise AssertionError("Resource \"%s\" not downloadable!" % url)

    r = _request_get(url)

    create_path_recursively(path.parent)
    with open(path, "wb") as f:
        for chunk in r:
            f.write(chunk)

    return path


# todo: write tests
def _request_get(url):
    """Get a response from a request to a resource url."""
    r = requests.get(url, allow_redirects=True, stream=True)

    if r.status_code != ResponseStatus.OK.value:
        raise ConnectionError("Could not connect to resource %s!" % url)

    return r
