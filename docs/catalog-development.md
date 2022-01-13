# Catalog management

This page documents how to setup and use your own catalogs. We encourage folks who don't want to curate their own catalogs to 
use our [capture-knowledge](https://gitlab.com/album-app/catalogs/capture-knowledge) catalog instead. 
Please [contact us](/contributing) if you have questions!

## Creating a new catalog

Use this command to create a new catalog based on any template from [here](https://gitlab.com/album-app/catalogs/templates) - it will be copied into the provided directory with the provided new name.
```
album clone [catalog-template-name] --target-dir [parent-dir-of-new-catalog] --name [name-of-new-catalog]
```
The most basic template is this one:
```
album clone catalog --target-dir [parent-dir-of-new-catalog] --name [name-of-new-catalog]
```
If you want to build a catalog website using Gatsby (this can be done via gitlab or github CI), use this template:
```
album clone catalog-gatsby --target-dir [parent-dir-of-new-catalog] --name [name-of-new-catalog]
```
Turn this newly created folder (`[parent-dir-of-new-catalog]/[name-of-new-catalog]`) into a git repo and upload it somewhere.

**GATSBY NOTE** The whole gatsby website procedure is not documented well yet and will be improved.

## Deploy a solution into a catalog
Add the catalog to your local collection:
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

## DOI support for solutions
We provide tools to automatically upload solutions to Zenodo and add the respective DOI to the solution during solution deployment. 
This requires more steps when creating a catalog and these steps still need to be documented properly. 
For now, if you want to cite your solution using DOIs, we suggest doing one of the following things:
- manually upload the solution ZIP file added to the catalog during the deployment to, for example, Zenodo
- use our [capture-knowledge](https://gitlab.com/album-app/catalogs/capture-knowledge) catalog - deploying to it will create a merge request which includes the Zenodo upload procedure
- contact us so we can help you
