album usage
================================

For installation instructions, see [installation-instructions](/installation-instructions).

## Solutions

A solution holds all information to solve a specific problem. Ideally, this includes:
* a code snippet installing software components needed to run the solution in a reproducible manner
* the solution parameters (e.g. input and output files, algorithm parameters)
* how to apply the parameters to a specific algorithm / software to get the result to the problem
* information about what to cite if this solution is used to solve scientic problems
* information about the author of the solution itself

After adding catalogs (see next chapter), a solution should first be installed via one of these commands:
```
album install [solution-file-or-url]
album install [group:name:version]
```
Once a solution is installed, you can run it like this:
```
album run [solution-file-or-url] --my-parameter [parameter-value]
album run [group:name:version] --my-parameter [parameter-value]
```
A solution can include a test routine which should help verify that your system can run the solution correctly:
```
album test [solution-file-or-url]
album test [group:name:version]
```

## Catalogs
A catalog holds a set of solutions together. This could be a set of thematically matching solutions or maybe the solution collection of a research group. A catalog should include all existing versions of the same solution.
It can live in a git repository, e.g. on github or gitlab, on a network drive or just locally on your hard rive.

In order to use an existing catalog, you need to add it to your local album collection:
```
album add-catalog [catalog-directory-or-url]
```
You can also remove a catalog - this will remove  all solutions associated with the catalog.
```
album remove-catalog [catalog-directory-or-url]
```
Adding a catalog will not automatically make new solutions available and changes to a catalog will not automatically appear in your local collection - you first have to initiate the update process.

Call this command to reload all indices of all catalogs added to your local collection:
```
album update
```
Once this is done, you can review the difference between these indices and your local collection: 
```
album upgrade --dry-run
```
.. and also apply the changes - this will synchronize the latest state of all your catalogs with the state of your local solution collection: 
```
album upgrade
```
The same can be done for just one catalog:
```
album update [catalog-directory-or-url]
album upgrade [catalog-directory-or-url] --dry-run
album upgrade [catalog-directory-or-url]
```

To get an overview of your whole local collection, you can run this command:
```
album index
```