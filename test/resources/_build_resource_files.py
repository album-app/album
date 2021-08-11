import os
from pathlib import Path

from album.core.controller.catalog_manager import CatalogManager
from album.core.model.catalog_index_new import CatalogIndex
from album.core.model.default_values import DefaultValues
from album.core.utils.operations import file_operations


def build_resource_files():
    current_path = Path(os.path.dirname(os.path.realpath(__file__))).joinpath("catalogs")
    build_empty_catalog("empty", current_path.joinpath("unit", "empty"))
    build_single_solution_catalog("minimal-solution", current_path.joinpath("unit", "minimal-solution"))
    build_test_catalog(str(CatalogIndex.version), current_path.joinpath(str(CatalogIndex.version)))


def build_empty_catalog(name, path):
    if path.exists():
        file_operations.force_remove(path)
    path.mkdir(parents=True)
    CatalogManager.create_new_catalog(path)
    db_file = path.joinpath(DefaultValues.catalog_index_file_name.value)
    catalog_index = CatalogIndex(name, db_file)
    catalog_index.get_connection().commit()
    return catalog_index


def build_test_catalog(name, path):
    catalog_index = build_empty_catalog(name, path)
    catalog_index.update(solution_attrs={
        "args": [
            {
                "default": "inp1",
                "description": "desc1",
                "name": "inp1"
            },
            {
                "default": 1.0,
                "description": "desc2",
                "name": "inp2"
            },
            {
                "default": True,
                "description": "desc3",
                "name": "inp3"
            },
            {
                "default": 2.0,
                "description": "desc4",
                "name": "inp4"
            },
            {
                "default": 0.01,
                "description": "desc5",
                "name": "inp5"
            },
            {
                "default": 1,
                "description": "desc6",
                "name": "inp6"
            },
            {
                "default": 0.3,
                "description": "desc7",
                "name": "inp7"
            },
            {
                "default": 0.75,
                "description": "desc8",
                "name": "inp8"
            }
        ],
        "authors": "Sample Author",
        "cite": "citation",
        "covers": [
            {
                "description": "coverDescription",
                "source": "sourcePath"
            }
        ],
        "description": "keyword1",
        "documentation": "",
        "format_version": "0.3.0",
        "git_repo": "https://gitlab.com/album-app/album",
        "license": "MIT",
        "min_album_version": "0.1.0",
        "sample_inputs": [
            {
                "description": "sampleInputDescription1",
                "value": "sampleInput.tif"
            }
        ],
        "sample_outputs": [
            {
                "description": "sampleOutputDescription1",
                "value": "sampleResult.txt"
            }
        ],
        "group": "ida-mdc",
        "name": "solution0_dummy",
        "title": "solution0_dummy",
        "version": "0.1.0",
        "tags": [
            "tag1"
        ],
        "tested_album_version": "0.1.0",
        "timestamp": "2021-02-08T22:16:03.331998"
    })
    catalog_index.update(solution_attrs={
        "args": [
            {
                "default": "",
                "description": "desc1",
                "name": "inp1"
            }
        ],
        "authors": "Sample Author",
        "cite": "Citation",
        "covers": [
            {
                "description": "coverDescription",
                "source": "sourcePath"
            }
        ],
        "description": "keyword2",
        "documentation": "",
        "format_version": "0.3.0",
        "git_repo": "https://gitlab.com/album-app/album",
        "license": "MIT",
        "min_album_version": "0.1.0",
        "sample_inputs": [],
        "sample_outputs": [],
        "group": "ida-mdc",
        "name": "solution0_dummy2",
        "title": "solution0_dummy2",
        "version": "0.1.0",
        "tags": [
            "tag2",
            "tag3"
        ],
        "tested_album_version": "0.1.0",
        "timestamp": "2021-02-08T22:16:03.331998"
    })
    catalog_index.get_connection().commit()


def build_single_solution_catalog(name, path):
    catalog_index = build_empty_catalog(name, path)
    catalog_index.update(solution_attrs={
        "args": [
            {
                "default": "",
                "description": "desc1",
                "name": "inp1"
            }
        ],
        "authors": [],
        "cite": [],
        "covers": [],
        "sample_inputs": [],
        "sample_outputs": [],
        "description": "",
        "documentation": "",
        "format_version": "0.3.0",
        "git_repo": "",
        "license": "",
        "min_album_version": "0.1.0",
        "group": "testGroup",
        "name": "testName",
        "title": "testTitle",
        "version": "testVersion",
        "tags": [],
        "tested_album_version": "0.1.0",
        "timestamp": "2021-02-08T22:16:03.331998"
    })
    catalog_index.get_connection().commit()


build_resource_files()
