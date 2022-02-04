# Usage instructions for album

For installation instructions, see [installation-instructions](/installation-instructions).

Once album is installed, list all available commands: 
```
album -h
```
Have a look at your local collection. 
```
album index
```
When running album for the first time, the default album catalog is added and you should see a list of template solutions in your collection.

## What is a solution?
A solution holds all information to solve a specific problem. Ideally, this includes:
* a code snippet installing software components needed to run the solution in a reproducible manner
* the solution parameters (e.g. input and output files, algorithm parameters)
* how to apply the parameters to a specific algorithm / software to get the result to the problem
* information about what to cite if this solution is used to solve scientific problems
* information about the author of the solution itself

A solution can be identified..
- by string: `GROUP:NAME:VERSION` or `CATALOG_NAME:GROUP:NAME:VERSION`
- by file path (Python file or ZIP)
- by URL pointing to the solution file
- by DOI

In this guide we will use `album:template-python:0.1.0` as an example since this solution is part of the default catalog
and you can run all the following commands without editing them - replace this with the identifier of your target solution.

## How to use solutions
In order to get a first idea what a solution is supposed to address, run the `info` command:
```
album info album:template-python:0.1.0
```

A solution can be installed via the `install` command:
```
album install album:template-python:0.1.0
```
Once a solution is installed, you can run it and also attach parameter values:
```
album run album:template-python:0.1.0 --name PARAMETER_VALUE
```
A solution can include a test routine which should help verify that your system can run the solution correctly:
```
album test album:template-python:0.1.0
```
A solution can be uninstalled via the `uninstall` command - this will remove all local files associated with the solution:
```
album uninstall album:template-python:0.1.0
```

## What is a catalog?

A catalog holds a set of solutions together. This could be a set of thematically matching solutions or maybe the solution collection of a research group. A catalog should include all existing versions of the same solution.
It can live in a git repository, e.g. on github or gitlab, on a network drive or just locally on your hard rive.

A catalog can be identified..
- by path
- by git URL
- by github or gitlab repository URL

In this guide, we will use the `https://gitlab.com/album-app/catalogs/capture-knowledge` catalog as an example, please replace this URL with the target catalog identifier.

## How to use catalogs
In order to use an existing catalog, you need to add it to your local album collection:
```
album add-catalog https://gitlab.com/album-app/catalogs/capture-knowledge
```
You can also remove a catalog - this will remove all solutions associated with the catalog.
```
album remove-catalog https://gitlab.com/album-app/catalogs/capture-knowledge
```
Changes to a catalog will not automatically appear in your local collection - you first have to initiate the update process.

Call this command to reload all indices of all catalogs added to your local collection:
```
album update
```
Once this is done, you can review the difference between these indices and your local collection: 
```
album upgrade --dry-run
```
.. and also apply the changes - this will synchronize the latest state of all catalogs with the state of the local solution collection: 
```
album upgrade
```
The same can be done for just one catalog:
```
album update https://gitlab.com/album-app/catalogs/capture-knowledge
album upgrade https://gitlab.com/album-app/catalogs/capture-knowledge --dry-run
album upgrade https://gitlab.com/album-app/catalogs/capture-knowledge
```
