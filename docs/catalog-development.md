# Catalog management

This page documents how to setup and use your own catalogs. 
Please [contact us](/contributing) if you have questions!

All instructions are command line calls based on the Unix syntax - Windows users have to use backslashes for local paths.

## Catalog types

We distinguish between **direct** and **request** catalogs. Both are based on GIT and can be uploaded to for example GitHub or GitLab. They differ in how new or updated solutions are handled via the command `album deploy [solution] [catalog]`:
- Changes to a **direct** catalog will be immediately accessible to anyone who uses this catalog. The changes are directly pushed to the `main` branch of the catalog.
- Changes to a **request** catalog have to be reviewed. The changes are pushed to a branch. We provide a GitLab CI script automatically creating a merge request to the catalog repository which also supports Zenodo DOI generation.

We suggest using the different types in these scenarios:
- For **rapid development** use a **direct catalog** - for example for local, personal, or temporary catalogs.
- For **federated catalogs** and **versioned solutions with DOIs** use a **request catalog**.

## How to automatically share solutions to GitLab / GitHub

1. Setup a new empty repository on GitLab or GitHub. Copy the repo URL (SSH) and make sure your console is configured to be able to push to this repository (via SSH for example).
2. Decide if you want a direct or a request catalog - see the *Catalog types* chapter.

For a direct catalog (i.e. for rapid prototyping), clone the catalog first locally using this command:
```
album clone template:catalog [repo-url] [catalog-name]
```
For a request catalog (i.e. federated), clone the catalog first locally using this command:
```
album clone template:catalog-request [repo-url] [catalog-name]
```

3. Add the online catalog to your local collection:
```
album add-catalog [repo-url]
```

4. Write your new solutions anywhere on disk and deploy them into the remote catalog:
```
album deploy [solution-path] [catalog-name]
```
For request catalogs, changes won't appear in album until the newly created branch is merged.

5. Upgrade the catalog in your local collection:
```
album update [catalog-name]
album upgrade [catalog-name]
```

## How to create and use a local catalog
1. Use this command to create a new catalog:
```
album clone template:catalog [catalog-dir] [catalog-name]
```
This will create a bare git repository including the basics of a direct catalog in `[catalog-dir]`. 

2. Add it to your collection by calling this:
```
album add-catalog [catalog-dir]
```

3. Write your new solutions anywhere on disk and deploy them into the catalog with this command:
```
album deploy [solution-path] [catalog-name]
```

4. Upgrade the catalog in your local collection:
```
album update [catalog-name]
album upgrade [catalog-name]
```

## How to manually share a local catalog on GitLab / GitHub
1. Setup a new empty repository on GitLab or GitHub.

2. After setting up a local catalog as described in the previous chapter, clone your catalog somewhere locally first:
```
cd [catalog-dir]
git remote add online [git-repo-ssh-url]
git push -u online main
```

Whenever you want to update the online representation of your catalog, call these commands inside the cloned repo:
```
cd [catalog-dir]
git push -u online main
```

## How to track solution development \[within the catalog repository\]
We recommend making a separate repository for developing your solutions, next to the catalog repository (see our [default](https://gitlab.com/album-app/catalogs/default) and [default-dev](https://gitlab.com/album-app/catalogs/default-dev) repositories as an example - `default` is a catalog which was created via the `clone` command demonstrated below, `default-dev` does not have a fixed structure, it's just the source from where we deploy solutions into the catalog) 

One can also add the source files of solutions to the catalog repository - here is an example:

Add your solution source files for example to `[catalog-dir]/src/`:
```
[catalog-dir]/src/groupA/solution1/solution.py`
[catalog-dir]/src/groupA/solution2/solution.py`
[catalog-dir]/src/groupB/solution1/solution.py`
```
Add them to the repository using the default git commands.
This is how you would deploy these solutions into the catalog:
```
album deploy [catalog-dir]/src/groupA/solution1 [catalog-name]
```

## How to create a catalog with a website representation

We provide a Gatsby theme and a GitLab CI setup for automatically deploying a web representation of a catalog. This won't work on GitHub, but the CI script can surely easily be adjusted to also work on GitHub.

Proceed as described in *How to automatically share solutions to GitLab / GitHub*, but instead of `template:catalog` clone `template:catalog-gatsby` (or instead of `template:catalog-request` use `template:catalog-request-gatsby`). The webste will be deployed using GitLab pages

It's also possible to add the website feature to an already existing catalog. The whole Gatsby website procedure is not documented well yet and will be improved.


## Rapid prototyping
While developing a solution, developers and testers might not always want to deploy new versions of a solution - we recommend attaching `-SNAPSHOT` to the version
one is working on (i.e. `0.1.0-SNAPSHOT` prior to releasing `0.1.0`).

In order to test changes to the run method of a solution rapidly without having to uninstall and reinstall a solution, use the `--override` flag after deploying the solution:
```
album update [catalog-name]
album upgrade [catalog-name] --override
```
The `--override` flag will check for each changed solution if it is already installed, and update the local cache of the solution content in this case.
Now `album run [solution]` will use the updated solution file. Be aware that any changes to the `setup` method of the solution will not be processed,
including changes to the environment of the solution. In order to apply these, the solution needs to be uninstalled and reinstalled.

## DOI support for solutions
We provide tools to automatically upload solutions to Zenodo and add the respective DOI to the solution during solution deployment. 
This requires more steps when creating a catalog and these steps still need to be documented properly. 