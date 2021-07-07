album solution development guide
================================

Write a solution file.

Here is an example solution file:

```
    from hips_runner import setup
    from io import StringIO

    env_file = StringIO("""name: demo-solution
    channels:
      - conda-forge
      - defaults
    dependencies:
      - python=3.6
      - pip
      - git
      - pip:
          - git+https://gitlab.com/album-app/album-runner.git
    """)


    def init():
        pass


    def install():
        pass


    def run():
        print('The solution finished running')


    def close():
        pass


    setup(group="ida-mdc",
          name="demo-solution",
          version="0.1.0",
          format_version="0.3.0",
          title="A demo solution",
          description="This demo solution doesn't do anything",
          authors="Kyle Harrington",
          cite=["TBA"],
          git_repo="https://github.com/ida-mdc/capture-knowledge",
          tags=["vascu", "ec", "app"],
          license="ApacheV2.0",
          documentation="",
          covers=[{
              "description": "Dummy cover image.",
              "source": "cover.png"
          }],
          sample_inputs=[],
          sample_outputs=[],
          min_hips_version="0.1.0",
          tested_hips_version="0.1.0",
          args=[],
          install=install,
          init=init,
          run=run,
          close=close,
          dependencies={'environment_file': env_file})
```

## Tips for developing solutions

Some useful paths and variables for a solution to use

```
get_active_hips().environment_cache_path
get_active_hips().environment_path
get_active_hips().environment_name
get_active_hips().download_cache_path
```
