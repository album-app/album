"""Operations for urls."""

from __future__ import annotations

import os
import re
import tempfile
from enum import Enum, unique
from pathlib import Path

from album.core.utils.operations.file_operations import check_zip
from album.environments.utils.file_operations import copy
from album.environments.utils.url_operations import _get_session
from album.runner import album_logging

module_logger = album_logging.get_active_logger


def retrieve_redirect_url(url: str) -> str:
    """Retrieve the redirect url."""
    with _get_session() as s:
        r = s.get(url, allow_redirects=True, stream=False)

        if r.status_code != ResponseStatus.OK.value:
            raise ConnectionError("Could not connect to resource %s!" % url)

        return r.url


def is_url(str_input: str) -> bool:
    """Parse a url."""
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


def is_git_ssh_address(str_input: str) -> bool:
    """Parse an ssh address."""
    git_regex = re.compile(
        r"(ssh://){0,1}"  # long ssh address start
        r"[\S]*@"  # user@
        r"[\S]*",  # host and project
        re.IGNORECASE,
    )
    return re.match(git_regex, str_input) is not None


def download(str_input: str, base: str) -> Path:
    """Download a solution file into a temporary file.

    Raises:
        ConnectionError: If the resource does not answer with status 200.

    """
    Path(base).mkdir(exist_ok=True, parents=True)

    with _get_session() as s:
        r = s.get(str_input, allow_redirects=True, stream=True)

        if r.status_code != ResponseStatus.OK.value:
            raise ConnectionError(
                "Could not download resource %s! Server responded with status %s."
                % (str_input, r.status_code)
            )

        fd, tmp_file_name = tempfile.mkstemp(dir=base)
        with os.fdopen(fd, "wb") as out:
            out.write(r.content)
        if check_zip(tmp_file_name):
            fd_zip, tmp_file_name_zip = tempfile.mkstemp(dir=base, suffix=".zip")
            os.close(fd_zip)  # only the name is needed, copy() writes the content
            copy(tmp_file_name, tmp_file_name_zip)
            return Path(tmp_file_name_zip)
        return Path(tmp_file_name)


@unique
class ResponseStatus(Enum):
    """Response values and their name."""

    OK = 200  # response included
    Created = 201  # response included
    Accepted = 202  # response included
    NoContent = 204  # response NOT included
    BadRequest = 400  # error response included
    Unauthorized = 401  # error response included
    Forbidden = 403  # error response included
    NotFound = 404  # error response included
    MethodNotAllowed = 405  # error response included
    Conflict = 409  # error response included
    UnsupportedMediaType = 415  # error response included
    TooManyRequests = 429  # error response included
    InternalServerError = 500  # error NOT response included
