# Command line overview

In the listed commands `solution-identifier` can be replaced by:
- `name` - the name of the solution
- `group:name` - group and name of the solution
- `group:name:version` - the full coordinates of the solution
- `catalog:group:name:version` - the catalog name and the solution coordinates
- a path to a single solution python file
- a path to the solution folder containing the `solution.py` file 
- URL (python file or zip containing `solution.py`)
- DOI 

See [usage instructions](/usage-instructions) for more details.

| Album basics  |   |
|---|---|
|`album help`| Print help message and exit.  |
|`album index`| Print all catalogs and associated solutions in your local collection. |

| Manage catalogs  | See [usage instructions](/usage-instructions) for more details. |
|---|---|
|`album add-catalog [catalog-directory-or-url]`| Add a catalog to your local collection. |
|`album remove-catalog [catalog-name]`| Remove a catalog from your local collection. This will remove all solutions associated with the catalog!|
|`album update`| Reload all indices of all catalogs added to your local collection.|
|`album update [catalog-name]`| Like `update`, but only for one specific catalog.|
|`album upgrade`| Synchronize the latest state of all your catalogs with the state of your local solution collection.|
|`album upgrade --dry-run`| Same as `upgrade`, but only prints changes and does not apply them to the collection.|
|`album upgrade [catalog-name]`| Like `upgrade`, but only for one specific catalog.|

| Use solutions | See [usage instructions](/usage-instructions) for more details.|
|---|---|
|`album install [solution-identifier]`| Install a solution.|
|`album uninstall [solution-identifier]`| Uninstall a solution.|
|`album info [solution-identifier]`| Print the metadata and usage instructions of a solution.|
|`album run [solution-identifier]`| Run a solution.|
|`album test [solution-identifier]`| Test if a solution behaves on your system as expected.|

| Write your own solutions |See [solution development guide](/solution-development) and [catalog development guide](/catalog-development) for more details.|
|---|---|
|`album clone [catalog-template-name] [parent-dir-of-new-catalog] [name-of-new-catalog]`| Creates a new catalog based on any template from [here](https://gitlab.com/album-app/catalogs/templates) into the provided directory with the provided new name.|
|`album clone [solution-identifier] [parent-dir-of-new-solution] [name-of-new-solution]`| Copies a solution  into the provided directory with the provided new name.|
|`album deploy [solution-file] [catalog-name]`| Deploy a solution into a catalog.|
|`album deploy [solution-file] [catalog-name] --dry-run`| Simulate deploying a solution into a catalog.|
