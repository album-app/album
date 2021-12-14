from io import StringIO

from album.runner.api import setup

env_file = StringIO("""name: template-python
channels:
  - defaults
dependencies:
  - albuasdasdm=0.0.0.1
""")

setup(
    group="group",
    name="faultySolution",
    title="name",
    version="0.1.0",
    album_api_version="0.1.1",
    dependencies={'environment_file': env_file}
)
