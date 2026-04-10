"""Module for handling a catalog as administrator."""

import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Iterator, List, Tuple

from git import Repo
from git.refs import HEAD

from album.api import Album
from album.ci.controller.zenodo_manager import ZenodoManager
from album.ci.utils.continuous_integration import create_report, get_ssh_url
from album.ci.utils.zenodo_api import ZenodoMetadata
from album.core.api.model.configuration import IConfiguration
from album.core.model.catalog import Catalog, retrieve_index_files_from_src
from album.core.model.default_values import DefaultValues
from album.core.utils.export.changelog import get_changelog_file_name
from album.core.utils.operations import view_operations
from album.core.utils.operations.file_operations import (
    force_remove,
    get_dict_entry,
    zip_folder,
)
from album.core.utils.operations.git_operations import (
    add_files_commit_and_push,
    add_tag,
    checkout_branch,
    configure_git,
    retrieve_files_from_head,
    retrieve_files_from_head_last_commit,
)
from album.core.utils.operations.resolve_operations import as_tag, dict_to_coordinates
from album.environments.utils.file_operations import (
    copy,
    get_dict_from_yml,
    write_dict_to_yml,
)
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class ReleaseManager:
    """Class for handling a catalog as administrator."""

    configuration: IConfiguration

    def __init__(
        self,
        album_instance: Album,
        catalog_name: str,
        catalog_path: str,
        catalog_src: str,
        force_retrieve: bool,
    ):
        """Initialize the ReleaseManager."""
        self.catalog_name = catalog_name
        self.catalog_path = catalog_path
        self.catalog_src = catalog_src

        self.configuration = album_instance.configuration()
        if not self.configuration.is_setup():
            self.configuration.setup()

        self.catalog = Catalog(
            None, name=self.catalog_name, path=catalog_path, src=self.catalog_src
        )
        self.force_retrieve = force_retrieve
        self.album_instance = album_instance

    @contextmanager
    def _open_repo(self) -> Iterator[Repo]:
        with self.catalog.retrieve_catalog(
            force_retrieve=self.force_retrieve, update=False
        ) as repo:
            yield repo

    def close(self) -> None:
        """Close the catalog and dispose resources."""
        if self.catalog:
            self.catalog.dispose()

    def configure_repo(self, user_name: str, user_email: str) -> None:
        """Configure the repository with the given user name and email."""
        module_logger().info(
            "Configuring repository using:\n\tusername:\t%s\n\temail:\t%s"
            % (user_name, user_email)
        )
        with self._open_repo() as repo:
            configure_git(repo, user_email, user_name)

    def configure_ssh(self, project_path: str) -> None:
        """Configure ssh protocol for the repository."""
        module_logger().info("Configure ssh protocol for repository %s" % project_path)
        with self._open_repo() as repo:
            if not repo.remote().url.startswith("git"):
                repo.remote().set_url(get_ssh_url(project_path, self.catalog_src))

    @staticmethod
    def _get_yml_dict(head: HEAD) -> Tuple[Dict[str, Any], Path]:
        yml_file_path = Path(
            retrieve_files_from_head_last_commit(
                head, DefaultValues.solution_yml_default_name.value
            )[0]
        )
        yml_dict = get_dict_from_yml(yml_file_path)

        return yml_dict, yml_file_path

    def zenodo_publish(
        self, branch_name: str, zenodo_base_url: str, zenodo_access_token: str
    ) -> None:
        """Publish an unpublished Zenodo deposit."""
        zenodo_base_url, zenodo_access_token = self._prepare_zenodo_arguments(
            zenodo_base_url, zenodo_access_token
        )

        zenodo_manager = self._get_zenodo_manager(zenodo_access_token, zenodo_base_url)

        with self._open_repo() as repo:
            head = checkout_branch(repo, branch_name)

            # get the yml file to release from current branch
            yml_dict, yml_file_path = self._get_yml_dict(head)

            # query deposit
            deposit_name = self._get_deposit_metadata(yml_dict).title
            deposit_id = get_dict_entry(yml_dict, "deposit_id", allow_none=False)

            module_logger().info(
                "Get unpublished deposit with deposit id %s..." % deposit_id
            )
            deposit = zenodo_manager.zenodo_get_unpublished_deposit_by_id(
                deposit_id, deposit_name
            )

            # publish to zenodo
            deposit.publish()

            add_tag(repo, as_tag(dict_to_coordinates(yml_dict)))

        module_logger().info(
            "Published unpublished deposit with deposit id %s..." % deposit_id
        )

    def _get_release_files(
        self,
        repo: Repo,
        yml_dict: Dict[str, Any],
        tmp_dir: str,
    ) -> Tuple[List[str], List[str]]:
        """Collect files to upload to Zenodo.

        The solution directory is zipped into ``solution.zip`` so that the
        full directory structure (including subdirectories like
        ``src/main/java/``) is preserved on Zenodo.  Key metadata files
        are additionally uploaded individually so Zenodo can preview them.

        Returns:
            A tuple of (absolute_paths, basenames) for all files to upload.
        """
        coordinates = dict_to_coordinates(yml_dict)
        solution_relative_path = (
            self.configuration.get_solution_path_suffix_unversioned(coordinates)
        )
        solution_dir_in_repo = Path(repo.working_tree_dir).joinpath(
            solution_relative_path
        )

        if not solution_dir_in_repo.is_dir():
            raise RuntimeError(
                "Solution directory %s does not exist in the repository!"
                % str(solution_dir_in_repo)
            )

        # zip the entire solution directory — preserves folder structure
        zip_target = Path(tmp_dir).joinpath(
            DefaultValues.solution_zip_default_name.value
        )
        zip_path = zip_folder(solution_dir_in_repo, zip_target)

        # individual files for Zenodo preview
        solution_yml = solution_dir_in_repo.joinpath(
            DefaultValues.solution_yml_default_name.value
        )
        files: List[str] = [str(solution_yml), str(zip_path)]

        for doc in self._get_documentation_paths(solution_dir_in_repo, yml_dict):
            files.append(str(doc))

        for cover in self._get_cover_paths(solution_dir_in_repo, yml_dict):
            files.append(str(cover))

        changelog = solution_dir_in_repo.joinpath(get_changelog_file_name())
        if changelog.exists():
            files.append(str(changelog))

        return files, [Path(f).name for f in files]

    def zenodo_upload(
        self,
        branch_name: str,
        zenodo_base_url: str,
        zenodo_access_token: str,
        report_file: Path,
    ) -> None:
        """Upload a solution to Zenodo."""
        zenodo_base_url, zenodo_access_token = self._prepare_zenodo_arguments(
            zenodo_base_url, zenodo_access_token
        )

        zenodo_manager = self._get_zenodo_manager(zenodo_access_token, zenodo_base_url)
        with self._open_repo() as repo, TemporaryDirectory() as tmp_dir:
            head = checkout_branch(repo, branch_name)

            # get the yml file to release
            yml_dict, yml_file_path = self._get_yml_dict(head)

            # get metadata from yml_file
            try:
                deposit_id = yml_dict["deposit_id"]
            except KeyError:
                deposit_id = None

            # If deposit_id is not explicitly set but a Zenodo DOI exists,
            # derive deposit_id from the DOI (format: 10.5281/zenodo.<id>)
            if not deposit_id:
                doi = yml_dict.get("doi")
                if doi and "zenodo" in doi.lower():
                    deposit_id = doi.rsplit(".", 1)[-1]
                    module_logger().info(
                        f"Derived deposit_id={deposit_id} from doi={doi}"
                    )
            coordinates = dict_to_coordinates(yml_dict)

            # do not upload SNAPSHOT versions
            if coordinates.version().endswith("SNAPSHOT"):
                module_logger().info(
                    "Will not upload SNAPSHOT version to zenodo! Skipping..."
                )
                return

            files, file_names = self._get_release_files(repo, yml_dict, tmp_dir)

            # get the release deposit. Either a new one or an existing one to perform an update on
            deposit = zenodo_manager.zenodo_get_deposit(
                self._get_deposit_metadata(yml_dict), deposit_id
            )
            module_logger().info("Deposit %s successfully retrieved..." % deposit.id)

            # include doi, deposit ID, and concept DOI in yml
            assert deposit.metadata is not None
            yml_dict["doi"] = deposit.metadata.prereserve_doi["doi"]
            yml_dict["deposit_id"] = deposit.id
            if deposit.conceptdoi:
                yml_dict["conceptdoi"] = deposit.conceptdoi
            elif deposit.conceptrecid:
                # conceptdoi is "" on draft deposits, but conceptrecid is
                # always available.  Derive the concept DOI so that
                # commit_changes (which runs before publish) captures it.
                yml_dict["conceptdoi"] = "10.5281/zenodo.%s" % deposit.conceptrecid
            write_dict_to_yml(yml_file_path, yml_dict)

            if deposit.files:
                for file in deposit.files:
                    if file.filename not in file_names:
                        # remove file from deposit
                        zenodo_manager.zenodo_delete(deposit, file.filename)

            for file in files:
                deposit = zenodo_manager.zenodo_upload(deposit, file)

        if report_file:
            report_vars = {
                "DOI": yml_dict["doi"],
                "DEPOSIT_ID": yml_dict["deposit_id"],
            }
            if yml_dict.get("conceptdoi"):
                report_vars["CONCEPTDOI"] = yml_dict["conceptdoi"]
            report_file = create_report(report_file, report_vars)
            module_logger().info("Created report file under %s" % str(report_file))

    @staticmethod
    def _prepare_zenodo_arguments(
        zenodo_base_url: str, zenodo_access_token: str
    ) -> Tuple[str, str]:
        if zenodo_base_url is None or zenodo_access_token is None:
            raise RuntimeError(
                "Zenodo base URL or Zenodo access token invalid! "
                "See https://zenodo.org/ documentation for information!"
            )

        zenodo_base_url = zenodo_base_url.strip()
        zenodo_access_token = zenodo_access_token.strip()

        if zenodo_base_url == "" or zenodo_access_token == "":
            raise RuntimeError("Empty zenodo base_url or zenodo_access_token!")

        module_logger().info("Using zenodo URL: %s" % zenodo_base_url)

        return zenodo_base_url, zenodo_access_token

    def update_index(self, branch_name: str, doi: str, deposit_id: str) -> None:
        """Update the catalog index with the solution from the given branch."""
        with self._open_repo() as repo:
            head = checkout_branch(repo, branch_name)

            # always use remote index
            with TemporaryDirectory(dir=self.configuration.tmp_path()) as tmp_dir:
                repo = Path(tmp_dir).joinpath("repo")
                try:
                    index_db, index_meta = retrieve_index_files_from_src(
                        self.catalog_src,
                        branch_name=self.catalog.branch_name(),
                        tmp_dir=repo,
                    )
                    if index_db.exists():
                        copy(index_db, self.catalog.index_file_path())
                    else:
                        module_logger().warning(
                            "Index not downloadable! Using Index in merge request branch!"
                        )
                finally:
                    force_remove(repo)

            self.album_instance.load_catalog_index(self.catalog)

            yml_dict, yml_file_path = self._get_yml_dict(head)

            # update doi and deposit_id if given
            log_message_doi = "without a doi"
            if doi:
                yml_dict["doi"] = doi
                log_message_doi = "with doi %s" % doi

            log_message_deposit = "without deposit"
            if deposit_id:
                yml_dict["deposit_id"] = deposit_id
                log_message_deposit = "in zenodo deposit %s" % deposit_id

            if doi or deposit_id:
                write_dict_to_yml(yml_file_path, yml_dict)

        module_logger().info(
            "Update index to include solution from branch %s %s %s!"
            % (branch_name, log_message_doi, log_message_deposit)
        )

        index = self.catalog.index()
        assert index is not None
        index.update(dict_to_coordinates(yml_dict), yml_dict)
        index.save()
        index.export(self.catalog.solution_list_path())

    def commit_changes(
        self, branch_name: str, ci_user_name: str, ci_user_email: str
    ) -> bool:
        """Commit changes to the catalog repository."""
        with self._open_repo() as repo:
            head = checkout_branch(repo, branch_name)

            yml_dict, yml_file = self._get_yml_dict(head)

            # get files to release
            coordinates = dict_to_coordinates(yml_dict)
            solution_relative_path = (
                self.configuration.get_solution_path_suffix_unversioned(coordinates)
            )
            files = retrieve_files_from_head(
                head, str(solution_relative_path) + os.sep + "*", number_of_files=-1
            )

            commit_files = [yml_file] + files
            if not all(Path(f).is_file() for f in commit_files):
                raise FileNotFoundError(
                    "Invalid deploy request or broken catalog repository!"
                )

            commit_msg = 'Prepared branch "%s" for merging.' % branch_name

            add_files_commit_and_push(
                head,
                commit_files,
                commit_msg,
                push=False,
                username=ci_user_name,
                email=ci_user_email,
            )

        return True

    def merge(
        self,
        branch_name: str,
        dry_run: bool,
        push_option: List[str],
        ci_user_name: str,
        ci_user_email: str,
    ) -> None:
        """Merge the branch into the main branch."""
        with self._open_repo() as repo:
            head = checkout_branch(repo, branch_name)

            yml_dict, yml_file = self._get_yml_dict(head)

            commit_files = [
                yml_file,
                self.catalog.solution_list_path(),
                self.catalog.index_file_path(),
            ]
            if not all(Path(f).is_file() for f in commit_files):
                raise FileNotFoundError(
                    "Invalid deploy request or broken catalog repository!"
                )

            commit_msg = "Updated index."

            module_logger().info("Prepare merging...")

            add_files_commit_and_push(
                head,
                commit_files,
                commit_msg,
                push=not dry_run,
                push_option_list=push_option,
                username=ci_user_name,
                email=ci_user_email,
                allow_empty=True,
            )

    def _get_zenodo_manager(
        self, zenodo_access_token: str, zenodo_base_url: str
    ) -> ZenodoManager:
        # TODO in case one wants to reuse the zenodo manager, this needs to be smarter, but be aware that another call
        #  to this method might have different parameters
        return ZenodoManager(zenodo_base_url, zenodo_access_token)

    @staticmethod
    def _get_documentation_paths(
        base_dir: Path, yml_dict: Dict[str, Any]
    ) -> List[Path]:
        documentation_paths = []
        if "documentation" in yml_dict.keys():
            documentation_list = yml_dict["documentation"]
            if not isinstance(documentation_list, list):
                documentation_list = [documentation_list]

            for documentation_name in documentation_list:
                documentation_paths.append(base_dir.joinpath(documentation_name))
        return documentation_paths

    @staticmethod
    def _get_cover_paths(base_dir: Path, yml_dict: Dict[str, Any]) -> List[Path]:
        cover_paths = []
        if "covers" in yml_dict.keys():
            cover_list = yml_dict["covers"]
            if not isinstance(cover_list, list):
                cover_list = [cover_list]

            for cover in cover_list:
                if "source" in cover:
                    cover_paths.append(base_dir.joinpath(cover["source"]))
        return cover_paths

    def _get_deposit_metadata(self, solution_meta: Dict[str, Any]) -> ZenodoMetadata:
        if "title" in solution_meta:
            deposit_name = solution_meta["title"]
        else:
            deposit_name = str(dict_to_coordinates(solution_meta))
        if "solution_creators" in solution_meta:
            authors = solution_meta["solution_creators"]
        else:
            authors = []
        creators = [{"name": author} for author in authors]
        if not creators:
            creators = [{"name": "unknown"}]
        description = (
            "Album solution - for more information read https://album.solutions."
        )
        if "description" in solution_meta:
            description = solution_meta["description"]
        license_ = None
        if "license" in solution_meta:
            license_ = solution_meta["license"]
        version = None
        if "version" in solution_meta:
            version = solution_meta["version"]
        related_identifiers = [
            {"relation": "cites", "identifier": DefaultValues.album_cite_doi.value}
        ]
        references = [
            view_operations.get_citation_as_string(
                {
                    "doi": DefaultValues.album_cite_doi.value,
                    "url": DefaultValues.album_cite_url.value,
                    "text": DefaultValues.album_cite_text.value,
                }
            )
        ]
        if "cite" in solution_meta:
            for citation in solution_meta["cite"]:
                if "doi" in citation:
                    related_identifiers.append(
                        {"relation": "cites", "identifier": citation["doi"]}
                    )
                if "text" in citation:
                    references.append(view_operations.get_citation_as_string(citation))

        return ZenodoMetadata.default_values(
            deposit_name,
            creators,
            description,
            license_,
            version,
            related_identifiers,
            references,
        )
