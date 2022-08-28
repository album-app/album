from datetime import datetime
from pathlib import Path

from album.core.model.default_values import DefaultValues

from album.core.api.model.catalog import ICatalog
from album.core.utils.export.keepachangelog import to_raw_dict
from album.core.utils.operations.file_operations import create_path_recursively
from album.runner.album_logging import get_active_logger
from album.runner.core.api.model.solution import ISolution


def get_changelog_file_name():
    return DefaultValues.changelog_default_name.value


def get_changelog_content(
    active_solution: ISolution, catalog: ICatalog, dummy_content: str = None
):
    content = """# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
"""
    versions = catalog.get_all_solution_versions(
        active_solution.coordinates().group(), active_solution.coordinates().name()
    )
    for version in versions:
        timestamp = version.setup()["timestamp"]
        if timestamp:
            timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
            time = timestamp.strftime("%Y-%m-%d")
            if (
                version.setup().version == active_solution.setup().version
                and dummy_content
            ):
                change = dummy_content
            else:
                if version.setup()["changelog"]:
                    change = version.setup()["changelog"]
                else:
                    change = ""
            content += "\n## [%s] - %s\n%s\n" % (
                version.setup()["version"],
                time,
                change,
            )
    return content


def create_changelog_file(
    active_solution: ISolution, catalog: ICatalog, target_folder: Path
):
    """Creates a changelog file in the given repo for the given solution.

    Returns:
        The Path to the created markdown file.

    """
    changelog_path = target_folder.joinpath(get_changelog_file_name())
    get_active_logger().debug("Writing changelog file to: %s..." % changelog_path)
    content = get_changelog_content(active_solution, catalog)

    create_path_recursively(changelog_path.parent)
    with open(str(changelog_path), "w+") as yml_f:
        yml_f.write(content)

    return changelog_path


def process_changelog_file(
    catalog: ICatalog, active_solution: ISolution, deploy_path: Path
):
    """Sets the changelog of a given solution."""
    changelog_name = get_changelog_file_name()
    changelog_file = Path(deploy_path).joinpath(changelog_name)

    if changelog_file.exists():
        # process existing changelog file
        changelogs = to_raw_dict(str(changelog_file))
        keyword = str(active_solution.setup().version).lower()
        if keyword in changelogs:
            active_solution.setup().changelog = changelogs[keyword]["raw"]
    else:
        # no changelog file found
        if not active_solution.setup().changelog:
            content = get_changelog_content(
                active_solution, catalog, "- INSERT LIST OF CHANGES"
            )
            get_active_logger().warning(
                "No %s file found.\nWe recommend documenting changes between versions. "
                "You can either\n\t- use the '--changelog' parameter of the deploy command\n\t"
                "- or add a file called %s next to the solution file.\nInsert what's printed "
                "between the following lines into %s and add your changes to the version you are "
                "about to release before running 'deploy':\n\n-----------------\n%s"
                "\n-----------------\n"
                % (changelog_name, changelog_name, changelog_name, content)
            )
