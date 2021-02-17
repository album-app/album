import unittest


class TestHipsCommon(unittest.TestCase):

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