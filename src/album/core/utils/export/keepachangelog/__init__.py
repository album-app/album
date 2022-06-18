import re
from typing import Dict
from typing import Optional


def is_release(line: str) -> bool:
    return line.startswith("## ")


def add_release(changes: Dict[str, dict], line: str) -> dict:
    release_line = line[3:].lower().strip(" ")
    # A release is separated by a space between version and release date
    # Release pattern should match lines like: "[0.0.1] - 2020-12-31" or [Unreleased]
    version, release_date = (
        release_line.split(" ", maxsplit=1)
        if " " in release_line
        else (release_line, None)
    )
    version = unlink(version)

    metadata = {"version": version, "release_date": extract_date(release_date)}
    try:
        metadata["semantic_version"] = to_semantic(version)
    except InvalidSemanticVersion:
        pass

    return changes.setdefault(version, {"metadata": metadata})


def unlink(value: str) -> str:
    return value.lstrip("[").rstrip("]")


def extract_date(date: str) -> str:
    if not date:
        return date

    return date.lstrip(" -(").rstrip(" )")


# Link pattern should match lines like: "[1.2.3]: https://github.com/user/project/releases/tag/v0.0.1"
link_pattern = re.compile(r"^\[(.*)\]: (.*)$")


def is_link(line: str) -> bool:
    return link_pattern.fullmatch(line) is not None


def to_raw_dict(changelog_path: str) -> Dict[str, dict]:
    changes = {}
    # As URLs can be defined before actual usage, maintain a separate dict
    urls = {}
    with open(changelog_path) as change_log:
        current_release = {}
        for line in change_log:
            clean_line = line.strip(" \n")

            if is_release(clean_line):
                current_release = add_release(changes, clean_line)
            elif is_link(clean_line):
                link_match = link_pattern.fullmatch(clean_line)
                urls[link_match.group(1).lower()] = link_match.group(2)
            elif clean_line:
                current_release["raw"] = current_release.get("raw", "") + line

    # Add url for each version (create version if not existing)
    for version, url in urls.items():
        changes.setdefault(version, {"metadata": {"version": version}})["metadata"][
            "url"
        ] = url

    unreleased_version = None
    for version, current_release in changes.items():
        metadata = current_release["metadata"]
        # If there is an empty release date, it identify the unreleased section
        if ("release_date" in metadata) and not metadata["release_date"]:
            unreleased_version = version

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
    def __init__(self, version: str):
        super().__init__(
            f"{version} is not following semantic versioning. Check https://semver.org for more information."
        )


semantic_versioning = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:[-\.]?(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def to_semantic(version: Optional[str]) -> dict:
    if not version:
        return initial_semantic_version.copy()

    match = semantic_versioning.fullmatch(version)
    if match:
        return {
            key: int(value) if key in ("major", "minor", "patch") else value
            for key, value in match.groupdict().items()
        }

    raise InvalidSemanticVersion(version)
