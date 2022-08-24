import json
import os
from enum import Enum, unique

import requests


class InvalidResponseStatusError(BaseException):
    """Raised when the response status is not the one expected."""

    pass


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


@unique
class DepositStatus(Enum):
    """All possible zenodo deposit status."""

    DRAFT = "draft"
    PUBLISHED = "published"


@unique
class SortOrder(Enum):
    """Sort order of the results obtained in 'list' methods."""

    BEST_MATCH = "bestmatch"
    MOST_RECENT = "mostrecent"


@unique
class UploadType(Enum):
    """Possible upload values and their name."""

    PUBLICATION = "publication"
    POSTER = "poster"
    PRESENTATION = "presentation"
    DATA_SET = "dataset"
    IMAGE = "image"
    VIDEO = "video"
    SOFTWARE = "software"
    LESSON = "lesson"
    PHYSICAL_OBJECT = "physicalobject"
    OTHER = "other"


@unique
class AccessRight(Enum):
    """Possible upload values and their name."""

    OPEN = "open"
    EMBARGOED = "embargoed"
    RESTRICTED = "restricted"
    CLOSED = "closed"


@unique
class PublicationType(Enum):
    """Possible publication values and their name."""

    ANNOTATION_COLLECTION = "annotationcollection"
    BOOK = "book"
    SECTION = "section"
    CONFERENCE_PAPER = "conferencepaper"
    DATA_MANAGEMENT_PLAN = "datamanagementplan"
    ARTICLE = "article"
    PATENT = "patent"
    PRE_PRINT = "preprint"
    DELIVERABLE = "deliverable"
    MILESTONE = "milestone"
    PROPOSAL = "proposal"
    REPORT = "report"
    SOFTWARE_DOCUMENTATION = "softwaredocumentation"
    TAXONOMIC_TREATMENT = "taxonomictreatment"
    TECHNICAL_NOTE = "technicalnote"
    THESIS = "thesis"
    WORKING_PAPER = "workingpaper"
    OTHER = "other"


class ZenodoEntry(object):
    """Base class for all Zenodo API objects.

     The base class all Zenodo API objects inherit from.
     Base url and access_token stored in object to query the API.

    Attributes:
        entry_dict: The dictionary used to construct the object.
        base_url: The URL used to query the API (Save changes).
        params: Holds access token to authenticate to the API.
    """

    @staticmethod
    def _get_attribute(entry_dict, key, required=False):
        """Checks the dict for keys.

        Args:
            entry_dict:
                The dict to retrieve values from.
            key:
                The key to look for.
            required:
                Boolean to indicate weather to raise Error on missing key.

        Returns:
            Value or None.

        Raises:
            AttributeError: When key not found if required.
        """
        if key in entry_dict.keys():
            return entry_dict[key]
        if required:
            raise AttributeError("Key %s not found but required" % key)
        return None

    def __init__(self, entry_dict, base_url, access_token):
        """Inits @ZenodoEntry.

        Args:
            entry_dict:
                Dictionary for init.
            base_url:
                The base URL of the API to use.
            access_token:
                The authentication token to use for querying the API.
        """
        self.entry_dict = entry_dict
        self.base_url = base_url
        self.params = {"access_token": access_token}

    def to_dict(self):
        """Removes sensitive information from the object and gives back its dictionary representation.

        Returns:
            The dictionary ready for submission via API.
        """
        d = self.__dict__

        if "entry_dict" in d.keys():
            d.pop("entry_dict")
        if "params" in d.keys():
            d.pop("params")
        if "base_url" in d.keys():
            d.pop("base_url")

        # remove None
        d = {k: v for k, v in d.items() if v is not None}

        # treat special objects
        if "metadata" in d.keys():
            if isinstance(d["metadata"], ZenodoMetadata):
                d["metadata"] = self.metadata.to_dict()

        if "files" in d.keys():
            if isinstance(d["files"], ZenodoFile):
                d["files"] = [x.to_dict() for x in self.files]

        if "stats" in d.keys():
            if isinstance(d["stats"], ZenodoRecordStats):
                d["stats"] = self.stats.to_dict()

        return d


