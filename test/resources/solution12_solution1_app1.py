from album.runner.api import setup


setup(
    group="group",
    name="solution12_solution1_app1",
    version="0.1.0",
    album_api_version="0.1.1",
    dependencies={
        'parent': {
            'name': 'solution1_app1',
            'group': 'group',
            'version': '0.1.0',
            'args': [
                {
                    "name": "file_solution1_app1",
                    "value": "value"
                }
            ]
        }
    }
)

