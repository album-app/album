import unittest
import os
from utils.zenodo_api import ZenodoAPI


class TestHipsCommon(unittest.TestCase):
    """Base class for all Unittest using a hips object"""

    @classmethod
    def setUpClass(cls):
        """On inherited classes, run our `setUp` method"""
        if cls is not TestHipsCommon and cls.setUp is not TestHipsCommon.setUp:
            orig_set_up = cls.setUp

            def set_up_override(self, *args, **kwargs):
                TestHipsCommon.setUp(self)
                return orig_set_up(self, *args, **kwargs)

            cls.setUp = set_up_override

    def setUp(self):
        """Could initialize default values for each test class. use `_<name>` to skip property setting."""
        self.attrs = {}

    @property
    def main(self):
        return self._main

    @main.setter
    def main(self, val):
        self._main = val
        self.attrs["main"] = val

    @property
    def init(self):
        return self._init

    @init.setter
    def init(self, val):
        self._init = val
        self.attrs["init"] = val

    @property
    def args(self):
        return self._args

    @args.setter
    def args(self, val):
        self._args = val
        self.attrs["args"] = val

    @property
    def tested_hips_version(self):
        return self._tested_hips_version

    @tested_hips_version.setter
    def tested_hips_version(self, val):
        self._tested_hips_version = val
        self.attrs["tested_hips_version"] = val

    @property
    def min_hips_version(self):
        return self._min_hips_version

    @min_hips_version.setter
    def min_hips_version(self, val):
        self._min_hips_version = val
        self.attrs["min_hips_version"] = val

    @property
    def license(self):
        return self._license

    @license.setter
    def license(self, val):
        self._license = val
        self.attrs["license"] = val

    @property
    def git_repo(self):
        return self._git_repo

    @git_repo.setter
    def git_repo(self, val):
        self._git_repo = val
        self.attrs["git_repo"] = val

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, val):
        self._description = val
        self.attrs["description"] = val

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, val):
        self._version = val
        self.attrs["version"] = val

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        self._name = val
        self.attrs["name"] = val

    @property
    def dependencies(self):
        return self._dependencies

    @dependencies.setter
    def dependencies(self, val):
        self._dependencies = val
        self.attrs["dependencies"] = val

    @property
    def attrs(self):
        return self._attrs

    @attrs.setter
    def attrs(self, val):
        self._attrs = val


class TestUtilsCommon(unittest.TestCase):
    """Base class for all Unittests including the ZenodoAPI"""

    access_token_environment_name = 'ZENODO_ACCESS_TOKEN'
    base_url = 'https://sandbox.zenodo.org/'

    @classmethod
    def setUpClass(cls):
        """On inherited classes, run our `setUp` method"""
        if cls is not TestUtilsCommon and cls.setUp is not TestUtilsCommon.setUp:
            orig_set_up = cls.setUp

            def set_up_override(self, *args, **kwargs):
                TestUtilsCommon.setUp(self)
                return orig_set_up(self, *args, **kwargs)

            cls.setUp = set_up_override

    def set_environment_attribute(self, attr_name, env_name):
        try:
            setattr(self, attr_name, os.environ[env_name])
        except KeyError:
            raise KeyError("Environment variable %s not set. Please set environment variable to run tests!" % env_name)

    def setUp(self):
        """Could initialize default values for each test class. use `_<name>` to skip property setting."""

        self.access_token = None

        self.set_environment_attribute("access_token", self.access_token_environment_name)

        # create a test deposit
        self.zenodoAPI = ZenodoAPI(self.base_url, self.access_token)
        self.test_deposit = self.zenodoAPI.deposit_create()

    def tearDown(self):
        assert self.test_deposit.delete()
