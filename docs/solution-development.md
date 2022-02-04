# Developing solutions

## Tips for writing solutions
- We recommend making a separate repository for developing your solutions (see our [default](https://gitlab.com/album-app/catalogs/default) and [default-dev](https://gitlab.com/album-app/catalogs/default) repositories as an example - `default` can be created via the `clone` command demonstrated below, `default-dev` does not have a fixed structure, it's just the source from where we deploy solutions into the catalog) 
- We recommend keeping solutions short - develop the tool or algorithm separately - the solution is just a thin wrapper describing how to use the tool or algorithm.
- Use [semantic versioning](https://semver.org/), append `-SNAPSHOT` to your version of you are redeploying the same version repeatedly for test purposes 

## Cloning solution templates
You can use any existing solution as a template to write your own:
```
album clone [solution-file-or-url] --target-dir [parent-dir-of-new-solution] --name [name-of-new-solution]
album clone [group:name:version] --target-dir [parent-dir-of-new-solution] --name [name-of-new-solution]
```
It copies a solution into the provided directory with the provided new name.

- replace the identifiers (`group`, `name`, `version`)
- replace all the relevant content, including `authors` with your (and your coworker's) name
- attributing the authors of the tool or algorithm the solution is using should happen in the `cite` tag

We provide templates, check out the full list in our [default catalog development repo](https://gitlab.com/album-app/catalogs/default-dev).
For the basic python template, this is the correct call:
```
album clone album:template-python:0.1.0 --target-dir [parent-dir-of-new-solution] --name [name-of-new-solution]
```

## Solution setup examples
Each following example is a fully contained solution highlighting different features of the `album.runner.api.setup` method. 

The minimal configuration of a solution looks like this:
```python
from album.runner.api import setup


setup(
   group="my-group-name",
   name="my-solution-name",
   version="0.1.0-SNAPSHOT",
    album_api_version="0.3.0"
)
```

Make solutions reproducible by adding a conda environment specification using fixed versioning:
```python
from album.runner.api import setup
from io import StringIO


env_file = StringIO("""name: my-solution-name
channels:
 - conda-forge
 - defaults
dependencies:
 - python=3.6
""")


setup(
    group="my-group-name",
    name="my-solution-name",
    version="0.1.0-SNAPSHOT",
    album_api_version="0.3.0",
    dependencies={"environment_file": env_file}
)
```

Make solutions findable by adding metadata:
```python
from album.runner.api import setup


setup(
    group="my-group-name",
    name="my-solution-name",
    version="0.1.0-SNAPSHOT",
    album_api_version="0.3.0",
    title="The title of this solution",
    description="A description of what this solution is doing.",
    authors=["My name", "My coworkers name"],
    cite=[{
       "text": "My citation text",
       "doi": "my.citation.doi",
       "url": "my://citation.url"
    }],
    tags=["dummy", "python"],
    license="MIT",
    documentation=["documentation.md"],
    covers=[{
       "description": "Dummy cover image.",
       "source": "cover.png"
    }]
)
```

Add custom install / uninstall methods (they will be called from the solution environment):
```python
from album.runner.api import setup

def install():
    print("installing..")

def uninstall():
    print("uninstalling..")


setup(
   group="my-group-name",
   name="my-solution-name",
   version="0.1.0-SNAPSHOT",
   album_api_version="0.3.0",
   install=install,
   uninstall=uninstall
)
```

Make solutions accessible by adding arguments:
```python
from album.runner.api import setup

def run():
    from album.runner.api import get_args
    args = get_args()
    print("Hi " + args.name + ", nice to meet you!")


setup(
    group="my-group-name",
    name="my-solution-name",
    version="0.1.0-SNAPSHOT",
    album_api_version="0.3.0",
    args=[{
        "name": "name",
        "type": "string",
        "default": "Bugs Bunny",
        "description": "How to you want to be addressed?"
    }],
    run=run
)
```

Adding a test routine to easily let others verify the solution / understand how it's used:
```python
from album.runner.api import setup


def run():
    from album.runner.api import get_args
    with open(get_args().file, "a") as file:
        file.write("RUNNING\n")

def prepare_test():
    import tempfile
    file = tempfile.NamedTemporaryFile(delete=False, mode="w+")
    return {"--file": file.name}

def test():
    from album.runner.api import get_args
    with open(get_args().file, "r") as file:
        file_content = file.readlines()
    assert ["RUNNING\n"] == file_content


setup(
    group="my-group-name",
    name="my-solution-name",
    version="0.1.0-SNAPSHOT",
    album_api_version="0.3.0",
    args=[{
       "name": "file"
    }],
    run=run,
    pre_test=prepare_test,
    test=test
)
```

Solutions can inherit from each other. They should live in the same catalog or should be identified via DOI to be findable. 
This solution will use the environment of `my:group-name:my-parent-app-solution-name:0.1.0` and call the parents run method 
with the provided argument before running their own run method (if provided):
```python
from album.runner.api import setup


setup(
   group="my-group-name",
   name="my-child-solution-name",
   version="0.1.0-SNAPSHOT",
   album_api_version="0.1.1",
   dependencies={
      "parent": {
         "name": "my-parent-app-solution-name",
         "group": "my-group-name",
         "version": "0.1.0",
         "args": [
             {
                 "name": "app_param",
                 "value": "app_param_value"
             }
         ]
      }
   }
)
```

## Testing your solution
You can install and run a new or cloned solution with these commands:
```
album install [path-to-solution]
album run [path-to-solution] --my-parameter [parameter-value]
```

## Setup parameters
The setup parameters are derived from the [bioimage.io](https://bioimage.io) specification. We provide a (not yet fully specified) [RDF schema](https://gitlab.com/album-app/album/-/blob/main/src/album/core/schema/solution_schema_0.json).

### Required solution parameters

* `group`: The group/organization associated with the specific solution.
* `name`: The name of the solution itself
* `version`: The version of the solution. Note that the `-SNAPSHOT`
  convention is used to indicate a version is not yet final.
* `album_api_version`: The required version of the album API to run this solution (= `album-runner` module version).

### Lambdas of a solution (optional)
**-- NOTE: IMPORT HANDLING --** When writing solution methods, make sure to add the imports specific to the solution target environment at the beginning of the method, not the top of the file.
The solution is initially executed from the album environment while the following parameters are only called from the solution target environment.

* `run`: The `run` function for the solution. This can either be a
  variable that points to a function, or a `lambda` function.
* `install`: The `install` function for the solution. This can either be a
  variable that points to a function, or a `lambda` function.
* `pre_test`: The `pre_test` function for the solution. This can either be a
  variable that points to a function, or a `lambda` function. This
  function is evaluated before the test function is evaluated. The
  purpose of this function is to do things like prepare files for testing.
* `test`: The `test` function for the solution. This can either be a
  variable that points to a function, or a `lambda` function. This
  function is evaluated in the solution environment and tests whether
  the solution is working as expected.
* `close`: The `close` function for the solution. This can either be a
 variable that points to a function, or a `lambda` function. This
 function is evaluated after the solution finishes running.
  
### Metadata of a solution (optional)
* `title`: The title of the solution.
* `description`: This is a short description of the specific solution.
* `license`: The license of the solution (e.g. MIT, Apache, GPL, ...)
* `args`: The arguments that can be (and may be required) to run the
  specific solution.
* `author`: The author(s) of the solution. This is an array of strings.
* `dependencies`: A dictionary that specifies the environment, the following options currently exist:
  * `environment_file`: A `File` object or path to the solution environment file. 
  * `parent`: A dictionary specifying the parent solution. Either use coordinates (`group`, `name`, `version`), `doi`, or `resolve_solution` which can be any solution identifier string like a path or a URL.
* `cite`: This is a list of dictionaries that specify the citations
  associated with this solution file. Each dictionary may contain
  keys: `text` for the text representation of the citation (Harvard
  format), `url` for the project URL of the citation, if available, and `doi` the DOI of the citation, if available.
* `tags`: This is a list of strings for tags that describe the key features of 
  the solution.
* `documentation`: A list of markdown files or links to the documentation for the solution.
* `covers`: This is a list of cover images to be displayed for this
  solution in a catalog.
* `doi`: This is the DOI of this solution. This DOI is distinct from DOIs of citations for this solution.
* `acknowledgement`: A free text place for funding, important institutions, people, and more.

## Solution API

The solution API is provided through the `album-runner` module. There
are multiple key methods:

`get_environment_name()`:  This is the name of the
conda environment for this particular solution.  

`get_environment_path()`:  This is the local path for
the conda environment of this particular solution.  

`get_data_path()`: Returns the data path provided for the solution.

`get_package_path()`: Returns the package path provided for the solution.

`get_app_path()`: Returns the app path provided for the solution.

`get_cache_path()`: Returns the cache path provided for the solution.

`in_target_environment()`: Returns `true` if the current python is the
python from the solution target environment.

`get_args()`: Get the parsed argument from the solution call.
