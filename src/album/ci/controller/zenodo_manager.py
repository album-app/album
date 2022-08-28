import os

from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.runner import album_logging

from album.ci.utils import zenodo_api

module_logger = album_logging.get_active_logger


class ZenodoManager:
    def __init__(self, zenodo_base_url, zenodo_access_token):
        self.query = zenodo_api.ZenodoAPI(zenodo_base_url, zenodo_access_token)

    @staticmethod
    def zenodo_upload(deposit, file):
        """Uploads a solution file to a ZenodoDeposit. Expects the deposit to be writable. (e.g. unpublished)

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
            module_logger().debug(
                "Update file %s in Zenodo deposit with id %s..."
                % (file_basename, deposit.id)
            )
            deposit.update_file(file_basename, file)
        else:
            module_logger().debug(
                "Create file %s in Zenodo deposit with id %s..."
                % (file_basename, deposit.id)
            )
            deposit.create_file(file)

        return deposit

    @staticmethod
    def zenodo_delete(deposit, file):
        """Deletes a solution file from a ZenodoDeposit. Expects the deposit to be writable. (e.g. unpublished)

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
            module_logger().debug(
                "Update file %s in Zenodo deposit with id %s..."
                % (file_basename, deposit.id)
            )
            deposit.delete_file(file_basename, file)
        else:
            module_logger().warning(
                "Cannot find file %s in Zenodo deposit with id %s."
                % (file_basename, deposit.id)
            )

        return deposit

    def zenodo_get_deposit(self, metadata, deposit_id, expected_files=None):
        """Queries zenodo to get the deposit of the solution_file. Creates an empty deposit if no deposit exists.

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
            deposit = self._zenodo_get_deposit_by_id(deposit_id)

            self._check_deposit(deposit, metadata.title, expected_files)

        else:
            module_logger().debug("Query new deposit with DOI...")
            deposit = self.query.deposit_create_with_prereserve_doi(metadata)

        return deposit

    def _get_deposit_name(self, solution_meta):
        if solution_meta["title"]:
            deposit_name = solution_meta["title"]
        else:
            deposit_name = str(dict_to_coordinates(solution_meta))
        return deposit_name

    def zenodo_get_unpublished_deposit_by_id(
        self, deposit_id, deposit_name, expected_files=None
    ):
        deposit = self._zenodo_get_unpublished(deposit_id)

        # raise error when not found
        if not deposit:
            raise RuntimeError("Deposit with id %s not found!" % deposit_id)

        self._check_deposit(deposit, deposit_name, expected_files)

        return deposit

    @staticmethod
    def _check_deposit(deposit, expected_deposit_name, expected_files=None):
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

    def _zenodo_get_deposit_by_id(self, deposit_id):
        """Querying deposit by id."""
        # get published deposit
        deposit = self._zenodo_get_published(deposit_id)

        # get unpublished deposit
        if not deposit:
            deposit = self._zenodo_get_unpublished(deposit_id)

        # raise error when not found
        if not deposit:
            raise RuntimeError("Deposit with id %s not found!" % deposit_id)

        return deposit

    def _zenodo_get_unpublished(self, deposit_id):
        deposit = self.query.deposit_get(
            deposit_id, status=zenodo_api.DepositStatus.DRAFT
        )

        if deposit:
            deposit = deposit[0]

            module_logger().debug("Deposit with id %s found..." % deposit.id)

            if (
                deposit.metadata is None
                or not isinstance(deposit.metadata.prereserve_doi, dict)
                or "doi" not in deposit.metadata.prereserve_doi.keys()
            ):
                raise RuntimeError("Deposit has no prereserved DOI! Invalid deposit!")

        return deposit

    def _zenodo_get_published(self, deposit_id):
        deposit = self.query.deposit_get(deposit_id)

        if deposit and deposit[0].submitted:
            deposit = deposit[0]

            module_logger().debug(
                "Deposit with id %s found but it has already been published. Querying new version..."
                % deposit.id
            )

            deposit = deposit.new_version()

        return deposit
