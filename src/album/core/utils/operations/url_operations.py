import re
import tempfile
from pathlib import Path

import requests
from album.runner import album_logging
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from album.ci.utils.zenodo_api import ResponseStatus
from album.core.utils.operations.file_operations import (
    create_path_recursively,
    copy,
    check_zip,
)

module_logger = album_logging.get_active_logger


def is_downloadable(url):
    """Shows if url is a downloadable resource."""
    with _get_session() as s:
        h = s.head(url, allow_redirects=True)
        header = h.headers
        content_type = header.get("content-type")
        if "html" in content_type.lower():
            return False
        return True


def download_resource(url, path):
    """Downloads a resource given its url."""
    module_logger().debug("Download url %s to %s..." % (url, path))

    path = Path(path)

    if not is_downloadable(url):
        raise AssertionError('Resource "%s" not downloadable!' % url)

    r = _request_get(url)

    create_path_recursively(path.parent)
    with open(path, "wb") as f:
        for chunk in r:
            f.write(chunk)

    return path


def _get_session():
    s = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)

    adapter = HTTPAdapter(max_retries=retry)

    s.mount("http://", adapter)
    s.mount("https://", adapter)

    return s


def _request_get(url):
    """Get a response from a request to a resource url."""
    with _get_session() as s:
        r = s.get(url, allow_redirects=True, stream=True)

        if r.status_code != ResponseStatus.OK.value:
            raise ConnectionError("Could not connect to resource %s!" % url)

        return r


def retrieve_redirect_url(url):
    with _get_session() as s:
        r = s.get(url, allow_redirects=True, stream=False)

        if r.status_code != ResponseStatus.OK.value:
            raise ConnectionError("Could not connect to resource %s!" % url)

        return r.url


def is_url(str_input: str):
    """Parses a url."""
    url_regex = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return re.match(url_regex, str_input) is not None


def is_git_ssh_address(str_input: str):
    """Parses a ssh address."""
    git_regex = re.compile(
        r"(ssh://){0,1}"  # long ssh address start
        r"[\S]*@"  # user@
        r"[\S]*",  # host and project
        re.IGNORECASE,
    )
    return re.match(git_regex, str_input) is not None


def download(str_input, base):
    """Downloads a solution file into a temporary file."""
    Path(base).mkdir(exist_ok=True, parents=True)

    with _get_session() as s:
        r = s.get(str_input, allow_redirects=True, stream=True)

        new_file, tmp_file_name = tempfile.mkstemp(dir=base)
        with open(tmp_file_name, "wb") as out:
            out.write(r.content)
        if check_zip(tmp_file_name):
            new_file, tmp_file_name_zip = tempfile.mkstemp(dir=base, suffix=".zip")
            copy(tmp_file_name, tmp_file_name_zip)
            return Path(tmp_file_name_zip)
        return Path(tmp_file_name)