class ZenodoMetadata(ZenodoEntry):
    """All possible metadata of a @ZenodoDeposit."""

    @classmethod
    def default_values(
        cls,
        title,
        creators,
        description,
        license,
        version,
        related_identifiers,
        references,
    ):
        default_values = {
            "access_right": AccessRight.OPEN.value,
            "access_right_category": None,
            "creators": creators,
            "description": description,
            "doi": None,
            "license": license,
            "prereserve_doi": "true",
            "publication_date": None,
            "related_identifiers": related_identifiers,
            "relations": None,
            "references": references,
            "resource_type": None,
            "title": title,
            "version": version,
            "upload_type": UploadType.SOFTWARE.value,
        }
        return cls(default_values)

    def __init__(self, entry_dict):
        super().__init__(entry_dict, "", "")
        self.access_right = self._get_attribute(entry_dict, "access_right")
        self.access_right_category = self._get_attribute(
            entry_dict, "access_right_category"
        )
        self.creators = self._get_attribute(entry_dict, "creators")
        self.description = self._get_attribute(entry_dict, "description")
        self.doi = self._get_attribute(entry_dict, "doi")
        self.license = self._get_attribute(entry_dict, "license")
        self.prereserve_doi = self._get_attribute(entry_dict, "prereserve_doi")
        self.publication_date = self._get_attribute(entry_dict, "publication_date")
        self.related_identifiers = self._get_attribute(
            entry_dict, "related_identifiers"
        )
        self.relations = self._get_attribute(entry_dict, "relations")
        self.resource_type = self._get_attribute(entry_dict, "resource_type")
        self.title = self._get_attribute(entry_dict, "title")
        self.upload_type = self._get_attribute(entry_dict, "upload_type")
        self.version = self._get_attribute(entry_dict, "version")
        self.references = self._get_attribute(entry_dict, "references")


class IterableList(list):
    """List for accessing objects in the list by a certain attribute or by the index."""

    def __init__(self, id_attr):
        super().__init__()
        self._id_attr = id_attr

    def __contains__(self, attr):
        try:
            getattr(self, attr)
            return True
        except (AttributeError, TypeError):
            return False

    def __getattr__(self, attr):
        for item in self:
            if getattr(item, self._id_attr) == attr:
                return item
        return list.__getattribute__(self, attr)

    def __getitem__(self, index):
        if isinstance(index, int):
            return list.__getitem__(self, index)

        try:
            return getattr(self, index)
        except AttributeError as e:
            raise IndexError("No item found with id %r" % index) from e


class ZenodoFile(ZenodoEntry):
    """Describes a file in a @ZenodoDeposit or a @ZenodoRecord."""

    _id_attribute_ = "filename"

    @classmethod
    def list_items(cls, deposit):
        out_list = IterableList(cls._id_attribute_)
        out_list.extend(cls.iter_items(deposit))
        return out_list

    @classmethod
    def iter_items(cls, deposit):
        return (f for f in deposit._files)

    def __init__(self, entry_dict):
        super().__init__(entry_dict, "", "")
        self.checksum = self._get_attribute(entry_dict, "checksum")
        self.bucket = self._get_attribute(entry_dict, "bucket")
        self.key = self._get_attribute(entry_dict, "key")
        self.filename = self._get_attribute(entry_dict, "filename")
        self.filesize = self._get_attribute(entry_dict, "filesize")
        self.size = self._get_attribute(entry_dict, "size")
        self.id = self._get_attribute(entry_dict, "id")
        self.type = self._get_attribute(entry_dict, "type")
        self.links = self._get_attribute(entry_dict, "links")

    # todo: write tests
    def get_download_link(self):
        return self.links["self"]


