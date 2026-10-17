import hashlib
import json
import sys
import threading
import time
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from test.test_common import TEST_ALBUM_API_VERSION
from unittest.mock import patch

SOLUTION = """import json

from album.runner.api import setup


def album_run():
    from album.runner.api import get_resources_dict

    print("RESOURCES=" + json.dumps(get_resources_dict(os_specific=True)))


setup(
    group="group",
    name="%(name)s",
    version="0.1.0",
    album_api_version="%(api_version)s",
    run=album_run,
    dependencies=%(dependencies)s,
)
"""


class ResourceServer:
    """Serve the files of a folder on localhost and record the requested paths."""

    def __init__(self, folder: Path):
        requests = self.requests = []
        # seconds to wait before each response, so that downloads overlap
        self.delay = 0.0
        resource_server = self

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(folder), **kwargs)

            def do_GET(self):
                requests.append(self.path)
                time.sleep(resource_server.delay)
                super().do_GET()

            def log_message(self, format, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%s" % self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def close(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()


class TestIntegrationSharedResources(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()
        self.served_path = Path(self.tmp_dir.name).joinpath("served")
        self.served_path.mkdir()
        self.server = ResourceServer(self.served_path)
        self.shared_path = self.album_controller.configuration().shared_resources_path()

    def tearDown(self) -> None:
        self.server.close()
        super().tearDown()

    def _serve(self, file_name, content: bytes) -> str:
        """Serve a file, return its sha256 hash."""
        self.served_path.joinpath(file_name).write_bytes(content)
        return "sha256:%s" % hashlib.sha256(content).hexdigest()

    def _write_solution(self, name, resources, parent=None) -> str:
        dependencies = {"resource_file": {"resources": resources}}
        if parent:
            dependencies["parent"] = {"resolve_solution": parent}
        path = Path(self.tmp_dir.name).joinpath("%s.py" % name)
        path.write_text(
            SOLUTION
            % {
                "name": name,
                "api_version": TEST_ALBUM_API_VERSION,
                "dependencies": repr(dependencies),
            },
            encoding="utf-8",
        )
        return str(path)

    def _resource(self, file_name, **kwargs):
        return dict(
            {"name": file_name, "url": f"{self.server.url}/{file_name}"},
            **kwargs,
        )

    def _installed_resources(self, name):
        """Read the json file the solution reads its resources from."""
        resolve_result = (
            self.album_controller.collection_manager().resolve_installed_and_load(
                "group:%s:0.1.0" % name
            )
        )
        icache = resolve_result.loaded_solution().installation().internal_cache_path()
        json_path = icache.joinpath("group_%s_0.1.0_resource_file.json" % name)
        return json.loads(json_path.read_text(encoding="utf-8"))["resources"]

    def _active_environment_path(self):
        return (
            self.album_controller.environment_manager()
            .get_environment_handler()
            .get_package_manager()
            .get_active_environment_path()
        )

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.get_environment_path"
    )
    @patch("album.environments.controller.package_manager.PackageManager.install")
    def test_install_and_run(self, _, get_environment_path):
        get_environment_path.return_value = self._active_environment_path()
        model_hash = self._serve("model.pt", b"model weights")
        self._serve("README.md", b"read me")
        self._serve("tool.bin", b"a tool")
        other_os = "win32" if sys.platform != "win32" else "linux"
        path = self._write_solution(
            "solution_resources",
            {
                "model": self._resource("model.pt", hash=model_hash, scope="catalog"),
                "readme": self._resource("README.md"),
                "tool": self._resource("tool.bin", os=sys.platform, scope="solution"),
                "tool_other_os": self._resource(
                    "tool.exe", os=other_os, scope="solution"
                ),
            },
        )

        # install
        self.album_controller.install_manager().install(path)

        # assert: the files are where the json file says, the one of the other platform is not downloaded
        resources = self._installed_resources("solution_resources")
        self.assertEqual(
            b"model weights", Path(resources["model"]["path"]).read_bytes()
        )
        self.assertEqual(b"read me", Path(resources["readme"]["path"]).read_bytes())
        self.assertEqual(b"a tool", Path(resources["tool"]["path"]).read_bytes())
        self.assertIsNone(resources["tool_other_os"]["path"])
        self.assertNotIn("/tool.exe", self.server.requests)
        self.assertTrue(
            resources["model"]["path"].startswith(
                str(self.shared_path.joinpath("catalog", "cache_catalog"))
            )
        )
        self.assertTrue(
            resources["readme"]["path"].startswith(
                str(self.shared_path.joinpath("global"))
            )
        )
        self.assertNotIn(str(self.shared_path), resources["tool"]["path"])

        # run: the solution gets the paths from album-solution-api
        self.album_controller.run_manager().run(path)

        logs = self.get_logs_as_string()
        self.assertNotIn("ERROR", logs)
        printed = json.loads(logs.split("RESOURCES=")[1].splitlines()[0])["resources"]
        self.assertEqual(
            {"model", "readme", "tool"}, set(printed.keys())
        )  # os_specific=True: only the resources of this platform
        for key in printed:
            self.assertEqual(resources[key]["path"], printed[key]["path"])

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.get_environment_path"
    )
    @patch("album.environments.controller.package_manager.PackageManager.install")
    def test_install_shares_content(self, _, get_environment_path):
        get_environment_path.return_value = Path(self.tmp_dir.name).joinpath("env")
        model_hash = self._serve("model.pt", b"model weights")
        self._serve("other_model.pt", b"other weights")
        path_one = self._write_solution(
            "solution_one", {"model": self._resource("model.pt", hash=model_hash)}
        )
        # same content: shared. Same name, different content: not shared.
        path_two = self._write_solution(
            "solution_two",
            {
                "model": self._resource("model.pt", hash=model_hash),
                "other": dict(self._resource("other_model.pt"), name="model.pt"),
            },
        )

        self.album_controller.install_manager().install(path_one)
        self.album_controller.install_manager().install(path_two)

        resources_one = self._installed_resources("solution_one")
        resources_two = self._installed_resources("solution_two")
        self.assertEqual(resources_one["model"]["path"], resources_two["model"]["path"])
        self.assertEqual(1, self.server.requests.count("/model.pt"))
        self.assertNotEqual(
            resources_two["model"]["path"], resources_two["other"]["path"]
        )
        self.assertEqual(
            b"model weights", Path(resources_two["model"]["path"]).read_bytes()
        )
        self.assertEqual(
            b"other weights", Path(resources_two["other"]["path"]).read_bytes()
        )

    def test_concurrent_retrieval_downloads_once(self):
        """Two solutions installed at the same time that share a resource (#277)."""
        model_hash = self._serve("model.pt", b"model weights")
        # without the lock of the content folder, both downloads would run at once
        self.server.delay = 1.0
        download_manager = self.album_controller.download_manager()

        def resources_of(solution_name):
            model = dict(self._resource("model.pt", hash=model_hash), os=None)
            resources_dict = {"resources": {"model": dict(model, scope="global")}}
            download_manager._set_paths_in_dict(
                resources_dict,
                Path(self.tmp_dir.name).joinpath(solution_name),
                "cache_catalog",
                self.shared_path,
            )
            return resources_dict

        resources_dicts = [resources_of("one"), resources_of("two")]
        start = threading.Barrier(len(resources_dicts))
        errors = []

        def retrieve(resources_dict):
            start.wait()
            try:
                download_manager._retrieve_resources_from_dict(resources_dict)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=retrieve, args=(d,)) for d in resources_dicts
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # assert: downloaded once, both solutions get the same file
        self.assertEqual([], errors)
        self.assertEqual(["/model.pt"], self.server.requests)
        paths = {d["resources"]["model"]["path"] for d in resources_dicts}
        self.assertEqual(1, len(paths))
        self.assertEqual(b"model weights", Path(paths.pop()).read_bytes())

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.get_environment_path"
    )
    @patch("album.environments.controller.package_manager.PackageManager.install")
    def test_install_parent_gets_resources(self, _, get_environment_path):
        get_environment_path.return_value = Path(self.tmp_dir.name).joinpath("env")
        parent_hash = self._serve("parent.bin", b"parent")
        child_hash = self._serve("child.bin", b"child")
        parent = self._write_solution(
            "solution_parent", {"data": self._resource("parent.bin", hash=parent_hash)}
        )
        child = self._write_solution(
            "solution_child",
            {"data": self._resource("child.bin", hash=child_hash)},
            parent=parent,
        )

        # only the child is installed explicitly
        self.album_controller.install_manager().install(child)

        self.assertEqual(
            b"parent",
            Path(
                self._installed_resources("solution_parent")["data"]["path"]
            ).read_bytes(),
        )
        self.assertEqual(
            b"child",
            Path(
                self._installed_resources("solution_child")["data"]["path"]
            ).read_bytes(),
        )

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.get_environment_path"
    )
    @patch("album.environments.controller.package_manager.PackageManager.install")
    def test_install_hash_mismatch(self, install, get_environment_path, _):
        get_environment_path.return_value = Path(self.tmp_dir.name).joinpath("env")
        self._serve("model.pt", b"model weights")
        wrong_hash = "sha256:%s" % hashlib.sha256(b"something else").hexdigest()
        path = self._write_solution(
            "solution_broken",
            {"model": self._resource("model.pt", hash=wrong_hash, scope="solution")},
        )

        with self.assertRaises(RuntimeError) as e:
            self.album_controller.install_manager().install(path)

        self.assertIn('Could not retrieve resource "model"', str(e.exception))
        install.assert_not_called()  # failed before the environment was built

        # the failed installation is removed right away
        collection_index = (
            self.album_controller.collection_manager().get_collection_index()
        )
        self.assertEqual([], collection_index.get_unfinished_installation_solutions())
        self.assertFalse(
            self.album_controller.configuration()
            .installation_path()
            .joinpath("cache_catalog", "group", "solution_broken", "0.1.0")
            .exists()
        )

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.get_environment_path"
    )
    @patch("album.environments.controller.package_manager.PackageManager.install")
    def test_uninstall(self, _, get_environment_path, *__):
        get_environment_path.return_value = Path(self.tmp_dir.name).joinpath("env")
        shared_hash = self._serve("shared.bin", b"shared")
        own_hash = self._serve("own.bin", b"own")
        path = self._write_solution(
            "solution_uninstall",
            {
                "shared": self._resource("shared.bin", hash=shared_hash),
                "own": self._resource("own.bin", hash=own_hash, scope="solution"),
            },
        )
        self.album_controller.install_manager().install(path)
        resources = self._installed_resources("solution_uninstall")

        self.album_controller.install_manager().uninstall(path)

        # resources of the solution go with it, shared ones stay for others
        self.assertFalse(Path(resources["own"]["path"]).exists())
        self.assertTrue(Path(resources["shared"]["path"]).exists())

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.get_environment_path"
    )
    @patch("album.environments.controller.package_manager.PackageManager.install")
    def test_reinstall_keeps_and_downloads_resources(
        self, _, get_environment_path, *__
    ):
        get_environment_path.return_value = Path(self.tmp_dir.name).joinpath("env")
        self._serve("own.bin", b"own")
        shared = self._resource("shared.bin", hash=self._serve("shared.bin", b"shared"))
        own = self._resource("own.bin", scope="solution")
        path = self._write_solution("solution_again", {"own": own, "shared": shared})
        self.album_controller.install_manager().install(path)
        # no longer where it was downloaded from, and the solution has a new one
        self.served_path.joinpath("own.bin").unlink()
        self._serve("new.bin", b"new")
        self._write_solution(
            "solution_again",
            {
                "own": own,
                "shared": shared,
                "new": self._resource("new.bin", scope="solution"),
            },
        )

        self.album_controller.install_manager().install(path, reinstall=True)

        # the one it had is kept, the new one downloaded before it was uninstalled
        resources = self._installed_resources("solution_again")
        self.assertEqual(b"own", Path(resources["own"]["path"]).read_bytes())
        self.assertEqual(b"shared", Path(resources["shared"]["path"]).read_bytes())
        self.assertEqual(b"new", Path(resources["new"]["path"]).read_bytes())
        self.assertEqual(["/own.bin", "/shared.bin", "/new.bin"], self.server.requests)

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.get_environment_path"
    )
    @patch("album.environments.controller.package_manager.PackageManager.install")
    def test_reinstall_resource_not_available(
        self, _, get_environment_path, remove_environment, __
    ):
        get_environment_path.return_value = Path(self.tmp_dir.name).joinpath("env")
        self._serve("own.bin", b"own")
        own = self._resource("own.bin", scope="solution")
        path = self._write_solution("solution_gone", {"own": own})
        self.album_controller.install_manager().install(path)
        # a new resource that is not available: its server is gone
        gone_server = ResourceServer(self.served_path)
        gone_server.close()
        self._write_solution(
            "solution_gone",
            {
                "own": own,
                "gone": {
                    "name": "gone.bin",
                    "url": f"{gone_server.url}/gone.bin",
                    "scope": "solution",
                },
            },
        )

        with self.assertRaises(RuntimeError) as e:
            self.album_controller.install_manager().install(path, reinstall=True)

        self.assertIn(
            'Cannot install "cache_catalog:group:solution_gone:0.1.0" again, nothing was '
            'changed: Could not retrieve resource "gone" from %s/gone.bin'
            % gone_server.url,
            str(e.exception),
        )
        # still installed, with its resource
        remove_environment.assert_not_called()
        resources = self._installed_resources("solution_gone")
        self.assertEqual(["own"], list(resources))
        self.assertEqual(b"own", Path(resources["own"]["path"]).read_bytes())


if __name__ == "__main__":
    unittest.main()
