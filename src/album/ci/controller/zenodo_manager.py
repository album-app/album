"""ZenodoManager class to manage Zenodo deposits."""

import os
from typing import Dict, Iterable, List, Union

from album.ci.utils import zenodo_api
from album.ci.utils.zenodo_api import ZenodoDeposit, ZenodoMetadata
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class ZenodoManager:
    """ZenodoManager class to manage Zenodo deposits."""

    def __init__(self, zenodo_base_url: str, zenodo_access_token: str):
        """Initialize the ZenodoManager."""
        self.query = zenodo_api.ZenodoAPI(zenodo_base_url, zenodo_access_token)

    @staticmethod
    def zenodo_upload(deposit: ZenodoDeposit, file: str) -> ZenodoDeposit:
        """Upload a solution file to a ZenodoDeposit.

        Expects the deposit to be writable (e.g. unpublished).

        Args:
            deposit:
                The deposit to upload to.
            file:
                The file to upload.

        Returns:
            The updated deposit.

        """
        file_basename = os.path.basename(file)

        if file_basename in deposit.files:  # File does exist
            module_logger().info(
                "Updating file '%s' in Zenodo deposit %s..."
                % (file_basename, deposit.id)
            )
            deposit.update_file(file_basename, file)
        else:
            module_logger().info(
                "Creating file '%s' in Zenodo deposit %s..."
                % (file_basename, deposit.id)
            )
            deposit.create_file(file)

        module_logger().info(
            f"File '{file_basename}' uploaded to deposit {deposit.id}."
        )

        return deposit

    @staticmethod
    def zenodo_delete(deposit: ZenodoDeposit, file: str) -> ZenodoDeposit:
        """Delete a solution file from a ZenodoDeposit.

        Expects the deposit to be writable. (e.g. unpublished)

        Args:
            deposit:
                The deposit to upload to.
            file:
                The file to delete.

        Returns:
            The updated deposit.

        """
        file_basename = os.path.basename(file)

        if file_basename in deposit.files:  # File does exist
            module_logger().info(
                "Deleting file '%s' from Zenodo deposit %s..."
                % (file_basename, deposit.id)
            )
            deposit.delete_file(file_basename)
        else:
            module_logger().warning(
                "Cannot find file '%s' in Zenodo deposit %s — nothing to delete."
                % (file_basename, deposit.id)
            )

        return deposit

    def zenodo_get_deposit(
        self,
        metadata: ZenodoMetadata,
        deposit_id: str,
        expected_files: Union[Iterable, None] = None,
    ) -> ZenodoDeposit:
        """Query zenodo to get the deposit of the solution_file.

         Create an empty deposit if no deposit exists.

        Args:
            metadata:
                The metadata of the zenodo deposit.
            deposit_id:
                The deposit ID of the deposit the solution file lives in.
            expected_files:
                The files the deposit should hold.

        Returns:
            The deposit. Either brand-new, or the one holding the solution file.

        Raises:
            AttributeError:
               When the deposit does NOT hold the file it should hold.
               When the deposit_name given does not match the deposit name found

        """
        if deposit_id:  # case deposit already exists
            module_logger().info("Querying existing deposit with id %s..." % deposit_id)
            deposit = self._zenodo_get_deposit_by_id(deposit_id)[0]

            # Update the deposit metadata to reflect new version information.
            # This is crucial for new version drafts which inherit metadata
            # from the published version (e.g. old version number).
            module_logger().info(
                "Updating metadata for deposit %s (title=%s, version=%s)..."
                % (deposit.id, metadata.title, metadata.version)
            )
            deposit.update(metadata)

            self._check_deposit(deposit, metadata.title, expected_files)

        else:
            module_logger().info(
                "No deposit_id provided — creating new deposit with DOI..."
            )
            deposit = self.query.deposit_create_with_prereserve_doi(metadata)
            pre_doi = (
                deposit.metadata.prereserve_doi.get("doi", "?")
                if deposit.metadata
                else "?"
            )
            module_logger().info(f"New deposit created: id={deposit.id}, doi={pre_doi}")

        return deposit

    def _get_deposit_name(self, solution_meta: Dict[str, str]) -> str:
        """Get the deposit name from the solution metadata."""
        if solution_meta["title"]:
            deposit_name = solution_meta["title"]
        else:
            deposit_name = str(dict_to_coordinates(solution_meta))
        return deposit_name

    def zenodo_get_unpublished_deposit_by_id(
        self,
        deposit_id: str,
        deposit_name: str,
        expected_files: Union[Iterable, None] = None,
    ) -> ZenodoDeposit:
        """Query zenodo to get the unpublished deposit by id."""
        module_logger().info(
            "Querying unpublished (draft) deposit %s (expected name=%s)..."
            % (deposit_id, deposit_name)
        )
        deposit = self._zenodo_get_unpublished(deposit_id)[0]

        # raise error when not found
        if not deposit:
            raise RuntimeError("Deposit with id %s not found!" % deposit_id)

        module_logger().info(
            f"Unpublished deposit {deposit.id} found (title={deposit.title})."
        )
        self._check_deposit(deposit, deposit_name, expected_files)

        return deposit

    @staticmethod
    def _check_deposit(
        deposit: ZenodoDeposit,
        expected_deposit_name: str,
        expected_files: Union[Iterable, None] = None,
    ) -> None:
        """Check if the deposit is as expected."""
        # assess files in deposit.
        if expected_files:
            for expected_file in expected_files:
                if expected_file not in deposit.files:
                    raise AttributeError(
                        "Deposit has no file with the name %s!" % expected_file
                    )

        if deposit.title != expected_deposit_name:
            raise AttributeError(
                "Deposit name different than expected! Expected: %s Found: %s"
                % (expected_deposit_name, deposit.title)
            )

    def _zenodo_get_deposit_by_id(self, deposit_id: str) -> List[ZenodoDeposit]:
        """Get a deposit by id."""
        # get published deposit
        module_logger().info(
            "Looking up deposit %s (checking published first)..." % deposit_id
        )
        deposit = self._zenodo_get_published(deposit_id)

        # get unpublished deposit
        if not deposit:
            module_logger().info(
                "No published deposit %s — checking for unpublished draft..."
                % deposit_id
            )
            deposit = self._zenodo_get_unpublished(deposit_id)

        # raise error when not found
        if not deposit:
            raise RuntimeError("Deposit with id %s not found!" % deposit_id)

        module_logger().info(
            "Deposit %s resolved (submitted=%s)."
            % (deposit[0].id, deposit[0].submitted)
        )
        return deposit

    def get_published_deposit(self, deposit_id: str) -> Union[ZenodoDeposit, None]:
        """Return the published deposit if it exists, WITHOUT creating a new version.

        This is used for re-run detection: if a deposit is already published
        for the same version, the upload step can be skipped entirely.
        """
        module_logger().info("Checking published state of deposit %s..." % deposit_id)
        # Try the deposit API first.
        try:
            deposit = self.query.deposit_get(deposit_id)
            if deposit and deposit[0].submitted:
                module_logger().info(
                    "Deposit %s is published (via deposit API)." % deposit_id
                )
                return deposit[0]
        except Exception:
            module_logger().info(
                "Deposit API returned error for %s — trying records API..." % deposit_id
            )

        # Fallback: query the records API (published deposits are always
        # visible there, even when the deposit endpoint returns 404).
        try:
            records = self.query.records_get(record_id=deposit_id)
            if records:
                module_logger().info("Deposit %s found via records API." % deposit_id)
                return records[0]
        except Exception:
            module_logger().info(
                "Records API also returned no result for %s." % deposit_id
            )

        module_logger().info("Deposit %s is not published." % deposit_id)
        return None

    def get_latest_version_by_concept(
        self, conceptrecid: str
    ) -> Union[ZenodoDeposit, None]:
        """Return the latest published version under a concept record ID.

        Zenodo's records API automatically redirects a concept record ID
        to the latest published version.  This allows checking what the
        newest version is without knowing its specific deposit ID.

        Returns:
            The latest published ``ZenodoRecord`` (or ``ZenodoDeposit``),
            or ``None`` if the lookup fails.
        """
        module_logger().info(
            "Querying latest version under concept record %s..." % conceptrecid
        )
        try:
            records = self.query.records_get(record_id=conceptrecid)
            if records:
                latest = records[0]
                # The records API stores the semantic version in
                # metadata.version, not at the top level.
                version = getattr(latest, "version", None)
                if not version and latest.metadata:
                    version = getattr(latest.metadata, "version", None)
                module_logger().info(
                    "Latest version under concept %s: deposit=%s, version=%s"
                    % (conceptrecid, latest.id, version)
                )
                return latest
        except Exception:
            module_logger().info(
                "Could not resolve concept record %s via records API." % conceptrecid
            )
        return None

    def resolve_concept_record_id(
        self, deposit_id: str, conceptdoi: Union[str, None] = None
    ) -> Union[str, None]:
        """Derive the concept record ID for a deposit.

        Tries two strategies:
        1. Parse ``conceptdoi`` (format ``<prefix>/zenodo.<conceptrecid>``).
        2. Query the deposit API for ``deposit_id`` and read ``conceptrecid``.

        Returns:
            The concept record ID as a string, or ``None`` if unavailable.
        """
        # Strategy 1: parse from conceptdoi
        if conceptdoi and "zenodo" in conceptdoi.lower():
            conceptrecid = conceptdoi.rsplit(".", 1)[-1]
            module_logger().info(
                "Derived conceptrecid=%s from conceptdoi=%s"
                % (conceptrecid, conceptdoi)
            )
            return conceptrecid

        # Strategy 2: query the deposit and read conceptrecid
        if deposit_id:
            try:
                deposit = self.query.deposit_get(deposit_id)
                if deposit and deposit[0].conceptrecid:
                    conceptrecid = str(deposit[0].conceptrecid)
                    module_logger().info(
                        "Resolved conceptrecid=%s from deposit %s"
                        % (conceptrecid, deposit_id)
                    )
                    return conceptrecid
            except Exception:
                module_logger().info(
                    "Could not resolve conceptrecid from deposit %s." % deposit_id
                )

        module_logger().info(
            "No concept record ID available (deposit_id=%s, conceptdoi=%s)."
            % (deposit_id, conceptdoi)
        )
        return None

    def _zenodo_get_unpublished(self, deposit_id: str) -> List[ZenodoDeposit]:
        """Get an unpublished deposit by id."""
        module_logger().debug(
            "Querying Zenodo deposit API for draft deposit %s..." % deposit_id
        )
        deposit = self.query.deposit_get(
            deposit_id, status=zenodo_api.DepositStatus.DRAFT
        )

        if deposit:
            deposit_ = deposit[0]

            module_logger().info("Draft deposit %s found." % deposit_.id)

            if (
                deposit_.metadata is None
                or not isinstance(deposit_.metadata.prereserve_doi, dict)
                or "doi" not in deposit_.metadata.prereserve_doi.keys()
            ):
                raise RuntimeError("Deposit has no prereserved DOI! Invalid deposit!")
        else:
            module_logger().debug("No draft deposit found for id %s." % deposit_id)

        return deposit

    def _zenodo_get_published(self, deposit_id: str) -> List[ZenodoDeposit]:
        """Get a published deposit by id."""
        module_logger().debug(
            "Querying Zenodo deposit API for published deposit %s..." % deposit_id
        )
        deposit = self.query.deposit_get(deposit_id)

        if deposit and deposit[0].submitted:
            deposit_ = deposit[0]

            module_logger().info(
                "Deposit %s is already published — requesting new version draft..."
                % deposit_.id
            )

            deposit = deposit_.new_version()
            module_logger().info("New version draft created: id=%s" % deposit[0].id)

        return deposit
