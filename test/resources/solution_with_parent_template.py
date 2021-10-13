from album.runner import setup


def album_init():
    pass


def album_run():
    pass


setup(
    group="group",
    name="solution_with_parent_template",
    title="solution with parent template",
    version="0.1.0",
    format_version="0.3.0",
    timestamp="",
    description="",
    authors="",
    cite="",
    git_repo="",
    tags=[],
    license="license",
    documentation="",
    covers=[],
    sample_inputs=[],
    sample_outputs=[],
    min_album_version="0.1.1",
    tested_album_version="0.1.1",
    args=[],
    run=album_run,
    parent={
        'name': 'template-python',
        'group': 'album',
        'version': '0.1.0-SNAPSHOT'
    })

