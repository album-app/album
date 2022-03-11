# Command line overview

`solution-identifier` can be `group:name:version`, `catalog-name:group:name:version`, a path, a URL, or a DOI.

| Album basics  |   |
|---|---|
|`album help`| Print help message and exit.  |
|`album index`| Print all catalogs and associated solutions in your local collection. |

| Manage catalogs  | See [usage instructions](/usage-instructions) for more details. |
|---|---|
|`album add-catalog [catalog-directory-or-url]`| Add a catalog to your local collection. |
|`album remove-catalog [catalog-directory-or-url]`| Remove a catalog from your local collection. This will remove all solutions associated with the catalog!|
|`album update`| Reload all indices of all catalogs added to your local collection.|
|`album update --src [catalog-directory-or-url]`| Like `update`, but only for one specific catalog.|
|`album upgrade`| Synchronize the latest state of all your catalogs with the state of your local solution collection.|
|`album upgrade --dry-run`| Same as `upgrade`, but only prints changes and does not apply them to the collection.|
|`album upgrade --src [catalog-directory-or-url]`| Like `upgrade`, but only for one specific catalog.|

| Use solutions | See [usage instructions](/usage-instructions) for more details.|
|---|---|
|`album install [solution-identifier]`| Install a solution.|
|`album uninstall [solution-identifier]`| Uninstall a solution.|
|`album info [solution-identifier]`| Print the metadata and usage instructions of a solution.|
|`album run [solution-identifier]`| Run a solution.|
|`album test [solution-identifier]`| Test if a solution behaves on your system as expected.|

| Write your own solutions |See [solution development guide](/solution-development) for more details.|
|---|---|
|`album clone [catalog-template-name] [parent-dir-of-new-catalog] [name-of-new-catalog]`| Creates a new catalog based on any template from [here](https://gitlab.com/album-app/catalogs/templates) into the provided directory with the provided new name.|
|`album clone [solution-identifier] [parent-dir-of-new-solution] [name-of-new-solution]`| Copies a solution  into the provided directory with the provided new name.|
|`album deploy [solution-file] [catalog-name]`| Deploy a solution into a catalog.|
|`album deploy [solution-file] [catalog-name] --dry-run`| Simulate deploying a solution into a catalog.|

| Server | See [server instructions](/server) for more details.|
|---|---|
|`album server --port 1234`| Launch the album REST service - more information [here](/server).|
