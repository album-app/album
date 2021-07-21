import os

from album.ci.utils import zenodo_api
from album.core.concept.singleton import Singleton
from album_runner import logging

module_logger = logging.get_active_logger


class ZenodoManager(metaclass=Singleton):

    def __init__(self, zenodo_base_url, zenodo_access_token):
        self.query = zenodo_api.ZenodoAPI(
            zenodo_base_url,
            zenodo_access_token
        )

    @staticmethod
    def zenodo_upload(deposit, solution_zip):
        """ Uploads a solution file to a ZenodoDeposit. Expects the deposit to be writable. (e.g. unpublished)

        Args:
            deposit:
                The deposit to upload to.
            solution_zip:
                The solution zip file to upload.

        Returns:
            The updated deposit.

        """
        solution_zip_basename = os.path.basename(solution_zip)

        if solution_zip_basename in deposit.files:  # File does exist
            module_logger().debug(
                "Update solution file %s to Zenodo deposit with id %s..." % (solution_zip_basename, deposit.id)
            )
            deposit.update_file(solution_zip_basename, solution_zip)
        else:
            module_logger().debug(
                "Create solution file %s in Zenodo deposit with id %s..." % (solution_zip_basename, deposit.id)
            )
            deposit.create_file(solution_zip)

        return deposit

    def zenodo_get_deposit(self, deposit_name, deposit_id, expected_files=None):
        """Querys zenodo to get the deposit of the solution_file. Creates an empty deposit if no deposit exists.

        Args:
            deposit_name:
                The name of the deposit.
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

            self._check_deposit(deposit, deposit_name, expected_files)

        else:
            module_logger().debug("Query new deposit with DOI...")
            deposit = self.query.deposit_create_with_prereserve_doi(deposit_name)

        return deposit

    def zenodo_get_unpublished_deposit_by_id(self, deposit_id, deposit_name, expected_files=None):
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
                    raise AttributeError('Deposit has no file with the name %s!' % expected_file)

        if deposit.title != expected_deposit_name:
            raise AttributeError(
                'Deposit name different than expected! Expected: %s Found: %s' % (expected_deposit_name, deposit.title)
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
        deposit = self.query.deposit_get(deposit_id, status=zenodo_api.DepositStatus.DRAFT)

        if deposit:
            deposit = deposit[0]

            module_logger().debug("Deposit with id %s found..." % deposit.id)

            if deposit.metadata is None \
                    or not isinstance(deposit.metadata.prereserve_doi, dict) \
                    or "doi" not in deposit.metadata.prereserve_doi.keys():
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
