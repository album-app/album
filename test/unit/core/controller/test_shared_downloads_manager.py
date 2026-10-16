import json
import logging
import sys
import unittest
from io import StringIO
from pathlib import Path
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import MagicMock, patch

import pooch

from album.core.controller.shared_downloads_manager import DownloadManager
from album.core.utils.file_lock import FileLock
from album.runner.core.model.solution import Solution

SHA256 = "9d88224e3be283730af0f4388573eb3019bb0aa40c0b77a8350019fb34afe9d8"

# one resource per scope, the viewer exists once per platform
RESOURCE_FILE = (
    """resources:
  model:
    name: model.pt
    url: https://example.org/model.pt
    hash: "sha256:%s"
    scope: catalog
  viewer_linux:
    name: viewer.tar.xz
    url: https://example.org/viewer-linux.tar.xz
    os: linux
    scope: solution
  viewer_win32:
    name: viewer.zip
    url: https://example.org/viewer-win32.zip
    os: win32
    scope: solution
  viewer_darwin:
    name: viewer.dmg
    url: https://example.org/viewer-darwin.dmg
    os: darwin
    scope: solution
  readme:
    name: README.md
    url: https://example.org/README.md
"""
    % SHA256
)


class TestDownloadManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        self.download_manager: DownloadManager = (
            self.album_controller.download_manager()
        )
        self.installation_path = Path(self.tmp_dir.name).joinpath("installation")
        self.shared_path = self.album_controller.configuration().shared_resources_path()

    def tearDown(self):
        super().tearDown()

    def _solution(self, resource_file=None):
        attrs = self.get_solution_dict()
        if resource_file is not None:
            attrs["dependencies"] = {"resource_file": resource_file}
        solution = Solution(attrs)
        solution.installation().set_installation_path(self.installation_path)
        return solution

    @staticmethod
    def _collection_solution(solution, catalog_name="my_catalog"):
        collection_solution = MagicMock()
        collection_solution.loaded_solution.return_value = solution
        collection_solution.catalog.return_value.name.return_value = catalog_name
        return collection_solution

    def _resource(self, name, **kwargs):
        """Build a resource entry as it looks after the paths were resolved."""
        resource = {
            "url": "https://example.org/%s" % name,
            "name": name,
            "hash": None,
            "os": sys.platform,
            "scope": "global",
            "path": str(Path(self.tmp_dir.name).joinpath(name)),
        }
        resource.update(kwargs)
        return resource

    def _json_path(self):
        return self.installation_path.joinpath(
            "icache", "tsg_tsn_tsv_resource_file.json"
        )

    # load and validate

    def test__load_resources_no_resource_file(self):
        self.assertIsNone(self.download_manager._load_resources(self._solution()))

        solution = Solution(dict(self.get_solution_dict(), dependencies={}))
        self.assertIsNone(self.download_manager._load_resources(solution))

    def test__load_resources_forms(self):
        resource_dict = {
            "resources": {"a": {"name": "a.txt", "url": "https://e.org/a"}}
        }
        resource_yml = "resources:\n  a:\n    name: a.txt\n    url: https://e.org/a\n"
        resource_path = Path(self.tmp_dir.name).joinpath("resources.yml")
        resource_path.write_text(resource_yml, encoding="utf-8")
        expected = {
            "resources": {
                "a": {
                    "name": "a.txt",
                    "url": "https://e.org/a",
                    "hash": None,
                    "os": None,
                    "scope": "global",
                }
            }
        }

        for resource_file in [
            resource_dict,
            resource_yml,
            StringIO(resource_yml),
            "resources.yml",
        ]:
            with self.subTest(resource_file=type(resource_file).__name__):
                resources_dict = self.download_manager._load_resources(
                    self._solution(resource_file), Path(self.tmp_dir.name)
                )
                self.assertEqual(expected, resources_dict)

        # the intermediate yml file in the tmp folder is gone
        self.assertEqual(
            [],
            list(
                self.album_controller.configuration().tmp_path().glob("*resource_file*")
            ),
        )

    def test__load_resources_utf8(self):
        description = "Zellkerngröße in µm (顕微鏡)"
        resource_file = (
            "resources:\n"
            "  model:\n"
            '    name: "model.zip"\n'
            '    url: "https://example.org/model.zip"\n'
            '    description: "%s"\n' % description
        )

        resources_dict = self.download_manager._load_resources(
            self._solution(resource_file)
        )

        # the non-ASCII characters survive, independent of the platform encoding
        self.assertEqual(
            description, resources_dict["resources"]["model"]["description"]
        )

    def test__load_resources_invalid_form(self):
        with self.assertRaises(TypeError) as e:
            self.download_manager._load_resources(self._solution(42))
        self.assertIn("resource_file must either contain", str(e.exception))

    def test__load_resources_invalid_yaml(self):
        with self.assertRaises(ValueError) as e:
            self.download_manager._load_resources(
                self._solution("resources:\n  a: [\n")
            )
        self.assertIn(
            'The resource_file of "tsg:tsn:tsv" is not valid YAML', str(e.exception)
        )

    def test__load_resources_invalid_content(self):
        valid = {"name": "a.txt", "url": "https://e.org/a"}
        cases = {
            "not a mapping": "- resources: none\n",
            "no resources": {"files": {}},
            "resources no mapping": {"resources": ["a"]},
            "missing url": {"resources": {"a": {"name": "a.txt"}}},
            "missing name": {"resources": {"a": {"url": "https://e.org/a"}}},
            "empty name": {"resources": {"a": dict(valid, name="")}},
            "unknown url scheme": {
                "resources": {"a": dict(valid, url="file:///a.txt")}
            },
            "unknown scope": {"resources": {"a": dict(valid, scope="catalgo")}},
            "unknown os": {"resources": {"a": dict(valid, os="windows")}},
            "hash no hex": {"resources": {"a": dict(valid, hash="md5:xyz")}},
            "hash no string": {"resources": {"a": dict(valid, hash=1234)}},
        }
        for case, resource_file in cases.items():
            with self.subTest(case=case):
                with self.assertRaises(ValueError) as e:
                    self.download_manager._load_resources(self._solution(resource_file))
                self.assertIn(
                    'The resource_file of "tsg:tsn:tsv" is invalid', str(e.exception)
                )

    def test__load_resources_name_with_folder(self):
        for name in ["../a.txt", "sub/a.txt", "/a.txt", "sub\\a.txt", "C:a.txt", ".."]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as e:
                    self.download_manager._load_resources(
                        self._solution(
                            {
                                "resources": {
                                    "a": {"name": name, "url": "https://e.org/a"}
                                }
                            }
                        )
                    )
                self.assertIn("must be a plain file name", str(e.exception))

    def test__load_resources_valid_values(self):
        resource_file = {
            "resources": {
                "a": {
                    "name": "a.txt",
                    "url": "doi:10.5281/zenodo.3939050/a.txt",
                    "hash": "md5:70e2afd3fd7e336ae478b1e740a5f08e",
                    "os": "darwin",
                    "scope": "solution",
                },
                "b": {"name": "b", "url": "ftp://e.org/b", "hash": SHA256},
            }
        }

        resources_dict = self.download_manager._load_resources(
            self._solution(resource_file)
        )

        self.assertEqual(
            resource_file["resources"]["a"], resources_dict["resources"]["a"]
        )
        self.assertEqual(
            dict(resource_file["resources"]["b"], os=None, scope="global"),
            resources_dict["resources"]["b"],
        )

    # paths

    def test__set_paths_in_dict(self):
        resources_dict = self.download_manager._load_resources(
            self._solution(RESOURCE_FILE)
        )

        self.download_manager._set_paths_in_dict(
            resources_dict, self.installation_path, "my_catalog", self.shared_path
        )

        resources = resources_dict["resources"]
        model = resources["model"]
        self.assertEqual(
            str(
                self.shared_path.joinpath(
                    "catalog",
                    "my_catalog",
                    DownloadManager._get_content_folder_name(model),
                    "model.pt",
                )
            ),
            model["path"],
        )
        readme = resources["readme"]
        self.assertEqual(
            str(
                self.shared_path.joinpath(
                    "global",
                    DownloadManager._get_content_folder_name(readme),
                    "README.md",
                )
            ),
            readme["path"],
        )
        # resources without "os" are written with the current platform, album-solution-api filters on it
        self.assertEqual(sys.platform, readme["os"])
        self.assertEqual(sys.platform, model["os"])

        for platform in ["linux", "win32", "darwin"]:
            viewer = resources["viewer_%s" % platform]
            self.assertEqual(platform, viewer["os"])
            if platform == sys.platform:
                self.assertEqual(
                    str(
                        self.installation_path.joinpath(
                            "resources",
                            DownloadManager._get_content_folder_name(viewer),
                            viewer["name"],
                        )
                    ),
                    viewer["path"],
                )
            else:
                self.assertIsNone(viewer["path"])

    def test__get_content_folder_name(self):
        def folder(**kwargs):
            return DownloadManager._get_content_folder_name(
                dict({"url": "https://e.org/a", "hash": None}, **kwargs)
            )

        # same content, written differently
        self.assertEqual(folder(hash=SHA256), folder(hash="SHA256:%s" % SHA256.upper()))
        # a different url does not matter for pinned content
        self.assertEqual(
            folder(hash=SHA256), folder(hash=SHA256, url="https://mirror.org/a")
        )
        # different content
        self.assertNotEqual(folder(hash=SHA256), folder(hash="md5:%s" % SHA256[:32]))
        # without a hash the url decides
        self.assertEqual(folder(), folder())
        self.assertNotEqual(folder(), folder(url="https://e.org/b"))
        self.assertNotEqual(folder(), folder(hash=SHA256))

    def test__set_paths_in_dict_same_name_different_content(self):
        """Two solutions asking for the same file name with different content do not share a file."""
        resources_dict = {
            "resources": {
                "a": self._resource("model.pt", url="https://one.org/model.pt"),
                "b": self._resource("model.pt", url="https://two.org/model.pt"),
            }
        }

        self.download_manager._set_paths_in_dict(
            resources_dict, self.installation_path, "my_catalog", self.shared_path
        )

        self.assertNotEqual(
            resources_dict["resources"]["a"]["path"],
            resources_dict["resources"]["b"]["path"],
        )

    # retrieve

    @patch.object(DownloadManager, "_show_progressbar", return_value=False)
    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test__retrieve_resources_from_dict_with_hash(
        self, retrieve_mock, file_hash_mock, _
    ):
        # prepare
        resource = self._resource("res_a", hash="md5:abc")
        resources_dict = {"resources": {"a": resource}}

        # call
        self.download_manager._retrieve_resources_from_dict(resources_dict)

        # assert
        retrieve_mock.assert_called_once_with(
            url="https://example.org/res_a",
            known_hash="md5:abc",
            fname="res_a",
            path=self.tmp_dir.name,
            progressbar=False,
        )
        file_hash_mock.assert_not_called()
        logs = self.get_logs_as_string()
        self.assertIn('Resource "a" is available at %s.' % resource["path"], logs)
        self.assertNotIn("has no hash", logs)

    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test__retrieve_resources_from_dict_without_hash(
        self, retrieve_mock, file_hash_mock
    ):
        """A resource without a hash is retrieved and the hash to pin it is reported."""
        # prepare
        file_hash_mock.return_value = "0123456789abcdef"
        resource = self._resource("res_a")
        resources_dict = {"resources": {"a": resource}}

        # call
        self.download_manager._retrieve_resources_from_dict(resources_dict)

        # assert
        retrieve_mock.assert_called_once()
        self.assertIsNone(retrieve_mock.call_args.kwargs["known_hash"])
        file_hash_mock.assert_called_once_with(resource["path"])
        logs = self.get_logs_as_string()
        self.assertIn('Resource "a" has no hash', logs)
        self.assertIn('hash: "sha256:0123456789abcdef"', logs)

    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test__retrieve_resources_from_dict_download_fails(
        self, retrieve_mock, file_hash_mock
    ):
        """A failed download raises, the remaining resources are not retrieved."""
        # prepare
        retrieve_mock.side_effect = ConnectionError("no route to host")
        resources_dict = {
            "resources": {
                "a": self._resource("res_a"),
                "b": self._resource("res_b"),
            }
        }

        # call
        with self.assertRaises(RuntimeError) as e:
            self.download_manager._retrieve_resources_from_dict(resources_dict)

        # assert
        self.assertEqual(
            'Could not retrieve resource "a" from https://example.org/res_a: no route to host',
            str(e.exception),
        )
        retrieve_mock.assert_called_once()
        file_hash_mock.assert_not_called()
        self.assertNotIn("is available at", self.get_logs_as_string())

    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test__retrieve_resources_from_dict_hash_mismatch(self, retrieve_mock):
        retrieve_mock.side_effect = ValueError(
            "SHA256 hash of downloaded file (abc) does not match the known hash: expected def."
        )
        resources_dict = {"resources": {"a": self._resource("res_a", hash="def")}}

        with self.assertRaises(RuntimeError) as e:
            self.download_manager._retrieve_resources_from_dict(resources_dict)

        self.assertIn("does not match the known hash", str(e.exception))

    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test__retrieve_resources_from_dict_skips_other_os(
        self, retrieve_mock, file_hash_mock
    ):
        # prepare: resources for other platforms have no path
        other_os = "not-" + sys.platform
        resources_dict = {
            "resources": {"a": self._resource("res_a", os=other_os, path=None)}
        }

        # call
        self.download_manager._retrieve_resources_from_dict(resources_dict)

        # assert
        retrieve_mock.assert_not_called()
        file_hash_mock.assert_not_called()

    def test__retrieve_resources_from_dict_quiets_pooch(self):
        pooch_logger = pooch.get_logger()
        records = []
        handler = logging.Handler()
        handler.emit = records.append
        pooch_handlers = pooch_logger.handlers
        pooch_logger.handlers = [handler]

        def retrieve(**kwargs):
            pooch_logger.info("Downloading data from somewhere")
            pooch_logger.warning("pooch warns")

        try:
            # pooch has logged before, so its logger has cached that info is enabled
            pooch_logger.info("before")
            with patch(
                "album.core.controller.shared_downloads_manager.pooch.retrieve",
                side_effect=retrieve,
            ):
                self.download_manager._retrieve_resources_from_dict(
                    {"resources": {"a": self._resource("res_a", hash="md5:abc")}}
                )
            pooch_logger.info("after")
        finally:
            pooch_logger.handlers = pooch_handlers

        self.assertEqual(
            ["before", "pooch warns", "after"], [r.getMessage() for r in records]
        )

    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    def test__retrieve_resources_from_dict_locks_shared_resources(self, _):
        resources_dict = {
            "resources": {
                "global": self._resource("res_a", scope="global"),
                "catalog": self._resource("res_b", scope="catalog"),
                "solution": self._resource("res_c", scope="solution"),
            }
        }
        held = {}

        def retrieve(**kwargs):
            # which resource is retrieved, and is the lock of its content folder held?
            key = next(
                k
                for k, r in resources_dict["resources"].items()
                if r["name"] == kwargs["fname"]
            )
            lock = self.download_manager._get_resource_lock(
                resources_dict["resources"][key]
            )
            held[key] = isinstance(lock, FileLock) and lock.is_held_by_current_thread()

        # call
        with patch(
            "album.core.controller.shared_downloads_manager.pooch.retrieve",
            side_effect=retrieve,
        ):
            self.download_manager._retrieve_resources_from_dict(resources_dict)

        # assert: shared resources are retrieved holding their lock, released afterwards
        self.assertEqual({"global": True, "catalog": True, "solution": False}, held)
        lock = self.download_manager._get_resource_lock(
            resources_dict["resources"]["global"]
        )
        self.assertFalse(lock.is_held_by_current_thread())
        # the lock files are in the lock folder of album, named after the content folder
        content_folder = Path(self.tmp_dir.name).name
        lock_folder = (
            self.album_controller.configuration()
            .base_cache_path()
            .joinpath("locks", "resources")
        )
        self.assertTrue(
            lock_folder.joinpath("global", content_folder + ".lock").is_file()
        )
        self.assertTrue(
            lock_folder.joinpath("catalog", content_folder + ".lock").is_file()
        )
        # the same lock for the same content folder
        self.assertIs(
            lock,
            self.download_manager._get_resource_lock(
                self._resource("other_name", scope="global")
            ),
        )

    def test__show_progressbar(self):
        tty = MagicMock()
        tty.isatty.return_value = True
        with patch("sys.stderr", tty):
            with patch("importlib.util.find_spec", return_value=None):
                # pooch raises for a progress bar without tqdm
                self.assertFalse(DownloadManager._show_progressbar())
            with patch("importlib.util.find_spec", return_value=MagicMock()):
                self.assertTrue(DownloadManager._show_progressbar())
                tty.isatty.return_value = False
                self.assertFalse(DownloadManager._show_progressbar())

    # download_resources

    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test_download_resources(self, retrieve_mock, file_hash_mock):
        file_hash_mock.return_value = "0123456789abcdef"
        solution = self._solution(RESOURCE_FILE)

        json_path = self.download_manager.download_resources(
            self._collection_solution(solution)
        )

        # the json file is where album-solution-api (get_resources_dict) reads it
        self.assertEqual(self._json_path(), json_path)
        resources = json.loads(json_path.read_text(encoding="utf-8"))["resources"]

        # model, readme and the viewer of this platform
        self.assertEqual(3, retrieve_mock.call_count)
        retrieved = {
            str(Path(c.kwargs["path"]).joinpath(c.kwargs["fname"]))
            for c in retrieve_mock.call_args_list
        }
        downloaded = {
            key: resource["path"]
            for key, resource in resources.items()
            if resource["path"] is not None
        }
        self.assertEqual(
            {"model", "readme", "viewer_%s" % sys.platform}, set(downloaded.keys())
        )
        self.assertEqual(set(downloaded.values()), retrieved)
        self.assertTrue(
            resources["model"]["path"].startswith(
                str(self.shared_path.joinpath("catalog", "my_catalog"))
            )
        )

    def test_download_resources_no_resource_file(self):
        self.assertIsNone(
            self.download_manager.download_resources(
                self._collection_solution(self._solution())
            )
        )
        self.assertFalse(self._json_path().exists())

    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test_download_resources_failure_writes_no_json(self, retrieve_mock):
        retrieve_mock.side_effect = ConnectionError("no route to host")

        with self.assertRaises(RuntimeError):
            self.download_manager.download_resources(
                self._collection_solution(self._solution(RESOURCE_FILE))
            )

        self.assertFalse(self._json_path().exists())

    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test_download_resources_overwrites_json(self, _):
        """The json file always reflects the current resource file, it is never reused."""
        solution = self._solution(
            {
                "resources": {
                    "a": {"name": "a.txt", "url": "https://e.org/a", "hash": SHA256}
                }
            }
        )
        json_path = self._json_path()
        json_path.parent.mkdir(parents=True)
        json_path.write_text(json.dumps({"resources": {"old": {}}}), encoding="utf-8")

        self.download_manager.download_resources(self._collection_solution(solution))

        self.assertEqual(
            ["a"], list(json.loads(json_path.read_text(encoding="utf-8"))["resources"])
        )

    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test_download_resources_resource_file_from_solution_folder(self, _):
        folder = Path(self.tmp_dir.name).joinpath("solution")
        folder.mkdir()
        folder.joinpath("resources.yml").write_text(
            "resources:\n  a:\n    name: a.txt\n    url: https://e.org/a\n    hash: %s\n"
            % SHA256,
            encoding="utf-8",
        )
        solution = self._solution("resources.yml")
        # installed from the folder, wherever album runs
        collection_solution = self._collection_solution(solution)
        collection_solution.is_single_file.return_value = False
        collection_solution.path.return_value = folder.joinpath("solution.py")

        json_path = self.download_manager.download_resources(collection_solution)

        self.assertEqual(
            ["a"], list(json.loads(json_path.read_text(encoding="utf-8"))["resources"])
        )

    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test_download_resources_resource_list_written_by_deploy(self, _):
        # a deployed solution: the resource file it names is not on this computer
        package_path = Path(self.tmp_dir.name).joinpath("package")
        package_path.mkdir()
        package_path.joinpath("solution.resources.yml").write_text(
            "resources:\n  b:\n    name: b.txt\n    url: https://e.org/b\n    hash: %s\n"
            % SHA256,
            encoding="utf-8",
        )
        solution = self._solution("/not/on/this/computer/resources.yml")
        solution.installation().set_package_path(package_path)
        collection_solution = self._collection_solution(solution)
        collection_solution.is_single_file.return_value = False
        collection_solution.path.return_value = package_path.joinpath("solution.py")

        json_path = self.download_manager.download_resources(collection_solution)

        self.assertEqual(
            ["b"], list(json.loads(json_path.read_text(encoding="utf-8"))["resources"])
        )

    # check_resources

    def test_check_resources_no_resource_file(self):
        self.download_manager.check_resources(self._solution())

        self.assertNotIn("WARNING", self.get_logs_as_string())

    def test_check_resources_pinned(self):
        self.download_manager.check_resources(
            self._solution(
                {
                    "resources": {
                        "a": {
                            "name": "a.txt",
                            "url": "https://e.org/a",
                            "hash": SHA256,
                        },
                        "b": {
                            "name": "b.txt",
                            "url": "https://e.org/b",
                            "scope": "solution",
                        },
                    }
                }
            )
        )

        self.assertNotIn("WARNING", self.get_logs_as_string())

    def test_check_resources_unpinned_shared(self):
        self.download_manager.check_resources(self._solution(RESOURCE_FILE))

        logs = self.get_logs_as_string()
        self.assertIn(
            'Resource "readme" of "tsg:tsn:tsv" is shared, but has no hash', logs
        )
        self.assertNotIn('"model"', logs)
        self.assertNotIn('"viewer_', logs)

    def test_check_resources_file_in_solution_folder(self):
        Path(self.tmp_dir.name).joinpath("resources.yml").write_text(
            "resources:\n  a:\n    name: a.txt\n    url: https://e.org/a\n    scope: solution\n",
            encoding="utf-8",
        )

        self.download_manager.check_resources(
            self._solution("resources.yml"), Path(self.tmp_dir.name)
        )

        self.assertNotIn("WARNING", self.get_logs_as_string())

    def test_check_resources_file_outside_solution_folder(self):
        resource_path = Path(self.tmp_dir.name).joinpath("resources.yml")
        resource_path.write_text(
            "resources:\n  a:\n    name: a.txt\n    url: https://e.org/a\n    scope: solution\n",
            encoding="utf-8",
        )
        solution_folder = Path(self.tmp_dir.name).joinpath("solution")
        solution_folder.mkdir()

        # an existing file is taken wherever it is
        for resource_file, folder in [
            (str(resource_path), solution_folder),
            ("../resources.yml", solution_folder),
            (str(resource_path), None),
        ]:
            with self.subTest(resource_file=resource_file, folder=folder):
                self.download_manager.check_resources(
                    self._solution(resource_file), folder
                )

        for resource_file, folder, message in [
            ("missing.yml", solution_folder, "does not exist"),
            # a solution given as a single file has no folder for relative paths
            ("resources.yml", None, "is a path"),
        ]:
            with self.subTest(resource_file=resource_file, folder=folder):
                with self.assertRaises(TypeError) as e:
                    self.download_manager.check_resources(
                        self._solution(resource_file), folder
                    )
                self.assertIn(
                    f'resource_file "{resource_file}" {message}',
                    str(e.exception),
                )

    def test_check_resources_invalid(self):
        with self.assertRaises(ValueError):
            self.download_manager.check_resources(
                self._solution({"resources": {"a": {"name": "a.txt"}}})
            )


if __name__ == "__main__":
    unittest.main()
