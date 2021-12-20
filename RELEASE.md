# `album-runner` release procedure
increase version in:
- `./setup.cfg` to set a new pypi version.

commit changes to `main` branch to trigger the testing pipeline and including the release CI!

check pypi installation on fresh environment:
- ```
  conda create -n deploy_test_env python=3.6 pip
  conda activate deploy_test_env
  pip install album-runner=<version>
  python
 
within `python` cmd call:
- ` from album.runner import *`
 
# `album` release procedure
increase version in:
- `./setup.cfg` to set a new pypi version.
- `./test/resources/*.py` to work with the new version. Fix failing unittests!
- `./src/album/core/__init__.py` to output the new version on the logs
- `./album.yml` to get dockerfiles to run

Reason for the `album.yml`: in the latest pypi version there should be the correct `album.yml` file to create an environment 
with `album` installed. This is necessary for docker templates to work correctly!

if you increased the `album-runner` version additionally change:
- `album_api_version` in `./test/resources/*.py` to use the new runner API version
- `runner_url` in `default_values.py` to install the new runner in the target environment

commit changes to `main` branch to trigger the testing pipeline and including the release CI!

NOTE: Successful execution of deploy jobs is important! Docker deployment needs pypi version to be available!






