.. _solution-development:

hips solution development guide
================================

Write a solution file.

Here is an example solution file:

.. code-block: python
   
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
          - git+https://gitlab.com/ida-mdc/hips.git
    """)


    def hips_init():
        pass


    def hips_install():
        pass


    def hips_run():
        print('The solution finished running')


    def hips_close():
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
          install=hips_install,
          init=hips_init,
          run=hips_run,
          close=hips_close,
          dependencies={'environment_file': env_file})

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
>
