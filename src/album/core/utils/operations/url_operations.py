import re
import shutil
import tempfile
from pathlib import Path
from urllib import request

import requests

from album.ci.utils.zenodo_api import ResponseStatus
from album.core.utils.operations.file_operations import create_path_recursively
from album.runner import logging

module_logger = logging.get_active_logger


def is_downloadable(url):
    """Shows if url is a downloadable resource."""
    h = requests.head(url, allow_redirects=True)
    header = h.headers
    content_type = header.get('content-type')
    if 'html' in content_type.lower():
        return False
    return True


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


def _request_get(url):
    """Get a response from a request to a resource url."""
    r = requests.get(url, allow_redirects=True, stream=True)

    if r.status_code != ResponseStatus.OK.value:
        raise ConnectionError("Could not connect to resource %s!" % url)

    return r


def retrieve_redirect_url(url):
    r = requests.get(url, allow_redirects=True, stream=False)

    if r.status_code != ResponseStatus.OK.value:
        raise ConnectionError("Could not connect to resource %s!" % url)

    return r.url


def is_url(str_input: str):
    """Parses a url."""
    url_regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(url_regex, str_input) is not None


def download(str_input, base):
    """Downloads a solution file into a temporary file."""
    Path(base).mkdir(exist_ok=True, parents=True)
    new_file, file_name = tempfile.mkstemp(dir=base)
    with request.urlopen(str_input) as response, open(file_name, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    return Path(file_name)
