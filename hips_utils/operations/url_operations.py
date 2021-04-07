from pathlib import Path

import requests

from hips_utils import hips_logging
from hips_utils.operations.file_operations import create_path_recursively
from hips_utils.zenodo_api import ResponseStatus

module_logger = hips_logging.get_active_logger


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
    module_logger().debug("Download url %s to %s" % (url, path))

    path = Path(path)

    if not is_downloadable(url):
        raise AssertionError("Resource not downloadable!")

    r = _request_get(url)

    create_path_recursively(path.parent)
    with open(path, "wb") as f:
        for chunk in r:
            f.write(chunk)


# todo: write tests
def _request_get(url):
    r = requests.get(url, allow_redirects=True, stream=True)

    if r.status_code != ResponseStatus.OK.value:
        raise ConnectionError("Could not download resource!")

    return r