class ZenodoDeposit(ZenodoEntry):
    """The Zenodo Deposit class."""

    def __init__(self, entry_dict, base_url, access_token):
        """Inits the class.

        The dictionary usually comes from a API response. Files and metadata keys will have extra classes.

        Args:
            entry_dict:
                dictionary for init.
            base_url:
                The base URL of the API to use.
            access_token:
                The authentication token to use for querying the API.
        """
        super().__init__(entry_dict, base_url, access_token)
        self.conceptdoi = self._get_attribute(entry_dict, "conceptdoi")
        self.conceptrecid = self._get_attribute(entry_dict, "conceptrecid")
        self.created = self._get_attribute(entry_dict, "created")
        self.doi = self._get_attribute(entry_dict, "doi")
        self.doi_url = self._get_attribute(entry_dict, "doi_url")
        self.id = self._get_attribute(entry_dict, "id")
        self.links = self._get_attribute(entry_dict, "links")
        self.modified = self._get_attribute(entry_dict, "modified")
        self.owner = self._get_attribute(entry_dict, "owner")
        self.record_id = self._get_attribute(entry_dict, "record_id")
        self.state = self._get_attribute(entry_dict, "state")
        self.submitted = self._get_attribute(entry_dict, "submitted")
        self.title = self._get_attribute(entry_dict, "title")
        self.version = self._get_attribute(entry_dict, "version")
        self.related_identifiers = self._get_attribute(
            entry_dict, "related_identifiers"
        )
        self.references = self._get_attribute(entry_dict, "references")

        meta_init = self._get_attribute(entry_dict, "metadata")
        self.metadata = (
            ZenodoMetadata(meta_init) if meta_init is not None else meta_init
        )

        files_init = self._get_attribute(entry_dict, "files")
        self.files = files_init

    @property
    def files(self):
        return ZenodoFile.list_items(self)

    @files.setter
    def files(self, files_init):
        if files_init:
            files = []
            for file_entry in files_init:
                if isinstance(file_entry, ZenodoFile):
                    files.append(file_entry)
                else:
                    files.append(ZenodoFile(file_entry))
            self._files = files
        else:
            self._files = []

    # ############# Deposits attributes #############

    def get_files_id_by_name(self, name):
        """Retrieve the id of a file given its name.

        Args:
            name:
                The name of the file. A full path is not allowed since they are not stored in the Zenodo DB.

        Returns:
            The ID of the file if the name is unique.

        Raises:
            AssertionError: If the name is not unique.
        """
        file_id = None
        unique_control = 0
        if self.files:
            for file_entry in self.files:
                if file_entry.filename == name:
                    file_id = file_entry.id
                    unique_control += 1

        if unique_control > 1:
            raise AssertionError(
                "Deposit broken. File names not unique. Please reload deposit and try again!"
            )

        return file_id

    def list_files_name(self):
        """Obtain a list of all filenames in the deposit.

        Returns:
            list of names. Can be empty.
        """
        names = []
        for file in self.files:
            names.append(file.filename)

        return names

    # ############# Deposits operations #############

    def reload(self):
        """Reload the deposit. Resets all changes.

        Returns:
             True if success.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """
        link = self.base_url + "/api/deposit/depositions/%s" % self.id

        r = requests.get(link, params=self.params)

        response_dict = ZenodoAPI.validate_response(r, ResponseStatus.OK)

        # update object according to response
        self.__init__(response_dict, self.base_url, self.params["access_token"])

        return True

    def update(self, zenodo_metadata):
        """Updates the metadata of a deposit.

        Args:
            zenodo_metadata:
                The metadata. Either as dictionary or as @ZenodoMetadata object.

        Returns:
             True if success.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """
        if not isinstance(zenodo_metadata, ZenodoMetadata):
            try:
                zenodo_metadata = ZenodoMetadata(zenodo_metadata)
            except AttributeError:
                print("Please provide a valid dictionary as input!")

        link = self.base_url + "/api/deposit/depositions/%s" % self.id

        headers = {"Content-Type": "application/json"}
        r = requests.put(
            link,
            params=self.params,
            data=json.dumps({"metadata": zenodo_metadata.to_dict()}),
            headers=headers,
        )

        response_dict = ZenodoAPI.validate_response(r, ResponseStatus.OK)

        # update object according to response
        self.__init__(response_dict, self.base_url, self.params["access_token"])

        return True

    def delete(self):
        """Deletes an unpublished deposit.

        Returns:
             True if success.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """

        # todo: check if not already published

        link = self.base_url + "/api/deposit/depositions/%s" % self.id

        r = requests.delete(link, params=self.params)

        if ZenodoAPI.validate_response(r, ResponseStatus.NoContent):
            self.__init__({}, "", "")

        return True

    # ############# Deposits actions #############

    def publish(self):
        """Publishes an unpublished repo.

        Returns:
             True if success.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """

        # todo: check if already published

        link = self.base_url + "/api/deposit/depositions/%s/actions/publish" % self.id
        r = requests.post(link, params=self.params)

        response_dict = ZenodoAPI.validate_response(r, ResponseStatus.Accepted)

        # update object according to response
        self.__init__(response_dict, self.base_url, self.params["access_token"])

        return True

    def new_version(self):
        """Creates a new version of the deposit.

        Returns:
             True if success.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """

        def extract_draft_id(latest_draft_l):
            draft_id, _ = os.path.splitext(os.path.basename(latest_draft_l))
            return draft_id

        link = (
            self.base_url + "/api/deposit/depositions/%s/actions/newversion" % self.id
        )

        r = requests.post(link, params=self.params)

        response_dict = ZenodoAPI.validate_response(r, ResponseStatus.OK)

        # update object according to response
        self.__init__(response_dict, self.base_url, self.params["access_token"])

        # return new version
        try:
            latest_draft_link = self.links["latest_draft"]
            latest_draft_id = extract_draft_id(latest_draft_link)
        except KeyError as e:
            raise KeyError(
                "Could not find link to latest_draft in response! Aborting..."
            ) from e

        return ZenodoAPI(self.base_url, self.params["access_token"]).deposit_get(
            latest_draft_id, status=DepositStatus.DRAFT
        )

    # ############# Deposition files #############

    def get_remote_files(self):
        """Retrieve all files listed in a deposit

        Returns:
             A list of @ZenodoFile objects.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """
        link = self.base_url + "/api/deposit/depositions/%s/files" % self.id

        r = requests.get(link, params=self.params)

        response_dict = ZenodoAPI.validate_response(r, ResponseStatus.OK)

        file_list = []
        for file_dict in response_dict:
            file_list.append(ZenodoFile(file_dict))

        self.files = file_list if file_list else None

        return file_list

    def create_file(self, file):
        """Uploads a new file to the deposit.

        Args:
            file:
                The full path to the file to upload.

        Returns:
            A @ZenodoFile object.
        """
        link = self.base_url + "/api/deposit/depositions/%s/files" % self.id

        data = {"name": os.path.basename(file)}
        open_file = open(file, "rb")
        files = {"file": open_file}

        r = requests.post(link, data=data, files=files, params=self.params)

        open_file.close()

        response_dict = ZenodoAPI.validate_response(r, ResponseStatus.Created)

        self.get_remote_files()

        return ZenodoFile(response_dict)

    def delete_file_by_id(self, file_id):
        """Deletes the file with a certain ID in the deposit.

        Args:
            file_id:
                The id of the file to delete.

        Returns:
             True if success.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """
        link = self.base_url + "/api/deposit/depositions/%s/files/%s" % (
            self.id,
            file_id,
        )

        r = requests.delete(link, params=self.params)

        ZenodoAPI.validate_response(r, ResponseStatus.NoContent)

        self.get_remote_files()

        return True

    def update_file_by_id(self, file_id, new_file):
        """Updates a existent file with the new version.

        Args:
            file_id:
                The id of the file to delete.
            new_file:
                 The new version of the file.

        Returns:
             The new created @ZenodoFile object.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """
        self.delete_file_by_id(file_id)
        return self.create_file(new_file)

    def delete_file(self, file_name):
        """Deletes a file in a deposit given its name

        Args:
            file_name:
                The name of the file to delete.

        Returns:
             True on success.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """
        file_id = self.get_files_id_by_name(file_name)
        if file_id:
            self.delete_file_by_id(file_id)

    def update_file(self, file_name, new_file):
        """Updates a file in a deposit given its name

        Args:
            file_name:
                The name of the file to delete.
            new_file:
                 The new version of the file.

        Returns:
             The updated @ZenodoFile object.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """
        file_id = self.get_files_id_by_name(file_name)
        if file_id:
            self.update_file_by_id(file_id, new_file)


