"""Keep a Changelog parser."""
import re
from typing import Any, Dict, Optional
from warnings import warn


def is_release(line: str) -> bool:
    """Check if the line is a release line."""
    return line.startswith("## ")


def add_release(changes: Dict[str, dict], line: str) -> Dict[str, dict]:
    """Add a release to the changes dict."""
    release_line = line[3:].lower().strip(" ")
    # A release is separated by a space between version and release date
    # Release pattern should match lines like: "[0.0.1] - 2020-12-31" or [Unreleased]
    version, release_date = (
        release_line.split(" ", maxsplit=1)
        if " " in release_line
        else (release_line, "")
    )
    _version = unlink(version)

    metadata: Dict[str, Any] = {
        "version": _version,
        "release_date": extract_date(release_date),
    }
    try:
        metadata["semantic_version"] = to_semantic(_version)
    except InvalidSemanticVersion:
        pass

    return changes.setdefault(_version, {"metadata": metadata})


def unlink(value: str) -> str:
    """Remove square brackets from the version string."""
    return value.lstrip("[").rstrip("]")


def extract_date(date: str) -> str:
    """Remove leading and trailing characters from the date string."""
    if not date:
        return date

    return date.lstrip(" -(").rstrip(" )")


# Link pattern should match lines like: "[1.2.3]: https://github.com/user/project/releases/tag/v0.0.1"
link_pattern = re.compile(r"^\[(.*)\]: (.*)$")


def is_link(line: str) -> bool:
    """Check if the line is a link."""
    return link_pattern.fullmatch(line) is not None


def to_raw_dict(changelog_path: str) -> Dict[str, Any]:
    """Convert a changelog file to a raw dictionary."""
    changes: Dict[str, Any] = {}
    # As URLs can be defined before actual usage, maintain a separate dict
    urls = {}
    with open(changelog_path) as change_log:
        current_release: Dict[str, Any] = {"raw": ""}
        for line in change_log:
            clean_line = line.strip(" \n")

            if is_release(clean_line):
                current_release = add_release(changes, clean_line)
            elif is_link(clean_line):
                link_match = link_pattern.fullmatch(clean_line)
                if link_match:
                    urls[link_match.group(1).lower()] = link_match.group(2)
            elif clean_line:
                current_release["raw"] = current_release.get("raw", "") + line
                if "raw" == "":
                    # If there is no changelog, notifiy the user
                    warn(
                        "Your changelog description is empty, so "
                        "the release will state the version number without a description."
                    )

    # Add url for each version (create version if not existing)
    for version, url in urls.items():
        changes.setdefault(version, {"metadata": {"version": version}})["metadata"][
            "url"
        ] = url

    unreleased_version = None
    for version, current_release in changes.items():
        metadata = current_release["metadata"]
        # If there is an empty release date, it identifies the unreleased section
        if ("release_date" in metadata) and not metadata["release_date"]:
            unreleased_version = version

    if changes and unreleased_version:
        changes.pop(unreleased_version, None)

    return changes


initial_semantic_version = {
    "major": 0,
    "minor": 0,
    "patch": 0,
    "prerelease": None,
    "buildmetadata": None,
}


class InvalidSemanticVersion(Exception):
    """Exception raised for invalid semantic version."""

    def __init__(self, version: str):
        """Initialize the exception."""
        super().__init__(
            f"{version} is not following semantic versioning. Check https://semver.org for more information."
        )


semantic_versioning = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:[-\.]?(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"  # noqa: E501
)


def to_semantic(version: Optional[str]) -> Dict[str, Any]:
    """Convert a version string to a semantic version."""
    if not version:
        return initial_semantic_version.copy()

    match = semantic_versioning.fullmatch(version)
    if match:
        return {
            key: int(value) if key in ("major", "minor", "patch") else value
            for key, value in match.groupdict().items()
        }

    raise InvalidSemanticVersion(version)
