<p align="center">
  <a href="https://album.solutions"><img src="https://gitlab.com/album-app/album-docs/-/raw/main/docs/_static/album-l-no-text.png" alt="Album" width="200"></a>
</p>

# album

[![PyPI](https://img.shields.io/pypi/v/album?label=PyPI&logo=pypi&logoColor=white)](https://pypi.org/project/album/)
[![conda-forge](https://img.shields.io/conda/vn/conda-forge/album?label=conda-forge&logo=condaforge&logoColor=white)](https://anaconda.org/conda-forge/album)
[![Python](https://img.shields.io/pypi/pyversions/album?logo=python&logoColor=white)](https://pypi.org/project/album/)
[![Docker pulls](https://img.shields.io/docker/pulls/albumsolutions/album?logo=docker&logoColor=white)](https://hub.docker.com/r/albumsolutions/album)
[![Pipeline](https://img.shields.io/gitlab/pipeline-status/album-app%2Falbum?branch=main&label=pipeline&logo=gitlab)](https://gitlab.com/album-app/album/-/pipelines)
[![Documentation](https://img.shields.io/readthedocs/album?logo=readthedocs&logoColor=white)](https://docs.album.solutions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://gitlab.com/album-app/album/-/blob/main/LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2110.00601-b31b1b?logo=arxiv&logoColor=white)](https://arxiv.org/abs/2110.00601)
[![Helmholtz RSD](https://img.shields.io/badge/Helmholtz_RSD-album-005aa0)](https://helmholtz.software/software/album)
[![Helmholtz Imaging CONNECT](https://img.shields.io/badge/Helmholtz_Imaging-CONNECT-005aa0)](https://connect.helmholtz-imaging.de/solution/13)

Album is an open-source framework that turns scientific routines into **executable building blocks**
and organizes them into a shareable, versioned library of research software.

- A **solution** is a single Python file that bundles a routine with its metadata, arguments,
  environment and `install` / `run` / `test` hooks. It can wrap tools written in Python, Java, R,
  C++, Fiji, napari, Blender and more.
- A **catalog** is a git repository of solutions that you can search, share with collaborators,
  publish as a website and archive on Zenodo with a DOI per solution version.

Every solution gets its own micromamba environment, so tools with conflicting dependencies run side
by side on one machine.

## Installation

With [micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html)
(recommended, also installs `git`):

```
micromamba create -n album album -c conda-forge
micromamba activate album
```

With pip (needs `git` on your system):

```
pip install album
```

Installation wizards for Windows, macOS and Linux and more options are described in the
[installation instructions](https://docs.album.solutions/en/latest/installation-instructions.html).

## Getting started

The default catalog with solution templates is added the first time you run album:

```
album index                                             # list catalogs and their solutions
album info album:template-python                        # what the solution does and which arguments it takes
album install album:template-python                     # create its environment
album run album:template-python --name "your name"
```

Continue with the [quick start](https://docs.album.solutions/en/latest/quick-start.html), learn how
to [write your own solution](https://docs.album.solutions/en/latest/solution-development.html), or
browse the public catalogs on [album.solutions](https://album.solutions/#catalogs).

## The Album suite

| Package                                                                     | What it adds                                        | PyPI                                                                                                             | conda-forge                                                                                                                                  |
| --------------------------------------------------------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| [album](https://gitlab.com/album-app/album)                                 | the framework and the `album` command line          | [![PyPI](https://img.shields.io/pypi/v/album?label=)](https://pypi.org/project/album/)                           | [![conda-forge](https://img.shields.io/conda/vn/conda-forge/album?label=)](https://anaconda.org/conda-forge/album)                           |
| [album-gui](https://gitlab.com/album-app/plugins/album-gui)                 | graphical interface, `album gui`                    | [![PyPI](https://img.shields.io/pypi/v/album-gui?label=)](https://pypi.org/project/album-gui/)                   | [![conda-forge](https://img.shields.io/conda/vn/conda-forge/album-gui?label=)](https://anaconda.org/conda-forge/album-gui)                   |
| [album-docker](https://gitlab.com/album-app/plugins/album-docker)           | Docker images from solutions, `album docker`        | [![PyPI](https://img.shields.io/pypi/v/album-docker?label=)](https://pypi.org/project/album-docker/)             | [![conda-forge](https://img.shields.io/conda/vn/conda-forge/album-docker?label=)](https://anaconda.org/conda-forge/album-docker)             |
| [album-package](https://gitlab.com/album-app/plugins/album-package)         | standalone installers, `album package`              | [![PyPI](https://img.shields.io/pypi/v/album-package?label=)](https://pypi.org/project/album-package/)           | [![conda-forge](https://img.shields.io/conda/vn/conda-forge/album-package?label=)](https://anaconda.org/conda-forge/album-package)           |
| [album-distributed](https://gitlab.com/album-app/plugins/album-distributed) | batch and distributed runs, `album run-distributed` | [![PyPI](https://img.shields.io/pypi/v/album-distributed?label=)](https://pypi.org/project/album-distributed/)   | [![conda-forge](https://img.shields.io/conda/vn/conda-forge/album-distributed?label=)](https://anaconda.org/conda-forge/album-distributed)   |
| [album-solution-api](https://gitlab.com/album-app/album-solution-api)       | the API every solution script uses                  | [![PyPI](https://img.shields.io/pypi/v/album-solution-api?label=)](https://pypi.org/project/album-solution-api/) | [![conda-forge](https://img.shields.io/conda/vn/conda-forge/album-solution-api?label=)](https://anaconda.org/conda-forge/album-solution-api) |
| [album-environments](https://gitlab.com/album-app/album-environments)       | environment handling with micromamba                | [![PyPI](https://img.shields.io/pypi/v/album-environments?label=)](https://pypi.org/project/album-environments/) | [![conda-forge](https://img.shields.io/conda/vn/conda-forge/album-environments?label=)](https://anaconda.org/conda-forge/album-environments) |
| [album-mcp](https://gitlab.com/album-app/album-mcp)                         | MCP server for LLM agents                           | from source                                                                                                      | from source                                                                                                                                  |

## Find Album

- Documentation: [docs.album.solutions](https://docs.album.solutions)
- Website and public catalogs: [album.solutions](https://album.solutions)
- Source code and issues: [gitlab.com/album-app/album](https://gitlab.com/album-app/album)
- Developer documentation: [wiki](https://gitlab.com/album-app/album/-/wikis/home)
- Docker images: [albumsolutions/album](https://hub.docker.com/r/albumsolutions/album)
- Helmholtz Research Software Directory: [helmholtz.software/software/album](https://helmholtz.software/software/album)
- Helmholtz Imaging CONNECT: [Album](https://connect.helmholtz-imaging.de/solution/13)

## Citation

Albrecht, J.P.\*, Schmidt, D.\*, Rieckert, L., Otto, M., and Harrington, K., 2026.
Album: executable building blocks for scientific imaging routines, from sharing
to LLM-assisted orchestration. arXiv preprint arXiv:2110.00601v2.\
https://arxiv.org/abs/2110.00601v2

```bibtex
@misc{albrecht_album_2026,
  title         = {Album: executable building blocks for scientific imaging routines, from sharing to {LLM}-assisted orchestration},
  author        = {Albrecht, Jan Philipp and Schmidt, Deborah and Rieckert, Lucas and Otto, Maximilian and Harrington, Kyle},
  year          = {2026},
  eprint        = {2110.00601},
  archivePrefix = {arXiv},
  doi           = {10.48550/arXiv.2110.00601},
  url           = {https://arxiv.org/abs/2110.00601v2}
}
```

## Developers

- Kyle Harrington, Max Delbrueck Center for Molecular Medicine in the
  Helmholtz Association
- Jan Philipp Albrecht, Max Delbrueck Center for Molecular Medicine in
  the Helmholtz Association
- Deborah Schmidt, Max Delbrueck Center for Molecular Medicine in
  the Helmholtz Association

Everyone who contributed to album is listed in
[CITATION.cff](https://gitlab.com/album-app/album/-/blob/main/CITATION.cff).
