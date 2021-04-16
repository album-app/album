import tempfile
import shutil
import unittest
import os
import git

from xdg import xdg_cache_home

from hips_utils.zenodo_api import ZenodoAPI, ZenodoDefaultUrl


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


class TestZenodoCommon(unittest.TestCase):
    """Base class for all Unittests including the ZenodoAPI"""

    access_token_environment_name = 'ZENODO_ACCESS_TOKEN'
    base_url = ZenodoDefaultUrl.sandbox_url.value

    @classmethod
    def setUpClass(cls):
        """On inherited classes, run our `setUp` method"""
        if cls is not TestZenodoCommon and cls.setUp is not TestZenodoCommon.setUp:
            orig_set_up = cls.setUp

            def set_up_override(self, *args, **kwargs):
                TestZenodoCommon.setUp(self)
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
        if hasattr(self, "test_deposit2"):
            assert self.test_deposit2.delete()


class TestGitCommon(TestHipsCommon):
    """Base class for all Unittest using a hips object"""

    @classmethod
    def setUpClass(cls):
        """On inherited classes, run our `setUp` method"""
        if cls is not TestGitCommon and cls.setUp is not TestGitCommon.setUp:
            orig_set_up = cls.setUp

            def set_up_override(self, *args, **kwargs):
                TestGitCommon.setUp(self)
                return orig_set_up(self, *args, **kwargs)

            cls.setUp = set_up_override

    def setUp(self):
        """Could initialize default values for each test class. use `_<name>` to skip property setting."""
        self.attrs = {}

    def tearDown(self) -> None:
        basepath = xdg_cache_home().joinpath("testGitRepo")
        shutil.rmtree(basepath, ignore_errors=True)

    def create_tmp_repo(self, commit_solution_file=True, create_test_branch=False):
        basepath = xdg_cache_home().joinpath("testGitRepo")
        shutil.rmtree(basepath, ignore_errors=True)

        repo = git.Repo.init(path=basepath)

        # necessary for CI
        repo.config_writer().set_value("user", "name", "myusername").release()
        repo.config_writer().set_value("user", "email", "myemail").release()

        # initial commit
        init_file = tempfile.NamedTemporaryFile(
            dir=os.path.join(str(repo.working_tree_dir)),
            delete=False
        )
        repo.index.add([os.path.basename(init_file.name)])
        repo.git.commit('-m', "init", '--no-verify')

        if commit_solution_file:
            os.makedirs(os.path.join(str(repo.working_tree_dir), "solutions"), exist_ok=True)
            tmp_file = tempfile.NamedTemporaryFile(
                dir=os.path.join(str(repo.working_tree_dir), "solutions"),
                delete=False
            )
            repo.index.add([os.path.join("solutions", os.path.basename(tmp_file.name))])
        else:
            tmp_file = tempfile.NamedTemporaryFile(dir=str(repo.working_tree_dir))
            repo.index.add([os.path.basename(tmp_file.name)])

        repo.git.commit('-m', "added %s " % tmp_file.name, '--no-verify')

        if create_test_branch:
            new_head = repo.create_head("test_branch")
            new_head.ref = repo.heads["master"]  # manually point to master
            new_head.checkout()

            # add file to new head
            tmp_file = tempfile.NamedTemporaryFile(
                dir=os.path.join(str(repo.working_tree_dir), "solutions"), delete=False
            )
            repo.index.add([tmp_file.name])
            repo.git.commit('-m', "branch added %s " % tmp_file.name, '--no-verify')

            # checkout master again
            repo.heads["master"].checkout()

        self.repo = repo

        return tmp_file.name
