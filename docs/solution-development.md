album solution development guide
================================

## Write solutions
### Tips for writing solutions
- We recommend making a separate repository for developing your solutions (see our [default](https://gitlab.com/album-app/catalogs/default) and [default-dev](https://gitlab.com/album-app/catalogs/default) repositories as an example - `default` can be created via the `clone` command demonstrated below, `default-dev` does not have a fixed structure, it's just the source from where we deploy solutions into the catalog) 
- We recommend keeping solutions short - develop the tool or algorithm separately - the solution is just a thin wrapper describing how to use the tool or algorithm.

### How to start
You can use any existing solution as a template to write your own:
```
album clone [solution-file-or-url] --target-dir [parent-dir-of-new-solution] --name [name-of-new-solution]
album clone [group:name:version] --target-dir [parent-dir-of-new-solution] --name [name-of-new-solution]
```
It copies a solution into the provided directory with the provided new name.

Make sure to replace all the relevant content, including `authors` with your (and your coworker's) name. Attributing the authors of the tool or algorithm the solution is using should happen in the `cite` tag.

We provide templates for several languages:
Python:
```
album clone album:template-python:0.1.0-SNAPSHOT --target-dir [parent-dir-of-new-solution] --name [name-of-new-solution]
```
Java:
```
album clone album:template-java:0.1.0-SNAPSHOT --target-dir [parent-dir-of-new-solution] --name [name-of-new-solution]
```
R:
```
album clone album:template-r:0.1.0-SNAPSHOT --target-dir [parent-dir-of-new-solution] --name [name-of-new-solution]
```

### Testing your solution
You can install and run the new solution with these commands:
```
album install [path-to-solution]
album run [path-to-solution] --my-parameter [parameter-value]
```

### Setup parameters
The setup parameters are derived from the [bioimage.io]() specification.

* `group`: The group/organization associated with the specific solution.
* `name`: The name of the solution itself
* `version`: The version of the solution. Note that the `-SNAPSHOT`
  convention is used to indicate a version is not yet final.
* `description`: This is a short description of the specific solution.
* `url`: The URL of this solution.
* `license`: The license of the solution (e.g. MIT, Apache, GPL, ...)
* `min_album_version`: The minimum version of
  [album](https://album.solutions) required to run this solution.
* `tested_album_version`: The most recent version of
  [album](https://album.solutions) that was tested with this solution.
* `args`: The arguments that can be (and may be required) to run the
  specific solution.
* `run`: The `run` function for the solution. This can either be a
  variable that points to a function, or a `lambda` function. This
  function is evaluated within the solution's environment.
* `install`: The `install` function for the solution. This can either be a
  variable that points to a function, or a `lambda` function. This
  function is evaluated in the `album` environment.
* `pre_test`: The `pre_test` function for the solution. This can either be a
  variable that points to a function, or a `lambda` function. This
  function is evaluated before the test function is evaluated. The
  purpose of this function is to do things like prepare files for testing.
* `test`: The `test` function for the solution. This can either be a
  variable that points to a function, or a `lambda` function. This
  function is evaluated in the solution environment and tests whether
  the solution is working as expected.
* `author`: This (these) are the authors of the solution. This is a
  string-type variable.
* `author_email`: This is the email of the author responsible for the solution.
* `long_description`: This is a long description of the solution.
* `git_repo`: This is the URL of the git repository that stores the
  code that this solution provides.
* `dependencies`: This is a dictionary that specifies the environment
  of the solution.
* `timestamp`: This is the timestamp of the solution.
* `format_version`: This specifies the format version of the solution,
  which corresponds to the `album-runner` version.
* `cite`: This is a list of dictionaries that specify the citations
  associated with this solution file. Each dictionary may contain
  keys: `text` for the text representation of the citation (Harvard
  format), and `doi` the DOI URL of the solution, if one is available.
* `tags`: This is a list of strings for tags that descript the
  specific solution.
* `documentation`: A link to the documentation for the solution.
* `covers`: This is a list of cover images to be displayed for this
  solution in a catalog.
* `sample_inputs`: This is a list of sample inputs that can be used to
  test the specific solution.
* `sample_outputs`: This is an example output that can be used for
  comparison when running the solution on the `sample_inputs`.
* `doi`: This is the DOI of *this* solution. This DOI is distinct from
  DOIs of citations for this solution. This DOI points to the `album`
  solution for the specific solution.
* `catalog`: The catalog that this solution was obtained from.
* `parent`: (Optional) A parent solution for the specific solution.
* `steps`: (Optional) A sequence of steps to be evaluated in this solution.
* `close`: The `close` function for the solution. This can either be a
  variable that points to a function, or a `lambda` function. This
  function is evaluated in the solution environment when the solution
  finishes running.
* `title`: The title of the solution.

### Solution API

Some useful paths and variables for a solution to use

```
get_active_solution().environment_cache_path
get_active_solution().environment_path
get_active_solution().environment_name
get_active_solution().download_cache_path
```

`get_active_solution().environment_cache_path`:  This is the local
path where solution specific files can be stored for later use.  
`get_active_solution().environment_path`:  This is the local path for
the conda environment of this particular solution.  
`get_active_solution().environment_name`:  This is the name of the
conda environment for this particular solution.  
`get_active_solution().download_cache_path`:  This is the download
cache path for this solution. Files in here should be treated as
temporary.  

# Create your own catalog
Use this command to create a new catalog based on any template from [here](https://gitlab.com/album-app/catalogs/templates) - it will be copied into the provided directory with the provided new name.
```
album clone [catalog-template-name] --target-dir [parent-dir-of-new-catalog] --name [name-of-new-catalog]
```
The most basic template is this one:
```
album clone catalog --target-dir [parent-dir-of-new-catalog] --name [name-of-new-catalog]
```
If you want to build a catalog website using Gatsby (this can easily be done via gitlab or github CI), use this template:
```
album clone catalog-gatsby --target-dir [parent-dir-of-new-catalog] --name [name-of-new-catalog]
```
You can upload the newly created directory to gitlab or githab and make it easy for others to use your catalog as well.


## Deploy a new solution (version) into a catalog
Once the solution is working and the catalog exists, add the catalog to your local collection:
```
album add-catalog [path-to-new-catalog]
```
Now deploy the solution into this catalog:
```
album deploy [solution-file] --catalog [catalog-name]
```
Anyone who has this catalog in their collection and wants to use this new solution (including yourself) has to first..

.. update their local catalog cache:
```
album update
```
..  and then upgrade their local collection:
```
album upgrade
```
Now you should be able to install and run this solution via these commands:
```
album install [group:name:version-of-your-new-solution]
album run [group:name:version-of-your-new-solution]
```