class ZenodoRecord(ZenodoDeposit):
    """Class for the @ZenodoRecord. Holds the statistics (@ZenodoRecordStats) of a published deposit."""

    def __init__(self, entry_dict, base_url, access_token):
        super().__init__(entry_dict, base_url, access_token)
        self.owners = self._get_attribute(entry_dict, "owners")
        self.revision = self._get_attribute(entry_dict, "revision")
        self.stats = ZenodoRecordStats(self._get_attribute(entry_dict, "stats"))
        self.updated = self._get_attribute(entry_dict, "updated")

    def print_stats(self):
        """Prints the dictionary."""
        print(self.stats.to_dict())


class ZenodoRecordStats(ZenodoEntry):
    """Class holding the statistics of a @ZenodoRecord."""

    def __init__(self, entry_dict):
        super().__init__(entry_dict, "", "")
        self.downloads = self._get_attribute(entry_dict, "downloads")
        self.unique_downloads = self._get_attribute(entry_dict, "unique_downloads")
        self.unique_views = self._get_attribute(entry_dict, "unique_views")
        self.version_downloads = self._get_attribute(entry_dict, "version_downloads")
        self.version_unique_downloads = self._get_attribute(
            entry_dict, "version_unique_downloads"
        )
        self.version_unique_views = self._get_attribute(
            entry_dict, "version_unique_views"
        )
        self.version_views = self._get_attribute(entry_dict, "version_views")
        self.version_volume = self._get_attribute(entry_dict, "version_volume")
        self.views = self._get_attribute(entry_dict, "views")
        self.volume = self._get_attribute(entry_dict, "volume")


