# Quick start

### Album basics
* `album help` - Print help message and exit.
* `album index` - Print all catalogs and associated solutions in your local collection.

### Manage catalogs
* `album add-catalog [catalog-directory-or-url]` - Add a catalog to your local collection.
* `album remove-catalog [catalog-directory-or-url]` - Remove a catalog from your local collection. This will remove all solutions associated with the catalog!
* `album update` - Reload all indices of all catalogs added to your local collection.
* `album update --src [catalog-directory-or-url]` - Like `update`, but only for one specific catalog.
* `album upgrade` - Synchronize the latest state of all your catalogs with the state of your local solution collection.
* `album upgrade --dry-run` - Same as `upgrade`, but only prints changes and does not apply them to the collection.
* `album upgrade --src [catalog-directory-or-url]` - Like `upgrade`, but only for one specific catalog.

### Use solutions
* `album install [solution-file-or-url]` - Install a solution.
* `album install [group:name:version]` - Lookup and install a solution identified via group, name and version.
* `album uninstall [solution-file-or-url]` - Uninstall a solution.
* `album uninstall [group:name:version]` - Lookup and uninstall a solution identified via group, name and version.
* `album run [solution-file-or-url]` - Run a solution.
* `album run [group:name:version]` - Lookup and run a solution identified via group, name and version.
* `album test [solution-file-or-url]` - Test if a solution behaves on your system as expected.
* `album test [group:name:version]` - Lookup and test a solution identified via group, name and version.

### Write your own solutions
* `album clone [catalog-template-name] --target-dir [parent-dir-of-new-catalog] --name [name-of-new-catalog]` - Creates a new catalog based on any template from [here](https://gitlab.com/album-app/catalogs/templates) into the provided directory with the provided new name.
* `album clone [solution-file-or-url] --target-dir [parent-dir-of-new-solution] --name [name-of-new-solution]` - Copies a solution  into the provided directory with the provided new name.
* `album clone [group:name:version] --target-dir [parent-dir-of-new-solution] --name [name-of-new-solution]` - Looks up and copies a solution into the provided directory with the provided new name.
* `album deploy [solution-file] --catalog [catalog-name]` - Deploy a solution into a catalog.
* `album deploy [solution-file] --dry-run` - Simulate deploying a solution into a catalog.

### Server
* `album server --port 1234` - Launch the album REST service - more information [here](server).