class ZenodoDefaultUrl(Enum):
    sandbox_url = "https://sandbox.zenodo.org/"
    url = "https://zenodo.org/"


class ZenodoAPI:
    """
    Zenodo API. Querying the ZenodoAPI.
    """

    def __init__(self, base_url=ZenodoDefaultUrl.url.value, access_token=None):
        """Inits the object given a base_url and an access_token.

        Args:
            base_url:
                base URL for all queries
            access_token:
                The authentication token needed to perform operations.
        """
        self.base_url = base_url
        self.params = {"access_token": ""}

        if access_token:
            self.params["access_token"] = access_token

    @staticmethod
    def validate_response(response, expected_response_code=None):
        """Validates the response from a request.

        Args:
            response:
                The response of a request.
            expected_response_code:
                The expected response specified in the API

        Returns:
            JSON response body or "{'true'}" if no body included in response.

        Raises:
            InvalidResponseStatusError: If query response status other than expected.
        """
        # todo: nice feedback when operation not permitted
        status_code = ResponseStatus(response.status_code)
        if not expected_response_code:
            expected_response_code = status_code

        if status_code in [
            ResponseStatus.OK,
            ResponseStatus.Accepted,
            ResponseStatus.Created,
        ]:
            if status_code != expected_response_code:
                raise InvalidResponseStatusError(
                    "Expected %s got %s"
                    % (expected_response_code.name, status_code.name)
                )
            return response.json()
        elif status_code == ResponseStatus.NoContent:
            if status_code != expected_response_code:
                raise InvalidResponseStatusError(
                    "Expected %s got %s"
                    % (expected_response_code.name, status_code.name)
                )
            return json.dumps(True)
        else:
            print("Error: %s" % status_code.name)
            if status_code != ResponseStatus.InternalServerError:
                print("Detailed message:")
                print(response.json()["message"])
                if response.json()["errors"]:
                    print(response.json()["errors"])

        raise InvalidResponseStatusError(
            "Error '%s' occurred. See Log for detailed information!" % status_code.name
        )

    # ############# Deposits #############

    def deposit_get(
        self,
        deposit_id=None,
        q="",
        status=DepositStatus.PUBLISHED,
        sort=SortOrder.BEST_MATCH,
    ):
        """Retrieve a deposit.

        Args:
            deposit_id:
                The id of the deposit. If None specified other params define a search request.
            q:
                The search query. Holds keywords to search for in the deposit metadata.
            status:
                The deposit status. See @DepositStatus
            sort:
                Sorting of the result. See @SortOrder

        Returns:
            A list of @ZenodoDeposit found. Empty if none found.
        """

        link = self.base_url + "/api/deposit/depositions"

        if deposit_id:
            link = link + "/%s" % deposit_id
            params = self.params
        else:
            params = {
                **{"q": q, "status": status.value, "sort": sort.value},
                **self.params,
            }

        r = requests.get(link, params=params)

        response_dict = self.validate_response(r, ResponseStatus.OK)

        deposit_list = []
        if isinstance(response_dict, list):
            for deposit_dict in response_dict:
                deposit_list.append(
                    ZenodoDeposit(
                        deposit_dict, self.base_url, self.params["access_token"]
                    )
                )
        else:
            deposit_list.append(
                ZenodoDeposit(response_dict, self.base_url, self.params["access_token"])
            )

        return deposit_list

    def deposit_create(self):
        """Creates an empty deposit (already uploaded).

        Returns:
            A ZenodoDeposit object.
        """

        link = self.base_url + "/api/deposit/depositions"

        r = requests.post(link, params=self.params, json={})

        response_dict = self.validate_response(r, ResponseStatus.Created)

        return ZenodoDeposit(response_dict, self.base_url, self.params["access_token"])

    def deposit_create_with_prereserve_doi(self, metadata):
        deposit = self.deposit_create()
        deposit.update(metadata)

        return deposit

    # ############# Records #############

    # todo: write tests
    def records_get(
        self,
        record_id=None,
        q="",
        status=DepositStatus.PUBLISHED,
        sort=SortOrder.BEST_MATCH,
        record_type=UploadType.SOFTWARE,
    ):
        """Retrieve a record or searches through published records.

        Args:
            record_id:
                The id of the record to retrieve. If non specified other parameters define search criteria.
            q:
                The search query. Holds keywords to search for in the deposit metadata.
            status:
                The deposit status. See @DepositStatus.
            sort:
                Sorting of the result. See @SortOrder.
            record_type:
                Record type of the record. See @UploadType.

        Returns:
            Returns the @ZenodoRecord object.
        """

        link = self.base_url + "/api/records"

        if record_id:
            link = link + "/%s" % str(record_id)
            params = self.params
        else:
            params = {
                **{
                    "q": q,
                    "status": status.value,
                    "sort": sort.value,
                    "type": record_type.value,
                },
                **self.params,
            }

        r = requests.get(link, params=params)

        response_dict = self.validate_response(r, ResponseStatus.OK)

        record_list = []
        if isinstance(response_dict, list):
            for record_dict in response_dict:
                record_list.append(
                    ZenodoRecord(
                        record_dict, self.base_url, self.params["access_token"]
                    )
                )
        else:
            record_list.append(
                ZenodoRecord(response_dict, self.base_url, self.params["access_token"])
            )

        return record_list
